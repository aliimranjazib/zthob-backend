import logging
import uuid
from decimal import Decimal

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.orders.models import (
    CheckoutPaymentAttempt,
    CheckoutSession,
    MyFatoorahWebhookEvent,
    Order,
    RemainingPaymentSession,
)
from apps.orders.myfatoorah import (
    MyFatoorahConfigurationError,
    MyFatoorahGatewayError,
    get_payment_status,
    payment_metadata,
    verify_webhook_signature,
)
from apps.orders.payments import get_payment_option, money
from apps.orders.serializers import (
    MyFatoorahConfirmPaymentSerializer,
    MyFatoorahPreparePaymentSerializer,
    MyFatoorahRemainingPrepareSerializer,
    OrderSerializer,
)
from apps.orders.views import _create_order_from_checkout, _record_remaining_payment
from zthob.utils import api_response


logger = logging.getLogger(__name__)
TERMINAL_FAILURE_STATUSES = {'FAILED', 'CANCELED', 'CANCELLED'}


def _myfatoorah_currency():
    return getattr(settings, 'MYFATOORAH_CURRENCY', 'SAR').upper()


def _new_attempt_reference():
    return f"mfp_{uuid.uuid4().hex}"


def _new_remaining_key():
    return f"rem_{uuid.uuid4().hex[:24]}"


def _attempt_data(attempt, *, order=None):
    return {
        'attempt_reference': attempt.attempt_reference,
        'customer_reference': attempt.attempt_reference,
        'user_defined_field': attempt.attempt_reference,
        'invoice_id': attempt.invoice_id,
        'amount': str(attempt.expected_amount),
        'currency': attempt.currency,
        'payment_option': attempt.payment_option,
        'status': attempt.status,
        'expires_at': attempt.expires_at.isoformat(),
        'order_id': order.id if order else None,
    }


def _reference_matches(attempt, details):
    return attempt.attempt_reference in {
        details.customer_reference,
        details.user_defined_field,
    }


def _validate_paid_details(attempt, details):
    if details.invoice_id != attempt.invoice_id:
        raise ValidationError('MyFatoorah invoice does not match this payment attempt.')
    if money(details.invoice_value) != money(attempt.expected_amount):
        raise ValidationError('MyFatoorah payment amount does not match the expected amount.')
    if details.currency != attempt.currency:
        raise ValidationError(
            f'MyFatoorah payment currency must be {attempt.currency}.'
        )
    if not _reference_matches(attempt, details):
        raise ValidationError('MyFatoorah payment reference does not match this payment attempt.')


def _attach_invoice(*, attempt_reference, invoice_id, customer=None, purpose=None):
    with transaction.atomic():
        queryset = CheckoutPaymentAttempt.objects.select_for_update()
        if customer is not None:
            queryset = queryset.filter(customer=customer)
        if purpose is not None:
            queryset = queryset.filter(purpose=purpose)
        attempt = queryset.get(attempt_reference=attempt_reference)

        if attempt.status == 'succeeded':
            return attempt
        if attempt.invoice_id and attempt.invoice_id != invoice_id:
            raise ValidationError('This payment attempt already uses another MyFatoorah invoice.')
        if not attempt.invoice_id:
            attempt.invoice_id = invoice_id
            attempt.status = 'invoice_created'
            try:
                attempt.save(update_fields=['invoice_id', 'status', 'updated_at'])
            except IntegrityError as exc:
                raise ValidationError('This MyFatoorah invoice is already attached to another payment.') from exc
        return attempt


def _mark_attempt_not_paid(attempt_reference, details):
    with transaction.atomic():
        attempt = CheckoutPaymentAttempt.objects.select_for_update().get(
            attempt_reference=attempt_reference
        )
        if attempt.status == 'succeeded':
            return attempt
        attempt.gateway_status = details.transaction_status or details.invoice_status
        attempt.payment_id = details.payment_id or attempt.payment_id
        attempt.gateway_payment_method = details.payment_method or attempt.gateway_payment_method
        if details.transaction_status in TERMINAL_FAILURE_STATUSES:
            attempt.status = 'failed'
            attempt.failure_reason = 'Payment was not completed by MyFatoorah.'
        else:
            attempt.status = 'pending'
            attempt.failure_reason = None
        attempt.metadata = payment_metadata(details)
        attempt.save(update_fields=[
            'status',
            'payment_id',
            'gateway_status',
            'gateway_payment_method',
            'failure_reason',
            'metadata',
            'updated_at',
        ])
        return attempt


def _reject_attempt(attempt_reference, reason):
    CheckoutPaymentAttempt.objects.filter(
        attempt_reference=attempt_reference,
    ).exclude(status='succeeded').update(
        status='failed',
        failure_reason=str(reason)[:255],
        updated_at=timezone.now(),
    )


def _finalize_attempt(attempt_reference, details):
    with transaction.atomic():
        # Lock the attempt row only. select_related on nullable FKs causes
        # PostgreSQL "FOR UPDATE cannot be applied to the nullable side of an outer join".
        attempt = CheckoutPaymentAttempt.objects.select_for_update().get(
            attempt_reference=attempt_reference,
        )

        if attempt.status == 'succeeded':
            order = attempt.checkout.order if attempt.checkout_id else attempt.remaining_session.order
            return attempt, order

        _validate_paid_details(attempt, details)
        payment_reference = details.payment_id or f'myfatoorah-invoice-{details.invoice_id}'
        metadata = payment_metadata(details)

        if attempt.purpose == 'checkout':
            checkout = CheckoutSession.objects.select_for_update().select_related('customer').get(
                id=attempt.checkout_id
            )
            if checkout.order_id and checkout.payment_reference != payment_reference:
                attempt.status = 'requires_review'
                attempt.payment_id = details.payment_id or None
                attempt.gateway_status = details.transaction_status
                attempt.gateway_payment_method = details.payment_method or None
                attempt.verified_at = timezone.now()
                attempt.failure_reason = 'Duplicate successful payment requires manual review.'
                attempt.metadata = metadata
                attempt.save(update_fields=[
                    'status', 'payment_id', 'gateway_status', 'gateway_payment_method',
                    'verified_at', 'failure_reason', 'metadata', 'updated_at',
                ])
                return attempt, checkout.order
            order = _create_order_from_checkout(
                checkout=checkout,
                customer=checkout.customer,
                payment_method='credit_card',
                payment_option_key=attempt.payment_option,
                payment_reference=payment_reference,
                collected_by=None,
                payment_metadata={
                    'source': 'myfatoorah_verified_payment',
                    'attempt_reference': attempt.attempt_reference,
                    **metadata,
                },
                allow_expired=True,
            )
        else:
            session = RemainingPaymentSession.objects.select_for_update().select_related('order').get(
                id=attempt.remaining_session_id
            )
            order = Order.objects.select_for_update().get(id=session.order_id)
            if not order.has_remaining_balance or money(order.remaining_amount) != money(attempt.expected_amount):
                attempt.status = 'requires_review'
                attempt.payment_id = details.payment_id or None
                attempt.gateway_status = details.transaction_status
                attempt.gateway_payment_method = details.payment_method or None
                attempt.verified_at = timezone.now()
                attempt.failure_reason = 'Duplicate or excess successful payment requires manual review.'
                attempt.metadata = metadata
                attempt.save(update_fields=[
                    'status', 'payment_id', 'gateway_status', 'gateway_payment_method',
                    'verified_at', 'failure_reason', 'metadata', 'updated_at',
                ])
                return attempt, order
            _record_remaining_payment(
                order=order,
                amount=attempt.expected_amount,
                payment_method='credit_card',
                payment_reference=payment_reference,
                collected_by=None,
                notes='Remaining balance paid online via MyFatoorah.',
                metadata={
                    'source': 'myfatoorah_verified_remaining_payment',
                    'attempt_reference': attempt.attempt_reference,
                    **metadata,
                },
            )
            session.status = 'payment_completed'
            session.payment_reference = payment_reference
            session.payment_confirmed_at = timezone.now()
            session.save(update_fields=[
                'status', 'payment_reference', 'payment_confirmed_at', 'updated_at'
            ])

        attempt.status = 'succeeded'
        attempt.payment_id = details.payment_id or None
        attempt.gateway_status = details.transaction_status
        attempt.gateway_payment_method = details.payment_method or None
        attempt.verified_at = timezone.now()
        attempt.failure_reason = None
        attempt.metadata = metadata
        attempt.save(update_fields=[
            'status',
            'payment_id',
            'gateway_status',
            'gateway_payment_method',
            'verified_at',
            'failure_reason',
            'metadata',
            'updated_at',
        ])
        return attempt, order


def _verify_and_process(attempt):
    details = get_payment_status(attempt.invoice_id)
    if not details.is_paid:
        return _mark_attempt_not_paid(attempt.attempt_reference, details), None
    return _finalize_attempt(attempt.attempt_reference, details)


class MyFatoorahCheckoutPrepareView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=MyFatoorahPreparePaymentSerializer,
        summary='Prepare a MyFatoorah checkout payment',
        tags=['MyFatoorah Payments'],
    )
    def post(self, request):
        serializer = MyFatoorahPreparePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        existing = CheckoutPaymentAttempt.objects.filter(
            customer=request.user,
            client_idempotency_key=data['idempotency_key'],
        ).first()
        if existing:
            if (
                existing.purpose != 'checkout'
                or existing.checkout.booking_unique_key != data['bookingUniqueKey']
                or existing.payment_option != data['payment_option']
            ):
                return api_response(
                    success=False,
                    message='This idempotency key is already used for another payment.',
                    status_code=status.HTTP_409_CONFLICT,
                )
            return api_response(
                success=True,
                message='Existing MyFatoorah payment attempt retrieved.',
                data=_attempt_data(existing, order=existing.checkout.order),
                status_code=status.HTTP_200_OK,
            )

        with transaction.atomic():
            checkout = CheckoutSession.objects.select_for_update().filter(
                booking_unique_key=data['bookingUniqueKey'],
                customer=request.user,
            ).first()
            if not checkout:
                return api_response(
                    success=False,
                    message='Checkout not found.',
                    status_code=status.HTTP_404_NOT_FOUND,
                )
            if checkout.order_id:
                return api_response(
                    success=False,
                    message='This checkout already has an order.',
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            if checkout.is_expired:
                checkout.status = 'expired'
                checkout.save(update_fields=['status', 'updated_at'])
                return api_response(
                    success=False,
                    message='Checkout has expired. Please create a new checkout.',
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            if checkout.status not in {'active', 'payment_initiated', 'payment_failed'}:
                return api_response(
                    success=False,
                    message=f'Checkout cannot be paid in its current state: {checkout.status}.',
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            active_attempt = checkout.payment_attempts.filter(
                status__in={'prepared', 'invoice_created', 'pending'},
            ).first()
            if active_attempt:
                return api_response(
                    success=False,
                    message='This checkout already has an active payment attempt.',
                    data=_attempt_data(active_attempt),
                    status_code=status.HTTP_409_CONFLICT,
                )

            selected = get_payment_option(
                (checkout.pricing_snapshot or {}).get('total_amount', '0.00'),
                data['payment_option'],
            )
            if not selected or money(selected['pay_now_amount']) <= Decimal('0.00'):
                return api_response(
                    success=False,
                    message='The selected payment option is not available for online payment.',
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            try:
                with transaction.atomic():
                    attempt = CheckoutPaymentAttempt.objects.create(
                        attempt_reference=_new_attempt_reference(),
                        customer=request.user,
                        checkout=checkout,
                        purpose='checkout',
                        payment_option=data['payment_option'],
                        expected_amount=money(selected['pay_now_amount']),
                        currency=_myfatoorah_currency(),
                        client_idempotency_key=data['idempotency_key'],
                        expires_at=checkout.expires_at,
                    )
            except IntegrityError:
                attempt = CheckoutPaymentAttempt.objects.filter(
                    customer=request.user,
                    client_idempotency_key=data['idempotency_key'],
                    purpose='checkout',
                    checkout=checkout,
                ).first()
                if not attempt:
                    raise
                if attempt.payment_option != data['payment_option']:
                    return api_response(
                        success=False,
                        message='This idempotency key is already used for another payment option.',
                        status_code=status.HTTP_409_CONFLICT,
                    )
            checkout.status = 'payment_initiated'
            checkout.payment_method = 'credit_card'
            checkout.payment_option = data['payment_option']
            checkout.save(update_fields=[
                'status', 'payment_method', 'payment_option', 'updated_at'
            ])

        return api_response(
            success=True,
            message='MyFatoorah payment attempt prepared.',
            data=_attempt_data(attempt),
            status_code=status.HTTP_201_CREATED,
        )


class _MyFatoorahConfirmMixin:
    purpose = None

    @extend_schema(
        request=MyFatoorahConfirmPaymentSerializer,
        summary='Confirm and verify a MyFatoorah payment',
        tags=['MyFatoorah Payments'],
    )
    def post(self, request, order_id=None):
        serializer = MyFatoorahConfirmPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            attempt = _attach_invoice(
                attempt_reference=data['attempt_reference'],
                invoice_id=data['invoice_id'],
                customer=request.user,
                purpose=self.purpose,
            )
        except CheckoutPaymentAttempt.DoesNotExist:
            return api_response(
                success=False,
                message='Payment attempt not found.',
                status_code=status.HTTP_404_NOT_FOUND,
            )
        except ValidationError as exc:
            return api_response(
                success=False,
                message=str(exc.detail),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        if (
            order_id is not None
            and attempt.remaining_session_id
            and attempt.remaining_session.order_id != order_id
        ):
            return api_response(
                success=False,
                message='Payment attempt does not belong to this order.',
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        if attempt.status == 'succeeded':
            order = attempt.checkout.order if attempt.checkout_id else attempt.remaining_session.order
            return api_response(
                success=True,
                message='Payment was already confirmed.',
                data=_attempt_data(attempt, order=order),
                status_code=status.HTTP_200_OK,
            )
        if attempt.status == 'requires_review':
            order = attempt.checkout.order if attempt.checkout_id else attempt.remaining_session.order
            return api_response(
                success=False,
                message='Payment was received but requires manual review. Please contact support.',
                data=_attempt_data(attempt, order=order),
                status_code=status.HTTP_409_CONFLICT,
            )

        try:
            attempt, order = _verify_and_process(attempt)
        except MyFatoorahConfigurationError as exc:
            logger.error('MyFatoorah configuration error during payment confirmation: %s', exc)
            return api_response(
                success=False,
                message='Payment verification is temporarily unavailable.',
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except MyFatoorahGatewayError as exc:
            logger.warning('MyFatoorah payment verification failed for %s: %s', attempt.attempt_reference, exc)
            return api_response(
                success=False,
                message=str(exc),
                data=_attempt_data(attempt),
                status_code=status.HTTP_502_BAD_GATEWAY,
            )
        except ValidationError as exc:
            logger.warning('Rejected MyFatoorah payment %s: %s', attempt.attempt_reference, exc)
            _reject_attempt(attempt.attempt_reference, exc.detail)
            attempt.refresh_from_db()
            return api_response(
                success=False,
                message=str(exc.detail),
                data=_attempt_data(attempt),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        if not order:
            return api_response(
                success=True,
                message='Payment is not completed yet.',
                data=_attempt_data(attempt),
                status_code=status.HTTP_202_ACCEPTED,
            )
        if attempt.status == 'requires_review':
            return api_response(
                success=False,
                message='Payment was received but requires manual review. Please contact support.',
                data=_attempt_data(attempt, order=order),
                status_code=status.HTTP_409_CONFLICT,
            )
        return api_response(
            success=True,
            message='MyFatoorah payment confirmed successfully.',
            data={
                **_attempt_data(attempt, order=order),
                'order': OrderSerializer(order, context={'request': request}).data,
            },
            status_code=status.HTTP_200_OK,
        )


class MyFatoorahCheckoutConfirmView(_MyFatoorahConfirmMixin, APIView):
    permission_classes = [IsAuthenticated]
    purpose = 'checkout'


class MyFatoorahRemainingPrepareView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=MyFatoorahRemainingPrepareSerializer,
        summary='Prepare a MyFatoorah remaining-balance payment',
        tags=['MyFatoorah Payments'],
    )
    def post(self, request, order_id):
        serializer = MyFatoorahRemainingPrepareSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        idempotency_key = serializer.validated_data['idempotency_key']

        existing = CheckoutPaymentAttempt.objects.filter(
            customer=request.user,
            client_idempotency_key=idempotency_key,
        ).first()
        if existing:
            if existing.purpose != 'remaining_balance' or existing.remaining_session.order_id != order_id:
                return api_response(
                    success=False,
                    message='This idempotency key is already used for another payment.',
                    status_code=status.HTTP_409_CONFLICT,
                )
            return api_response(
                success=True,
                message='Existing MyFatoorah payment attempt retrieved.',
                data=_attempt_data(existing, order=existing.remaining_session.order),
                status_code=status.HTTP_200_OK,
            )

        with transaction.atomic():
            order = Order.objects.select_for_update().filter(id=order_id).first()
            if not order:
                return api_response(
                    success=False,
                    message='Order not found.',
                    status_code=status.HTTP_404_NOT_FOUND,
                )
            if not request.user.is_admin and order.customer_id != request.user.id:
                return api_response(
                    success=False,
                    message='You can only pay the remaining balance for your own order.',
                    status_code=status.HTTP_403_FORBIDDEN,
                )
            if order.status == 'cancelled' or order.payment_status == 'refunded':
                return api_response(
                    success=False,
                    message='This order cannot accept another payment.',
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            if not order.has_remaining_balance:
                return api_response(
                    success=False,
                    message='No remaining balance to pay.',
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            active_attempt = CheckoutPaymentAttempt.objects.filter(
                remaining_session__order=order,
                status__in={'prepared', 'invoice_created', 'pending'},
            ).first()
            if active_attempt:
                return api_response(
                    success=False,
                    message='This order already has an active remaining-balance payment attempt.',
                    data=_attempt_data(active_attempt, order=order),
                    status_code=status.HTTP_409_CONFLICT,
                )

            expires_at = timezone.now() + timezone.timedelta(minutes=30)
            session = RemainingPaymentSession.objects.create(
                booking_unique_key=_new_remaining_key(),
                customer=order.customer,
                order=order,
                status='payment_initiated',
                amount=money(order.remaining_amount),
                currency=_myfatoorah_currency(),
                expires_at=expires_at,
            )
            try:
                with transaction.atomic():
                    attempt = CheckoutPaymentAttempt.objects.create(
                        attempt_reference=_new_attempt_reference(),
                        customer=order.customer,
                        remaining_session=session,
                        purpose='remaining_balance',
                        payment_option='remaining_balance',
                        expected_amount=session.amount,
                        currency=_myfatoorah_currency(),
                        client_idempotency_key=idempotency_key,
                        expires_at=expires_at,
                    )
            except IntegrityError:
                attempt = CheckoutPaymentAttempt.objects.filter(
                    customer=request.user,
                    client_idempotency_key=idempotency_key,
                    purpose='remaining_balance',
                    remaining_session__order=order,
                ).first()
                if not attempt:
                    raise
                session.delete()
                session = attempt.remaining_session

        return api_response(
            success=True,
            message='MyFatoorah remaining payment attempt prepared.',
            data={
                **_attempt_data(attempt, order=order),
                'bookingUniqueKey': session.booking_unique_key,
            },
            status_code=status.HTTP_201_CREATED,
        )


class MyFatoorahRemainingConfirmView(_MyFatoorahConfirmMixin, APIView):
    permission_classes = [IsAuthenticated]
    purpose = 'remaining_balance'


class MyFatoorahWebhookView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = []

    def post(self, request):
        signature = request.headers.get('myfatoorah-signature', '')
        try:
            signature_valid = verify_webhook_signature(request.data, signature)
        except MyFatoorahConfigurationError:
            logger.exception('MyFatoorah webhook configuration is incomplete')
            return api_response(
                success=False,
                message='Webhook is not configured.',
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        if not signature_valid:
            return api_response(
                success=False,
                message='Invalid webhook signature.',
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        event = request.data.get('Event') or {}
        webhook_data = request.data.get('Data') or {}
        invoice = webhook_data.get('Invoice') or {}
        gateway_transaction = webhook_data.get('Transaction') or {}
        if event.get('Name') != 'PAYMENT_STATUS_CHANGED':
            return api_response(success=True, message='Webhook event ignored.', status_code=status.HTTP_200_OK)

        event_reference = str(event.get('Reference') or '').strip()
        invoice_id = str(invoice.get('Id') or '').strip()
        payment_id = str(gateway_transaction.get('PaymentId') or '').strip()
        if not event_reference or not invoice_id:
            return api_response(
                success=False,
                message='Webhook is missing required references.',
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        receipt, _ = MyFatoorahWebhookEvent.objects.get_or_create(
            event_reference=event_reference,
            defaults={
                'event_name': event.get('Name'),
                'invoice_id': invoice_id,
                'payment_id': payment_id or None,
                'transaction_status': gateway_transaction.get('Status'),
            },
        )
        if receipt.processed_at:
            return api_response(success=True, message='Webhook already processed.', status_code=status.HTTP_200_OK)
        receipt.attempts += 1
        receipt.save(update_fields=['attempts', 'updated_at'])

        attempt = CheckoutPaymentAttempt.objects.filter(invoice_id=invoice_id).first()
        if not attempt:
            reference = str(
                invoice.get('UserDefinedField')
                or invoice.get('ExternalIdentifier')
                or ''
            ).strip()
            attempt = CheckoutPaymentAttempt.objects.filter(attempt_reference=reference).first()
            if attempt:
                try:
                    attempt = _attach_invoice(
                        attempt_reference=attempt.attempt_reference,
                        invoice_id=invoice_id,
                    )
                except ValidationError as exc:
                    receipt.last_error = str(exc.detail)
                    receipt.processed_at = timezone.now()
                    receipt.save(update_fields=['last_error', 'processed_at', 'updated_at'])
                    return api_response(success=True, message='Webhook rejected.', status_code=status.HTTP_200_OK)

        if not attempt:
            receipt.last_error = 'No matching payment attempt.'
            receipt.processed_at = timezone.now()
            receipt.save(update_fields=['last_error', 'processed_at', 'updated_at'])
            return api_response(success=True, message='No matching payment attempt.', status_code=status.HTTP_200_OK)

        try:
            _verify_and_process(attempt)
        except (MyFatoorahConfigurationError, MyFatoorahGatewayError) as exc:
            receipt.last_error = str(exc)[:255]
            receipt.save(update_fields=['last_error', 'updated_at'])
            return api_response(
                success=False,
                message='Webhook processing will be retried.',
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except ValidationError as exc:
            _reject_attempt(attempt.attempt_reference, exc.detail)
            receipt.last_error = str(exc.detail)[:255]
            receipt.processed_at = timezone.now()
            receipt.save(update_fields=['last_error', 'processed_at', 'updated_at'])
            return api_response(success=True, message='Webhook payment was rejected.', status_code=status.HTTP_200_OK)

        receipt.last_error = None
        receipt.processed_at = timezone.now()
        receipt.save(update_fields=['last_error', 'processed_at', 'updated_at'])
        return api_response(success=True, message='Webhook processed.', status_code=status.HTTP_200_OK)
