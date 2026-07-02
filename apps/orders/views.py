import json
import logging
from types import SimpleNamespace
from urllib.parse import urlencode

from django.conf import settings
from django.shortcuts import get_object_or_404, render
from django.http import Http404, HttpResponse, HttpResponseRedirect
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from .actions import OrderActionManager
from django.db.models import Q
from drf_spectacular.utils import extend_schema
from .models import CheckoutSession, Order, OrderItem, OrderPayment, OrderStatusHistory, RemainingPaymentSession
from .serializers import(
OrderItemSerializer,
OrderItemCreateSerializer,
OrderSerializer,
OrderCreateSerializer,
OrderUpdateSerializer,
OrderListSerializer,
	OrderStatusHistorySerializer,
	OrderPaymentStatusUpdateSerializer,
    PayRemainingBalanceSerializer,
	OrderStatusUpdateResponseSerializer,
    CheckoutCreateOrderSerializer,
    CheckoutSessionSerializer,
    CheckoutInitiatePaymentSerializer,
    CheckoutInitiatePaymentResponseSerializer,
	)
from apps.tailors.models import TailorProfile
from apps.tailors.permissions import IsShopStaff
from apps.tailors.shop_access import user_can_manage_shop_order
from apps.customers.models import CustomerProfile, Address
from zthob.utils import api_response 
import uuid
from decimal import Decimal
from apps.orders.payments import get_payment_option, money
from apps.orders.alinma import (
    AlinmaConfigurationError,
    AlinmaGatewayError,
    get_response_message,
    get_alinma_config,
    initiate_hosted_payment,
    is_successful_callback,
    parse_callback_payload,
    response_amount,
    verify_callback_signature,
)


def _get_tailor_owner_user(request):
    """Resolve the owner tailor user for owner/staff sessions."""
    if hasattr(request.user, 'tailor_employee') and request.user.tailor_employee.is_active:
        return request.user.tailor_employee.tailor.user

    try:
        TailorProfile.objects.get(user=request.user)
        return request.user
    except TailorProfile.DoesNotExist:
        return None


logger = logging.getLogger(__name__)


def _create_order_from_checkout(
    *,
    checkout,
    customer,
    payment_method,
    payment_option_key,
    payment_reference,
    collected_by,
    serializer_request=None,
    payment_metadata=None,
):
    if checkout.order:
        return checkout.order

    if checkout.status not in {'active', 'payment_initiated'}:
        raise ValidationError(f"Checkout is not active. Current status: {checkout.status}")

    if checkout.is_expired:
        checkout.status = 'expired'
        checkout.save(update_fields=['status', 'updated_at'])
        raise ValidationError("Checkout has expired. Please create a new checkout.")

    checkout_total = (checkout.pricing_snapshot or {}).get('total_amount', '0.00')
    if not get_payment_option(checkout_total, payment_option_key):
        raise ValidationError(
            f"Payment option '{payment_option_key}' is not available for this checkout total."
        )

    if payment_method == 'credit_card':
        reference_used = (
            Order.objects.filter(payment_reference=payment_reference).exists()
            or CheckoutSession.objects.filter(payment_reference=payment_reference).exclude(id=checkout.id).exists()
            or OrderPayment.objects.filter(payment_reference=payment_reference).exists()
        )
        if reference_used:
            raise ValidationError("This payment reference has already been used.")

    previous_payment_status = 'pending'
    order_data = dict(checkout.request_payload)
    order_data['customer'] = customer.id
    order_data['payment_method'] = payment_method

    context_request = serializer_request or SimpleNamespace(user=customer)
    order_serializer = OrderCreateSerializer(data=order_data, context={'request': context_request})
    if not order_serializer.is_valid():
        raise ValidationError(order_serializer.errors)

    order = order_serializer.save()
    pricing_snapshot = checkout.pricing_snapshot or {}
    pricing_fields = [
        'subtotal',
        'stitching_price',
        'tax_amount',
        'delivery_fee',
        'system_fee',
        'measurement_fee',
        'express_fee',
        'total_amount',
    ]
    pricing_update_fields = []
    for field in pricing_fields:
        if field in pricing_snapshot:
            setattr(order, field, money(pricing_snapshot[field]))
            pricing_update_fields.append(field)

    selected_payment_option = get_payment_option(order.total_amount, payment_option_key)
    if not selected_payment_option:
        raise ValidationError(
            f"Payment option '{payment_option_key}' is not available for this checkout total."
        )

    pay_now_amount = money(selected_payment_option['pay_now_amount'])
    payment_plan = selected_payment_option['payment_plan']

    order.payment_method = payment_method
    order.payment_reference = payment_reference if pay_now_amount > Decimal('0.00') else None
    order.deposit_amount = pay_now_amount if payment_plan == 'partial' else Decimal('0.00')
    order.apply_payment_summary(
        pay_now_amount,
        payment_plan=payment_plan,
        payment_option=payment_option_key,
        save=False,
    )
    order.save(update_fields=[
        'payment_method',
        'payment_plan',
        'payment_option',
        'payment_status',
        'payment_reference',
        'deposit_amount',
        'paid_amount',
        'remaining_amount',
        *pricing_update_fields,
        'updated_at',
    ])

    if pay_now_amount > Decimal('0.00'):
        OrderPayment.objects.create(
            order=order,
            amount=pay_now_amount,
            payment_method=payment_method,
            payment_type='deposit' if payment_plan == 'partial' else 'full_payment',
            status='paid',
            payment_reference=payment_reference,
            collected_by=collected_by,
            notes='Initial checkout payment',
            metadata={'payment_option': payment_option_key, **(payment_metadata or {})},
        )

    checkout.order = order
    checkout.status = 'order_created'
    checkout.payment_method = payment_method
    checkout.payment_plan = payment_plan
    checkout.payment_option = payment_option_key
    checkout.payment_reference = payment_reference if pay_now_amount > Decimal('0.00') else None
    checkout.payment_confirmed_at = timezone.now() if pay_now_amount > Decimal('0.00') else None
    checkout.save(update_fields=[
        'order',
        'status',
        'payment_method',
        'payment_plan',
        'payment_option',
        'payment_reference',
        'payment_confirmed_at',
        'updated_at',
    ])

    # Checkout-created orders bypass the usual status transition/action flows,
    # so fire the initial order/payment notifications explicitly here.
    try:
        from apps.notifications.services import NotificationService

        NotificationService.send_order_status_notification(
            order=order,
            old_status='pending',
            new_status=order.status,
            changed_by=collected_by or customer,
        )

        if order.payment_status != previous_payment_status:
            NotificationService.send_payment_status_notification(
                order=order,
                old_status=previous_payment_status,
                new_status=order.payment_status,
            )
    except Exception:
        logger.exception(
            'Failed to send initial checkout notifications for order %s',
            getattr(order, 'order_number', order.id),
        )

    return order


def _build_alinma_customer_payload(*, checkout, user):
    payload = {}

    if getattr(user, 'email', None):
        payload['customerEmail'] = user.email

    address = None
    request_payload = checkout.request_payload if checkout is not None else {}
    address_id = request_payload.get('delivery_address')
    if address_id:
        try:
            address = Address.objects.filter(id=address_id, user=user).first()
        except Exception:
            address = None

    if address:
        payload['billingAddressStreet'] = address.street or 'N/A'
        payload['billingAddressCity'] = address.city or 'Riyadh'
        payload['billingAddressState'] = address.city or 'Riyadh'
        payload['billingAddressPostalCode'] = getattr(address, 'postal_code', '') or '00000'
        payload['billingAddressCountry'] = 'SA'
    else:
        payload['billingAddressStreet'] = 'N/A'
        payload['billingAddressCity'] = 'Riyadh'
        payload['billingAddressState'] = 'Riyadh'
        payload['billingAddressPostalCode'] = '00000'
        payload['billingAddressCountry'] = 'SA'

    return payload


def _build_alinma_return_redirect(*, booking_key, status_value, order_id=None, payment_reference=None):
    base_url = getattr(settings, 'ALINMAPAY_RETURN_URL', '').strip() or 'https://app.mgask.net/payment-result'
    query = {
        'booking_key': booking_key,
        'status': status_value,
    }
    if order_id is not None:
        query['order_id'] = order_id
    if payment_reference:
        query['payment_reference'] = payment_reference
    separator = '&' if '?' in base_url else '?'
    return f'{base_url}{separator}{urlencode(query)}'


def _payload_currency(payload):
    amount_details = payload.get('amountDetails') or {}
    return str(amount_details.get('currency') or payload.get('currency') or '').upper()


def _gateway_metadata(payload):
    card_details = payload.get('cardDetails') or {}
    amount_details = payload.get('amountDetails') or {}
    return {
        'gateway': 'alinma',
        'response_code': str(payload.get('responseCode') or ''),
        'response_description': payload.get('responseDescription'),
        'result': payload.get('result') or payload.get('status'),
        'transaction_datetime': payload.get('transactionDateTime'),
        'auth_code': payload.get('authCode'),
        'rrn': payload.get('rrn'),
        'terminal_id': payload.get('terminalId'),
        'masked_card': card_details.get('maskedCard'),
        'card_brand': card_details.get('cardBrand'),
        'issuer_name': payload.get('issuerName'),
        'amount': amount_details.get('amount') or payload.get('amount'),
        'original_amount': amount_details.get('originalAmount'),
    }


def _verify_alinma_terminal(request, payload):
    expected_terminal_id = get_alinma_config().terminal_id
    callback_terminal_id = (
        request.data.get('termId')
        or request.query_params.get('termId')
        or payload.get('terminalId')
    )
    return str(callback_terminal_id or '') == str(expected_terminal_id)


def _record_remaining_payment(*, order, amount, payment_method, payment_reference, collected_by, notes, metadata=None):
    reference_used = (
        Order.objects.filter(payment_reference=payment_reference).exclude(id=order.id).exists()
        or CheckoutSession.objects.filter(payment_reference=payment_reference).exists()
        or RemainingPaymentSession.objects.filter(payment_reference=payment_reference).exists()
        or OrderPayment.objects.filter(payment_reference=payment_reference).exists()
    )
    if reference_used:
        raise ValidationError("This payment reference has already been used.")

    old_payment_status = order.payment_status
    OrderPayment.objects.create(
        order=order,
        amount=amount,
        payment_method=payment_method,
        payment_type='remaining_balance' if order.paid_amount > Decimal('0.00') else 'full_payment',
        status='paid',
        payment_reference=payment_reference,
        collected_by=collected_by,
        notes=notes,
        metadata={'previous_payment_status': old_payment_status, **(metadata or {})},
    )

    if not order.payment_reference:
        order.payment_reference = payment_reference
    order.apply_payment_summary(order.paid_amount + amount, save=False)
    order.save(update_fields=[
        'payment_reference',
        'payment_status',
        'paid_amount',
        'remaining_amount',
        'updated_at',
    ])

    OrderStatusHistory.objects.create(
        order=order,
        status=order.status,
        previous_status=order.status,
        changed_by=collected_by,
        notes=(
            f"Remaining payment of {amount} collected via {payment_method}. "
            f"Payment status changed from {old_payment_status} to {order.payment_status}."
        ),
    )

    if order.payment_status != old_payment_status:
        try:
            from apps.notifications.services import NotificationService
            NotificationService.send_payment_status_notification(
                order=order,
                old_status=old_payment_status,
                new_status=order.payment_status,
            )
        except Exception as exc:
            logger.error("Failed to send remaining payment notification: %s", str(exc))

    return old_payment_status


class OrderListView(APIView):
    permission_classes=[IsAuthenticated]

    @extend_schema(
        responses=OrderListSerializer(many=True),
        summary="List all orders",
        description="Get a list of all orders with optional filtering",
        tags=["Orders"]
    )
    def get(self,request):
        status_filter=request.query_params.get('status')
        customer_id=request.query_params.get('customer_id')
        tailor_id=request.query_params.get('tailor_id')
        payment_status=request.query_params.get('payment_status')

        queryset=Order.objects.select_related('customer','tailor','delivery_address').all()
        if status_filter:
            queryset=queryset.filter(status=status_filter)
        if customer_id:
            queryset=queryset.filter(customer_id=customer_id)
        if tailor_id:
            queryset=queryset.filter(tailor_id=tailor_id)
        if payment_status:
            queryset=queryset.filter(payment_status=payment_status)

        queryset=queryset.order_by('-created_at')

        serializer=OrderListSerializer(queryset,many=True,
            context={'request':request}
        )
        return api_response(
        success=True,
        message="Orders retrieved successfully",
        data=serializer.data,
        status_code=status.HTTP_200_OK
        )

class OrderCreateView(APIView):
    permission_classes=[IsAuthenticated]

    @extend_schema(
        request=OrderCreateSerializer,
        responses={201: OrderSerializer},
        summary="Create new order",
        description="Create a new order with items",
        tags=["Customer Orders"]
    )
    def post(self,request):
        # 1. Idempotency Check
        idempotency_key = request.headers.get('Idempotency-Key') or request.data.get('idempotency_key')
        if idempotency_key:
            existing_order = Order.objects.filter(idempotency_key=idempotency_key).first()
            if existing_order:
                # If retrying a successful request, just return the existing order
                response_serializer = OrderSerializer(existing_order, context={'request': request})
                return api_response(
                    success=True,
                    message="Order retrieved from previous successful request (Idempotent)",
                    data=response_serializer.data,
                    status_code=status.HTTP_200_OK
                )

        data=request.data.copy()
        if idempotency_key:
            data['idempotency_key'] = idempotency_key

        if not (request.user.is_admin or request.user.is_tailor):
            data['customer'] = request.user.id
        # For TAILOR and ADMIN, we respect the 'customer' ID passed in the request.
        # This ensures that when a tailor/admin creates an order, the correct customer is linked.
        serializer = OrderCreateSerializer(data=data, context={'request':request})
        if serializer.is_valid():
            try:
                order=serializer.save()
                response_serializer = OrderSerializer(order, context={'request':request})
                return api_response(
                success=True,
                message="Order created successfully",
                data=response_serializer.data,
                status_code=status.HTTP_201_CREATED)
            except ValidationError as e:
                return api_response(
                success=False,
                message="Order creation failed",
                errors={'detail': str(e)},
                status_code=status.HTTP_400_BAD_REQUEST
            )
            except Exception as e:
            # Edge Case: Unexpected errors
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Order creation error: {str(e)}", exc_info=True)
            
                return api_response(
                success=False,
                message="An error occurred while creating your order. Please try again.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        else:
            return api_response(
            success=False,
            message="Order creation failed",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )
        

class CheckoutCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=OrderCreateSerializer,
        responses={201: CheckoutSessionSerializer},
        summary="Create checkout session",
        description="Validate order data and return a bookingUniqueKey before creating a real order.",
        tags=["Checkout"]
    )
    def post(self, request):
        client_idempotency_key = (
            request.headers.get('Idempotency-Key')
            or request.data.get('client_idempotency_key')
            or request.data.get('idempotency_key')
        )

        if client_idempotency_key:
            existing_checkout = CheckoutSession.objects.filter(
                customer=request.user,
                client_idempotency_key=client_idempotency_key,
            ).first()
            if existing_checkout:
                serializer = CheckoutSessionSerializer(existing_checkout, context={'request': request})
                return api_response(
                    success=True,
                    message="Checkout retrieved from previous request.",
                    data=serializer.data,
                    status_code=status.HTTP_200_OK
                )

        data = request.data.copy()
        if not request.user.is_admin:
            data['customer'] = request.user.id

        serializer = OrderCreateSerializer(data=data, context={'request': request})
        if not serializer.is_valid():
            return api_response(
                success=False,
                message="Checkout validation failed",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            pricing_snapshot = serializer.get_checkout_pricing_snapshot()
            checkout = CheckoutSession.objects.create(
                booking_unique_key=self._generate_booking_key(),
                customer=request.user,
                request_payload=self._json_safe_payload(data),
                pricing_snapshot=pricing_snapshot,
                client_idempotency_key=client_idempotency_key,
                expires_at=timezone.now() + timezone.timedelta(minutes=30),
            )
            response_serializer = CheckoutSessionSerializer(checkout, context={'request': request})
            return api_response(
                success=True,
                message="Checkout created successfully",
                data=response_serializer.data,
                status_code=status.HTTP_201_CREATED
            )
        except ValidationError as e:
            return api_response(
                success=False,
                message="Checkout validation failed",
                errors={'detail': str(e)},
                status_code=status.HTTP_400_BAD_REQUEST
            )

    def _generate_booking_key(self):
        while True:
            key = f"chk_{uuid.uuid4().hex[:24]}"
            if not CheckoutSession.objects.filter(booking_unique_key=key).exists():
                return key

    def _json_safe_payload(self, value):
        if isinstance(value, dict):
            return {key: self._json_safe_payload(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._json_safe_payload(item) for item in value]
        if hasattr(value, 'id'):
            return value.id
        return value


class CheckoutStatusView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: CheckoutSessionSerializer},
        summary="Get checkout status",
        description="Fetch checkout state by bookingUniqueKey.",
        tags=["Checkout"]
    )
    def get(self, request, booking_unique_key):
        checkout = get_object_or_404(
            CheckoutSession.objects.select_related('order'),
            booking_unique_key=booking_unique_key,
            customer=request.user,
        )
        if checkout.status == 'active' and checkout.is_expired:
            checkout.status = 'expired'
            checkout.save(update_fields=['status', 'updated_at'])

        serializer = CheckoutSessionSerializer(checkout, context={'request': request})
        return api_response(
            success=True,
            message="Checkout status retrieved successfully",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )


class CheckoutInitiatePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=CheckoutInitiatePaymentSerializer,
        responses={200: CheckoutInitiatePaymentResponseSerializer},
        summary="Initiate Alinma hosted payment",
        description="Create an Alinma hosted payment session for an existing checkout draft.",
        tags=["Checkout"]
    )
    @transaction.atomic
    def post(self, request):
        serializer = CheckoutInitiatePaymentSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(
                success=False,
                message="Invalid checkout payment initiation data",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        booking_key = serializer.validated_data['bookingUniqueKey']
        payment_option_key = serializer.validated_data.get('payment_option', 'full')
        checkout = get_object_or_404(
            CheckoutSession.objects.select_for_update(),
            booking_unique_key=booking_key,
            customer=request.user,
        )

        if checkout.order:
            return api_response(
                success=False,
                message="This checkout already has an order.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        if checkout.status not in {'active', 'payment_initiated'}:
            return api_response(
                success=False,
                message=f"Checkout is not active. Current status: {checkout.status}",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        if checkout.is_expired:
            checkout.status = 'expired'
            checkout.save(update_fields=['status', 'updated_at'])
            return api_response(
                success=False,
                message="Checkout has expired. Please create a new checkout.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        checkout_total = (checkout.pricing_snapshot or {}).get('total_amount', '0.00')
        selected_payment_option = get_payment_option(checkout_total, payment_option_key)
        if not selected_payment_option:
            return api_response(
                success=False,
                message=f"Payment option '{payment_option_key}' is not available for this checkout total.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        pay_now_amount = money(selected_payment_option['pay_now_amount'])
        if pay_now_amount <= Decimal('0.00'):
            return api_response(
                success=False,
                message="This payment option does not require online payment.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        request_payload = checkout.request_payload or {}
        customer_payload = _build_alinma_customer_payload(checkout=checkout, user=request.user)

        try:
            config = get_alinma_config()
            receipt_url = f"{config.receipt_base_url.rstrip('/')}/api/orders/checkout/alinma/callback/"
            gateway_response = initiate_hosted_payment(
                track_id=booking_key,
                amount=str(pay_now_amount),
                order_id=booking_key,
                description=f'Checkout payment for {booking_key}',
                receipt_url=receipt_url,
                customer=customer_payload or None,
                user_data={
                    'bookingUniqueKey': booking_key,
                    'paymentOption': payment_option_key,
                    'customerId': request.user.id,
                    'orderType': request_payload.get('order_type'),
                },
            )
        except AlinmaConfigurationError as exc:
            return api_response(
                success=False,
                message=str(exc),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except AlinmaGatewayError as exc:
            return api_response(
                success=False,
                message=str(exc),
                status_code=status.HTTP_502_BAD_GATEWAY
            )

        gateway_transaction_id = str(gateway_response.get('transactionId') or '')
        link_url = ((gateway_response.get('paymentLink') or {}).get('linkUrl') or '').strip()
        if not gateway_transaction_id or not link_url:
            return api_response(
                success=False,
                message="Alinma Pay did not return a valid payment link.",
                status_code=status.HTTP_502_BAD_GATEWAY
            )

        checkout.status = 'payment_initiated'
        checkout.payment_method = 'credit_card'
        checkout.payment_option = payment_option_key
        checkout.save(update_fields=['status', 'payment_method', 'payment_option', 'updated_at'])

        return api_response(
            success=True,
            message="Alinma payment initiated successfully",
            data={
                'bookingUniqueKey': booking_key,
                'payment_option': payment_option_key,
                'gateway_transaction_id': gateway_transaction_id,
                'payment_url': f'{link_url}{gateway_transaction_id}',
                'amount': str(pay_now_amount),
                'currency': config.currency,
                'status': 'initiated',
            },
            status_code=status.HTTP_200_OK
        )


class CheckoutCreateOrderView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=CheckoutCreateOrderSerializer,
        responses={201: OrderSerializer},
        summary="Create order from checkout",
        description=(
            "Create the real order from a bookingUniqueKey for COD/pay-later checkouts. "
            "Credit card orders are created only by verified Alinma Pay callbacks."
        ),
        tags=["Checkout"]
    )
    @transaction.atomic
    def post(self, request):
        request_serializer = CheckoutCreateOrderSerializer(data=request.data)
        if not request_serializer.is_valid():
            return api_response(
                success=False,
                message="Invalid checkout order data",
                errors=request_serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        booking_key = request_serializer.validated_data['bookingUniqueKey']
        payment_method = request_serializer.validated_data['payment_method']
        payment_option_key = request_serializer.validated_data['payment_option']
        payment_reference = request_serializer.validated_data.get('payment_reference')

        checkout = get_object_or_404(
            CheckoutSession.objects.select_for_update(),
            booking_unique_key=booking_key,
            customer=request.user,
        )

        if checkout.order:
            response_serializer = OrderSerializer(checkout.order, context={'request': request})
            return api_response(
                success=True,
                message="Order retrieved from previous checkout request.",
                data=response_serializer.data,
                status_code=status.HTTP_200_OK
            )

        if checkout.status != 'active':
            return api_response(
                success=False,
                message=f"Checkout is not active. Current status: {checkout.status}",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        if checkout.is_expired:
            checkout.status = 'expired'
            checkout.save(update_fields=['status', 'updated_at'])
            return api_response(
                success=False,
                message="Checkout has expired. Please create a new checkout.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            order = _create_order_from_checkout(
                checkout=checkout,
                customer=request.user,
                payment_method=payment_method,
                payment_option_key=payment_option_key,
                payment_reference=payment_reference,
                collected_by=request.user,
                serializer_request=request,
            )
            response_serializer = OrderSerializer(order, context={'request': request})
            return api_response(
                success=True,
                message="Order created successfully from checkout",
                data=response_serializer.data,
                status_code=status.HTTP_201_CREATED
            )
        except ValidationError as e:
            transaction.set_rollback(True)
            return api_response(
                success=False,
                message="Order creation from checkout failed",
                errors={'detail': str(e)},
                status_code=status.HTTP_400_BAD_REQUEST
            )


class CheckoutAlinmaCallbackView(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = []

    @transaction.atomic
    def post(self, request):
        return self._handle(request)

    @transaction.atomic
    def get(self, request):
        return self._handle(request)

    def _handle(self, request):
        encrypted_data = request.data.get('data') or request.query_params.get('data')
        if not encrypted_data:
            return HttpResponse('Missing data', status=400)

        try:
            payload = parse_callback_payload(encrypted_data)
        except (AlinmaConfigurationError, AlinmaGatewayError, ValueError) as exc:
            logger.exception('Failed to parse Alinma callback')
            return HttpResponse(str(exc), status=400)

        if not payload.get('signature'):
            logger.warning('Rejected Alinma callback with missing signature')
            return HttpResponse('Missing signature', status=400)

        if not verify_callback_signature(payload):
            logger.warning('Rejected Alinma callback with invalid signature')
            return HttpResponse('Invalid signature', status=400)

        if not _verify_alinma_terminal(request, payload):
            logger.warning('Rejected Alinma callback with invalid terminal id')
            return HttpResponse('Invalid terminal', status=400)

        order_details = payload.get('orderDetails') or {}
        booking_key = order_details.get('orderId')

        if not booking_key:
            user_data_raw = ((payload.get('additionalDetails') or {}).get('userData') or '').strip()
            if user_data_raw:
                try:
                    user_data = json.loads(user_data_raw)
                    booking_key = user_data.get('bookingUniqueKey')
                except json.JSONDecodeError:
                    booking_key = None

        if not booking_key:
            return HttpResponse('Missing order reference', status=400)

        remaining_session = RemainingPaymentSession.objects.select_for_update().select_related(
            'order',
            'customer',
        ).filter(booking_unique_key=booking_key).first()
        if remaining_session:
            return self._handle_remaining_payment_callback(
                session=remaining_session,
                booking_key=booking_key,
                payload=payload,
            )

        checkout = CheckoutSession.objects.select_for_update().select_related('customer').filter(
            booking_unique_key=booking_key
        ).first()
        if not checkout:
            return HttpResponse('Checkout not found', status=404)

        if checkout.order:
            return HttpResponseRedirect(
                _build_alinma_return_redirect(
                    booking_key=booking_key,
                    status_value='success',
                    order_id=checkout.order_id,
                    payment_reference=checkout.payment_reference,
                )
            )

        transaction_id = str(payload.get('transactionId') or '')

        if is_successful_callback(payload):
            payment_option_key = checkout.payment_option or 'full'
            checkout_total = (checkout.pricing_snapshot or {}).get('total_amount', '0.00')
            selected_payment_option = get_payment_option(checkout_total, payment_option_key)
            if not selected_payment_option:
                logger.warning(
                    'Rejected Alinma callback for checkout %s with unavailable payment option %s',
                    booking_key,
                    payment_option_key,
                )
                checkout.status = 'payment_failed'
                checkout.save(update_fields=['status', 'updated_at'])
                return HttpResponseRedirect(
                    _build_alinma_return_redirect(
                        booking_key=booking_key,
                        status_value='failed',
                    )
                )

            expected_amount = money(selected_payment_option['pay_now_amount'])
            actual_amount = money(response_amount(payload))
            expected_currency = get_alinma_config().currency.upper()
            actual_currency = _payload_currency(payload)
            if actual_amount != expected_amount or actual_currency != expected_currency:
                logger.warning(
                    'Rejected Alinma callback for checkout %s due to amount/currency mismatch: expected=%s %s actual=%s %s',
                    booking_key,
                    expected_amount,
                    expected_currency,
                    actual_amount,
                    actual_currency or 'missing',
                )
                checkout.status = 'payment_failed'
                checkout.save(update_fields=['status', 'updated_at'])
                return HttpResponseRedirect(
                    _build_alinma_return_redirect(
                        booking_key=booking_key,
                        status_value='failed',
                    )
                )

            try:
                _create_order_from_checkout(
                    checkout=checkout,
                    customer=checkout.customer,
                    payment_method='credit_card',
                    payment_option_key=payment_option_key,
                    payment_reference=transaction_id or booking_key,
                    collected_by=None,
                    payment_metadata=_gateway_metadata(payload),
                )
            except ValidationError as exc:
                logger.exception('Failed to finalize checkout %s after successful Alinma callback', booking_key)
                checkout.status = 'payment_failed'
                checkout.save(update_fields=['status', 'updated_at'])
                return HttpResponseRedirect(
                    _build_alinma_return_redirect(
                        booking_key=booking_key,
                        status_value='failed',
                    )
                )
        else:
            logger.info(
                'Alinma checkout payment failed for %s: %s',
                booking_key,
                get_response_message(payload.get('responseCode'), payload.get('responseDescription')),
            )
            checkout.status = 'payment_failed'
            checkout.payment_method = 'credit_card'
            checkout.payment_reference = transaction_id or None
            checkout.save(update_fields=['status', 'payment_method', 'payment_reference', 'updated_at'])

        if checkout.order_id:
            return HttpResponseRedirect(
                _build_alinma_return_redirect(
                    booking_key=booking_key,
                    status_value='success',
                    order_id=checkout.order_id,
                    payment_reference=checkout.payment_reference,
                )
            )

        return HttpResponseRedirect(
            _build_alinma_return_redirect(
                booking_key=booking_key,
                status_value='failed',
                payment_reference=checkout.payment_reference,
            )
        )

    def _handle_remaining_payment_callback(self, *, session, booking_key, payload):
        if session.status == 'payment_completed':
            return HttpResponseRedirect(
                _build_alinma_return_redirect(
                    booking_key=booking_key,
                    status_value='success',
                    order_id=session.order_id,
                    payment_reference=session.payment_reference,
                )
            )

        transaction_id = str(payload.get('transactionId') or '')
        if is_successful_callback(payload):
            expected_amount = money(session.amount)
            actual_amount = money(response_amount(payload))
            expected_currency = session.currency.upper()
            actual_currency = _payload_currency(payload)
            if actual_amount != expected_amount or actual_currency != expected_currency:
                logger.warning(
                    'Rejected Alinma remaining payment callback %s due to amount/currency mismatch: expected=%s %s actual=%s %s',
                    booking_key,
                    expected_amount,
                    expected_currency,
                    actual_amount,
                    actual_currency or 'missing',
                )
                session.status = 'payment_failed'
                session.save(update_fields=['status', 'updated_at'])
                return HttpResponseRedirect(
                    _build_alinma_return_redirect(
                        booking_key=booking_key,
                        status_value='failed',
                    )
                )

            try:
                _record_remaining_payment(
                    order=session.order,
                    amount=expected_amount,
                    payment_method='credit_card',
                    payment_reference=transaction_id or booking_key,
                    collected_by=None,
                    notes='Remaining balance paid online via Alinma Pay.',
                    metadata={
                        'source': 'alinma_remaining_callback',
                        'session': booking_key,
                        **_gateway_metadata(payload),
                    },
                )
            except ValidationError:
                logger.exception('Failed to finalize remaining payment session %s after successful Alinma callback', booking_key)
                session.status = 'payment_failed'
                session.save(update_fields=['status', 'updated_at'])
                return HttpResponseRedirect(
                    _build_alinma_return_redirect(
                        booking_key=booking_key,
                        status_value='failed',
                    )
                )

            session.status = 'payment_completed'
            session.payment_reference = transaction_id or booking_key
            session.payment_confirmed_at = timezone.now()
            session.save(update_fields=[
                'status',
                'payment_reference',
                'payment_confirmed_at',
                'updated_at',
            ])
        else:
            logger.info(
                'Alinma remaining payment failed for %s: %s',
                booking_key,
                get_response_message(payload.get('responseCode'), payload.get('responseDescription')),
            )
            session.status = 'payment_failed'
            session.payment_reference = transaction_id or None
            session.save(update_fields=['status', 'payment_reference', 'updated_at'])

        if session.status == 'payment_completed':
            return HttpResponseRedirect(
                _build_alinma_return_redirect(
                    booking_key=booking_key,
                    status_value='success',
                    order_id=session.order_id,
                    payment_reference=session.payment_reference,
                )
            )

        return HttpResponseRedirect(
            _build_alinma_return_redirect(
                booking_key=booking_key,
                status_value='failed',
                payment_reference=session.payment_reference,
            )
        )


class OrderDetailView(APIView):
    """
    Retrieve, update or delete a specific order
    GET /api/orders/{id}/
    PUT /api/orders/{id}/
    DELETE /api/orders/{id}/
    """

    permission_classes=[IsAuthenticated]

    def get_object(self, order_id,request):

        order=get_object_or_404(
            Order.objects.select_related(
                'customer',
                'tailor',
                'delivery_address',
                'rider__rider_profile',
                'assigned_rider__rider_profile',
                'measurement_rider__rider_profile',
                'delivery_rider__rider_profile',
                'family_member',
            ).prefetch_related('order_items__fabric', 'order_items__family_member'),
            id=order_id
        )
        # Resource-based permission check
        is_customer = order.customer == request.user
        is_tailor = user_can_manage_shop_order(request.user, order)
        is_rider = (
            order.rider == request.user
            or order.assigned_rider == request.user
            or order.measurement_rider == request.user
            or order.delivery_rider == request.user
        )
        is_admin = request.user.is_admin

        if not (is_customer or is_tailor or is_rider or is_admin):
            raise PermissionError('You do not have permission to view this order')

        return order

    @extend_schema(
        responses=OrderSerializer,
        summary="Get order details",
        description="Retrieve detailed information about a specific order",
        tags=["Orders"]
    )

    def get(self, request, order_id):
        try:
            order=self.get_object(order_id,request)
            serializer=OrderSerializer(order, context={'request':request})
            return api_response(
            success=True,
            message="Order retrieved successfully",
            data=serializer.data,
            status_code=status.HTTP_200_OK
            )
        except PermissionError as e:
            return api_response(
                success=False,
                message=str(e),
                status_code=status.HTTP_403_FORBIDDEN
            )
    @extend_schema(
        request=OrderUpdateSerializer,
        responses=OrderSerializer,
        summary="Update order",
        description="Update order information (limited fields)",
        tags=["Orders"]
    )

    def put(self, request, order_id):
        try:
            order=self.get_object(order_id,request)
            
            # Role-based permission checks for status updates
            new_status = request.data.get('status')
            if new_status:
                if request.user.is_customer and order.customer == request.user:
                    # Customers can cancel orders OR mark walk-in orders as collected
                    if new_status == 'cancelled':
                        # Only allow cancellation when status is pending
                        if order.status != 'pending':
                            raise PermissionError("Orders can only be cancelled when status is pending")
                    elif new_status == 'collected':
                        # Allow customers to mark walk-in orders as collected
                        if order.service_mode != 'walk_in':
                            raise PermissionError("Only walk-in orders can be marked as collected by customers")
                        if order.status != 'ready_for_pickup':
                            raise PermissionError("Order must be ready for pickup before marking as collected")
                    else:
                        # Any other status change is not allowed
                        raise PermissionError("Customers can only cancel orders or mark walk-in orders as collected")
                        
                elif user_can_manage_shop_order(request.user, order):
                    # Tailors cannot cancel orders (only customers can cancel)
                    if new_status == 'cancelled':
                        raise PermissionError("Tailors cannot cancel orders. Only customers can cancel their orders.")
                    # Tailors cannot mark as collected (only customers can)
                    elif new_status == 'collected':
                        raise PermissionError("Only customers can mark walk-in orders as collected")
                        
                elif request.user.is_admin:
                    # Admins can do everything - no restrictions
                    pass
                else:
                    raise PermissionError("You do not have permission to update this order status")
            
            serializer=OrderUpdateSerializer(order,data=request.data, partial=True)
            if serializer.is_valid():
                updated_order=serializer.save()
                # Check if status was updated - if so, use lightweight response
                status_updated = 'status' in request.data or 'rider_status' in request.data or 'tailor_status' in request.data
                if status_updated:
                    response_serializer = OrderStatusUpdateResponseSerializer(updated_order,context={'request':request})
                else:
                    # For non-status updates, return full order details
                    response_serializer = OrderSerializer(updated_order,context={'request':request})
                return api_response(
                    success=True,
                    message="Order updated successfully",
                    data=response_serializer.data,
                    status_code=status.HTTP_200_OK
                )
            return api_response(
                success=False,
                message="Order update failed",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except PermissionError as e:
            return api_response(
                success=False,
                message=str(e),
                status_code=status.HTTP_403_FORBIDDEN
            )
    @extend_schema(
        summary="Delete order",
        description="Delete an order (only if status is pending)",
        tags=["Customer Orders"]
    )

    def delete(self,request, order_id):

        try:
            order=self.get_object(order_id,request)
            if order.status!='pending':
                return api_response(
                    success=False,
                    message="Only pending orders can be deleted",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            order.delete()
            return api_response(
                success=True,
                message="Order deleted successfully",
                status_code=status.HTTP_200_OK
            )
        except PermissionError as e:
            return api_response(
                success=False,
                message=str(e),
                status_code=status.HTTP_403_FORBIDDEN
            )

class OrderStatusUpdateView(APIView):

    permission_classes=[IsAuthenticated]
    @extend_schema(
        request=OrderUpdateSerializer,
        responses=OrderStatusUpdateResponseSerializer,
        summary="Update order status",
        description="Update order status with automatic history tracking. Returns lightweight response with only essential fields (id, order_number, status, rider_status, tailor_status, status_info, updated_at).",
        tags=["Orders"]
    )

    @transaction.atomic
    def patch(self, request, order_id):

        try:
            order=get_object_or_404(Order,id=order_id)
            
            # Role-based and Resource-based permission checks
            is_customer = order.customer == request.user
            is_tailor = user_can_manage_shop_order(request.user, order)
            is_admin = request.user.is_admin

            if is_customer:
                # Customers can cancel orders OR mark walk-in orders as collected
                new_status = request.data.get('status')
                if new_status:
                    if new_status == 'cancelled':
                        # Only allow cancellation when status is pending
                        if order.status != 'pending':
                            raise PermissionError("Orders can only be cancelled when status is pending")
                    elif new_status == 'collected':
                        # Allow customers to mark walk-in orders as collected
                        if order.service_mode != 'walk_in':
                            raise PermissionError("Only walk-in orders can be marked as collected by customers")
                        if order.status != 'ready_for_pickup':
                            raise PermissionError("Order must be ready for pickup before marking as collected")
                    else:
                        # Any other status change is not allowed
                        raise PermissionError("Customers can only cancel orders or mark walk-in orders as collected")
                    
            elif is_tailor:
                # Tailors cannot cancel orders (only customers can cancel)
                new_status = request.data.get('status')
                if new_status and new_status == 'cancelled':
                    raise PermissionError("Tailors cannot cancel orders. Only customers can cancel their orders.")
                # Tailors cannot mark as collected (only customers can)
                elif new_status == 'collected':
                    raise PermissionError("Only customers can mark walk-in orders as collected")
                    
            elif is_admin:
                # Admins can do everything - no restrictions
                pass
            else:
                raise PermissionError("You do not have permission to update this order status")
            
            serializer=OrderUpdateSerializer(order, data=request.data,partial=True, context={'request':request})
            if serializer.is_valid():
                updated_order=serializer.save()
                response_serializer=OrderStatusUpdateResponseSerializer(updated_order,context={'request': request})
                return api_response(
                    success=True,
                    message="Order status updated successfully",
                    data=response_serializer.data,
                    status_code=status.HTTP_200_OK
                )
            return api_response(
                success=False,
                message="Status update failed",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except PermissionError as e:
            return api_response(
                success=False,
                message=str(e),
                status_code=status.HTTP_403_FORBIDDEN
            )

class OrderHistoryView(APIView):

    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        responses=OrderStatusHistorySerializer(many=True),
        summary="Get order history",
        description="Retrieve status change history for an order",
        tags=["Orders"]
    )
    def get(self, request, order_id):
        try:
            order = get_object_or_404(Order, id=order_id)
            
            # Resource-based permission check
            is_customer = order.customer == request.user
            is_tailor = user_can_manage_shop_order(request.user, order)
            is_admin = request.user.is_admin

            if not (is_customer or is_tailor or is_admin):
                raise PermissionError("You do not have permission to view this order history")
            
            # Get status history
            history = OrderStatusHistory.objects.filter(order=order).order_by('-created_at')
            serializer = OrderStatusHistorySerializer(history, many=True)
            
            return api_response(
                success=True,
                message="Order history retrieved successfully",
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )
        except PermissionError as e:
            return api_response(
                success=False,
                message=str(e),
                status_code=status.HTTP_403_FORBIDDEN
            )


class CustomerOrderListView(APIView):

    permission_classes = [IsAuthenticated]
    @extend_schema(
        responses=OrderListSerializer(many=True),
        summary="Get my orders",
        description="Retrieve all orders for the authenticated customer",
        tags=["Customer Orders"]
    )

    def get(self,request):
        orders = Order.objects.filter(customer=request.user).select_related('tailor', 'delivery_address').prefetch_related('order_items__fabric').order_by('-created_at')
        status_filter=request.query_params.get('status')
        if status_filter:
            orders=orders.filter(status=status_filter)
        serializer = OrderListSerializer(orders, many=True, context={'request': request})
        
        return api_response(
            success=True,
            message="Your orders retrieved successfully",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )
class TailorAvailableOrdersView(APIView):
    """Get all non-completed orders assigned to tailor (includes both pending and accepted orders)"""
    permission_classes=[IsAuthenticated, IsShopStaff]
    required_employee_permission = 'can_manage_orders'
    
    @extend_schema(
        responses=OrderListSerializer(many=True),
        summary="Get available orders for tailor",
        description="Retrieve all non-completed orders assigned to tailor (excludes 'delivered' and 'cancelled' statuses). Includes both pending orders and orders that tailor has already accepted, allowing frontend to manage all active orders in one screen.",
        tags=["Tailor Orders"]
    )
    def get(self, request):
        tailor_user = _get_tailor_owner_user(request)
        if not tailor_user:
            return api_response(
                success=False,
                message="User is not a tailor",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        # Show all orders that are not completed yet (exclude delivered and cancelled)
        orders = Order.objects.filter(
            tailor=tailor_user
        ).exclude(
            status__in=['delivered', 'cancelled']
        ).select_related(
            'customer',
            'delivery_address',
            'rider__rider_profile',
            'assigned_rider__rider_profile',
            'measurement_rider__rider_profile',
            'delivery_rider__rider_profile',
        ).prefetch_related('order_items__fabric').order_by('-created_at')
        
        # Filter by payment status
        payment_status = request.query_params.get('payment_status')
        if payment_status:
            orders = orders.filter(payment_status=payment_status)
        
        # Filter by order type
        order_type = request.query_params.get('order_type')
        if order_type:
            orders = orders.filter(order_type=order_type)
            
        serializer = OrderListSerializer(orders, many=True, context={'request': request, 'role': 'TAILOR'})
        
        return api_response(
            success=True,
            message="Available orders retrieved successfully",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )


class TailorOrderListView(APIView):
    permission_classes=[IsAuthenticated, IsShopStaff]
    required_employee_permission = 'can_manage_orders'
    @extend_schema(
        responses=OrderListSerializer(many=True),
        summary="Get my tailor orders",
        description="Retrieve all orders that tailor has accepted (tailor_status != 'none'). These are orders tailor is working on.",
        tags=["Tailor Orders"]
    )

    def get(self,request):
        tailor_user = _get_tailor_owner_user(request)
        if not tailor_user:
            return api_response(
                success=False,
                message="User is not a tailor",
                status_code=status.HTTP_400_BAD_REQUEST
            )
            
        # Base queryset: All orders for this tailor
        orders = Order.objects.filter(
            tailor=tailor_user
        ).select_related(
            'customer',
            'delivery_address',
            'rider__rider_profile',
            'assigned_rider__rider_profile',
            'measurement_rider__rider_profile',
            'delivery_rider__rider_profile',
        ).prefetch_related('order_items__fabric').order_by('-created_at')
        
        # Filters
        status_filter = request.query_params.get('status')
        tailor_status_filter = request.query_params.get('tailor_status')
        payment_status = request.query_params.get('payment_status')
        order_type = request.query_params.get('order_type')

        if status_filter:
            if status_filter == 'express':
                orders = orders.filter(is_express=True)
            else:
                orders = orders.filter(status=status_filter)
        elif not tailor_status_filter:
            # Default: Show active orders only (exclude completed/cancelled)
            # unless a specific tailor_status is requested
            orders = orders.exclude(status__in=['delivered', 'collected', 'cancelled'])
        
        if tailor_status_filter:
            orders = orders.filter(tailor_status=tailor_status_filter)
        
        if payment_status:
            orders = orders.filter(payment_status=payment_status)

        if order_type:
            orders = orders.filter(order_type=order_type)

        # Date based filters for dashboard alerts
        today = timezone.now().date()
        is_overdue = request.query_params.get('is_overdue')
        if is_overdue == 'true':
            orders = orders.filter(
                estimated_delivery_date__lt=today
            ).exclude(status__in=['delivered', 'collected', 'cancelled'])

        delivery_due = request.query_params.get('delivery_due')
        if delivery_due == 'today':
            orders = orders.filter(
                estimated_delivery_date=today
            ).exclude(status__in=['delivered', 'collected', 'cancelled'])
        elif delivery_due == 'week':
            week_end = today + timezone.timedelta(days=7)
            orders = orders.filter(
                estimated_delivery_date__gte=today,
                estimated_delivery_date__lte=week_end
            ).exclude(status__in=['delivered', 'collected', 'cancelled'])

        # New filters for action buckets
        service_mode_filter = request.query_params.get('service_mode')
        if service_mode_filter:
            orders = orders.filter(service_mode=service_mode_filter)
        
        exclude_ready = request.query_params.get('exclude_ready')
        if exclude_ready == 'true':
            orders = orders.exclude(status__in=['ready_for_delivery', 'ready_for_pickup', 'delivered', 'collected'])

        # Filter for orders that need measurements (usually for Shop Orders)
        needs_measurements = request.query_params.get('needs_measurements')
        if needs_measurements == 'true':
            orders = orders.filter(
                tailor_status='accepted'
            ).filter(
                Q(order_items__measurements={}) | Q(order_items__measurements__isnull=True)
            ).distinct()

        # New in_stitching filter for dashboard buckets
        in_stitching = request.query_params.get('in_stitching')
        if in_stitching == 'true':
            # Determine which statuses to include based on service_mode to match dashboard
            service_mode = request.query_params.get('service_mode')
            if service_mode == 'walk_in':
                # Shop orders include 'accepted' in the stitching bucket
                # BUT ONLY if they already have measurements
                # Those missing measurements are in the 'To Measure' bucket
                orders = orders.filter(
                    Q(tailor_status__in=['in_progress', 'stitching_started', 'stitched']) |
                    Q(tailor_status='accepted', order_type__in=['fabric_with_stitching', 'stitching_only'])
                ).exclude(
                    Q(tailor_status='accepted', order_items__measurements={}) |
                    Q(tailor_status='accepted', order_items__measurements__isnull=True)
                ).distinct()
            else:
                # Delivery orders separate 'accepted' into 'To Prepare' (Make Progress)
                stitching_statuses = ['in_progress', 'stitching_started', 'stitched']
                orders = orders.filter(tailor_status__in=stitching_statuses)
                
            orders = orders.exclude(status__in=['ready_for_delivery', 'ready_for_pickup', 'delivered', 'collected', 'cancelled'])
            
        serializer = OrderListSerializer(orders, many=True, context={'request': request, 'role': 'TAILOR'})
        
        return api_response(
            success=True,
            message="Your tailor orders retrieved successfully",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )


class TailorPaidOrdersView(APIView):
    """Get paid orders and pending COD orders for tailor"""
    permission_classes=[IsAuthenticated, IsShopStaff]
    required_employee_permission = 'can_manage_orders'
    
    @extend_schema(
        responses=OrderListSerializer(many=True),
        summary="Get processable orders",
        description="Retrieve paid orders and pending COD orders assigned to the authenticated tailor (ready for processing)",
        tags=["Tailor Orders"]
    )
    def get(self, request):
        tailor_user = _get_tailor_owner_user(request)
        if not tailor_user:
            return api_response(
                success=False,
                message="User is not a tailor",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        orders = Order.objects.filter(
            tailor=tailor_user,
        ).filter(
            Q(payment_status__in=['paid', 'partially_paid']) | Q(payment_method='cod', payment_status='pending')
        ).select_related(
            'customer',
            'delivery_address',
            'rider__rider_profile',
            'assigned_rider__rider_profile',
            'measurement_rider__rider_profile',
            'delivery_rider__rider_profile',
        ).prefetch_related('order_items').order_by('-created_at')
        
        # Filter by status if provided
        status_filter = request.query_params.get('status')
        if status_filter:
            orders = orders.filter(status=status_filter)
        
        # Filter by order type if provided
        order_type = request.query_params.get('order_type')
        if order_type:
            orders = orders.filter(order_type=order_type)
            
        serializer = OrderListSerializer(orders, many=True, context={'request': request, 'role': 'TAILOR'})
        
        return api_response(
            success=True,
            message="Processable orders retrieved successfully",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )


class TailorOrderDetailView(APIView):
    """Get detailed order information for tailor including rider measurements"""
    permission_classes=[IsAuthenticated, IsShopStaff]
    required_employee_permission = 'can_manage_orders'
    
    @extend_schema(
        responses=OrderSerializer,
        summary="Get order details",
        description="Retrieve detailed information about a specific order including rider measurements",
        tags=["Tailor Orders"]
    )
    def get(self, request, order_id):
        tailor_user = _get_tailor_owner_user(request)
        if not tailor_user:
            return api_response(
                success=False,
                message="User is not a tailor",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        order = get_object_or_404(
            Order.objects.select_related(
                'customer',
                'delivery_address',
                'rider__rider_profile',
                'assigned_rider__rider_profile',
                'measurement_rider__rider_profile',
                'delivery_rider__rider_profile',
                'family_member'
            ).prefetch_related('order_items__fabric', 'status_history'),
            id=order_id,
            tailor=tailor_user
        )
        
        serializer = OrderSerializer(order, context={'request': request, 'role': 'TAILOR'})
        
        return api_response(
            success=True,
            message="Order details retrieved successfully",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )


class OrderPaymentStatusUpdateView(APIView):
    permission_classes=[IsAuthenticated]
    @extend_schema(
        request=OrderPaymentStatusUpdateSerializer,
        responses=OrderSerializer,
        summary="Update payment status",
        description="Update order payment status after payment success",
        tags=["Customer Orders"]
    )
    def patch(self, request, order_id):
        try:
            order = get_object_or_404(Order, id=order_id)
            
            # Permission checks
            if request.user.is_customer:
                if order.customer != request.user:
                    raise PermissionError('You can only update payment status of your own orders')
            elif request.user.is_admin:
                # Admins can update any order's payment status
                pass
            else:
                # Tailors and other roles cannot update payment status
                raise PermissionError('Only customers and admins can update payment status')
            
            # Validate request data using serializer
            serializer = OrderPaymentStatusUpdateSerializer(data=request.data)
            if not serializer.is_valid():
                return api_response(
                    success=False,
                    message="Invalid payment status data",
                    errors=serializer.errors,
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            payment_status = serializer.validated_data['payment_status']
            current_payment_status = order.payment_status
            
            # Business logic validation
            if current_payment_status == 'refunded':
                return api_response(
                    success=False,
                    message="Cannot change payment status of refunded orders",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            if current_payment_status == 'paid' and payment_status == 'pending':
                return api_response(
                    success=False,
                    message="Cannot change payment status from paid to pending",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Update payment status
            old_payment_status = order.payment_status
            order.payment_status = payment_status
            order.save(update_fields=['payment_status'])

            OrderStatusHistory.objects.create(
                order=order,
                status=order.status,
                previous_status=order.status,
                changed_by=request.user,
                notes=f"Payment status changed from {old_payment_status} to {payment_status}"
            )

            # Send push notification for payment status change
            try:
                from apps.notifications.services import NotificationService
                NotificationService.send_payment_status_notification(
                    order=order,
                    old_status=old_payment_status,
                    new_status=payment_status
                )
            except Exception as e:
                # Log error but don't fail the update
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to send payment status notification: {str(e)}")

            response_serializer=OrderSerializer(order, context={'request':request})
            return api_response(
                success=True,
                message="Payment status updated successfully",
                data=response_serializer.data,
                status_code=status.HTTP_200_OK

            )
        except Http404:
            return api_response(
                success=False,
                message="Order not found",
                status_code=status.HTTP_404_NOT_FOUND
            )
        except PermissionError as e:
            return api_response(
                success=False,
                message=str(e),
                status_code=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            import logging
            logger=logging.getLogger(__name__)
            logger.error(f'Payment status update error : {str(e)}', exc_info=True)
            return api_response(
                success=False,
                message="Something went wrong while updating payment status",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PayRemainingBalanceView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=PayRemainingBalanceSerializer,
        responses={200: OrderSerializer},
        summary="Pay remaining order balance",
        description=(
            "Confirm a customer/admin online payment for the current remaining "
            "balance. The backend uses order.remaining_amount and does not accept "
            "an amount from the frontend."
        ),
        tags=["Customer Orders"]
    )
    @transaction.atomic
    def post(self, request, order_id):
        order = get_object_or_404(Order.objects.select_for_update(), id=order_id)

        if not request.user.is_admin and order.customer != request.user:
            return api_response(
                success=False,
                message="You can only pay remaining balance for your own order.",
                status_code=status.HTTP_403_FORBIDDEN
            )

        serializer = PayRemainingBalanceSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(
                success=False,
                message="Invalid remaining payment data",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        if order.status == 'cancelled':
            return api_response(
                success=False,
                message="Cannot pay remaining balance for a cancelled order.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        if order.payment_status == 'refunded':
            return api_response(
                success=False,
                message="Cannot pay remaining balance for a refunded order.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        if not order.has_remaining_balance:
            return api_response(
                success=False,
                message="No remaining balance to pay.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        payment_method = serializer.validated_data['payment_method']
        payment_reference = serializer.validated_data['payment_reference']

        amount = money(order.remaining_amount)
        try:
            _record_remaining_payment(
                order=order,
                amount=amount,
                payment_method=payment_method,
                payment_reference=payment_reference,
                collected_by=request.user,
                notes='Remaining balance paid by bank transfer.',
                metadata={'source': 'manual_remaining_payment_endpoint'},
            )
        except ValidationError as exc:
            return api_response(
                success=False,
                message="Remaining payment failed.",
                errors={'detail': str(exc)},
                status_code=status.HTTP_400_BAD_REQUEST
            )

        response_serializer = OrderSerializer(order, context={'request': request})
        return api_response(
            success=True,
            message="Remaining payment paid successfully.",
            data=response_serializer.data,
            status_code=status.HTTP_200_OK
        )


class RemainingBalanceInitiatePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, order_id):
        order = get_object_or_404(Order.objects.select_for_update(), id=order_id)

        if not request.user.is_admin and order.customer != request.user:
            return api_response(
                success=False,
                message="You can only pay remaining balance for your own order.",
                status_code=status.HTTP_403_FORBIDDEN
            )

        if order.status == 'cancelled':
            return api_response(
                success=False,
                message="Cannot pay remaining balance for a cancelled order.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        if order.payment_status == 'refunded':
            return api_response(
                success=False,
                message="Cannot pay remaining balance for a refunded order.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        if not order.has_remaining_balance:
            return api_response(
                success=False,
                message="No remaining balance to pay.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        amount = money(order.remaining_amount)
        session = RemainingPaymentSession.objects.create(
            booking_unique_key=self._generate_booking_key(),
            customer=order.customer,
            order=order,
            status='active',
            amount=amount,
            currency=getattr(settings, 'ALINMAPAY_CURRENCY', 'SAR'),
            expires_at=timezone.now() + timezone.timedelta(minutes=30),
        )

        try:
            config = get_alinma_config()
            receipt_url = f"{config.receipt_base_url.rstrip('/')}/api/orders/checkout/alinma/callback/"
            gateway_response = initiate_hosted_payment(
                track_id=session.booking_unique_key,
                amount=str(amount),
                order_id=session.booking_unique_key,
                description=f'Remaining payment for order {order.order_number}',
                receipt_url=receipt_url,
                customer=_build_alinma_customer_payload(checkout=None, user=order.customer),
                user_data={
                    'bookingUniqueKey': session.booking_unique_key,
                    'paymentType': 'remaining_balance',
                    'orderId': order.id,
                    'customerId': order.customer_id,
                },
            )
        except AlinmaConfigurationError as exc:
            return api_response(
                success=False,
                message=str(exc),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except AlinmaGatewayError as exc:
            return api_response(
                success=False,
                message=str(exc),
                status_code=status.HTTP_502_BAD_GATEWAY
            )

        gateway_transaction_id = str(gateway_response.get('transactionId') or '')
        link_url = ((gateway_response.get('paymentLink') or {}).get('linkUrl') or '').strip()
        if not gateway_transaction_id or not link_url:
            return api_response(
                success=False,
                message="Alinma Pay did not return a valid payment link.",
                status_code=status.HTTP_502_BAD_GATEWAY
            )

        session.status = 'payment_initiated'
        session.save(update_fields=['status', 'updated_at'])

        return api_response(
            success=True,
            message="Alinma remaining payment initiated successfully",
            data={
                'bookingUniqueKey': session.booking_unique_key,
                'payment_option': 'remaining_balance',
                'gateway_transaction_id': gateway_transaction_id,
                'payment_url': f'{link_url}{gateway_transaction_id}',
                'amount': str(amount),
                'currency': config.currency,
                'status': 'initiated',
            },
            status_code=status.HTTP_200_OK
        )

    def _generate_booking_key(self):
        while True:
            key = f"rem_{uuid.uuid4().hex[:24]}"
            if not RemainingPaymentSession.objects.filter(booking_unique_key=key).exists():
                return key


class RemainingPaymentStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, booking_unique_key):
        session = get_object_or_404(
            RemainingPaymentSession.objects.select_related('order', 'customer'),
            booking_unique_key=booking_unique_key,
            customer=request.user,
        )

        if session.status in {'active', 'payment_initiated'} and session.is_expired:
            session.status = 'expired'
            session.save(update_fields=['status', 'updated_at'])

        frontend_status = 'order_created' if session.status == 'payment_completed' else session.status
        return api_response(
            success=True,
            message="Remaining payment status retrieved successfully",
            data={
                'bookingUniqueKey': session.booking_unique_key,
                'status': frontend_status,
                'pricing_summary': {'total_amount': str(session.amount)},
                'expires_at': session.expires_at.isoformat(),
                'payment_method': 'credit_card',
                'payment_plan': session.order.payment_plan,
                'payment_option': 'remaining_balance',
                'payment_reference': session.payment_reference,
                'order_id': session.order_id,
            },
            status_code=status.HTTP_200_OK
        )


class OrderMeasurementsDetailView(APIView):
    """Get measurements for a specific order"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Get order measurements",
        description="Retrieve measurements for a specific order. Only available when rider_status is 'measurement_taken'.",
        tags=["Customer Measurements"]
    )
    def get(self, request, order_id):
        if not (request.user.is_customer or request.user.is_admin):
            return api_response(
                success=False,
                message="Only customers can access this endpoint",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        # Get order and verify it belongs to customer
        order = get_object_or_404(Order, id=order_id)
        
        if order.customer != request.user:
            return api_response(
                success=False,
                message="You can only view measurements for your own orders",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        # Check if measurements are available
        if order.rider_status != 'measurement_taken' or not order.rider_measurements:
            return api_response(
                success=False,
                message="No measurements available for this order. Measurements are only available when rider_status is 'measurement_taken'.",
                data={
                    'order_id': order.id,
                    'order_number': order.order_number,
                    'rider_status': order.rider_status,
                    'has_measurements': False
                },
                status_code=status.HTTP_200_OK
            )
        
        # Build recipient data (consistent with order detail API)
        if order.family_member:
            recipient = {
                'type': 'family_member',
                'id': order.family_member.id,
                'name': order.family_member.name,
                'relationship': order.family_member.relationship,
                'gender': order.family_member.gender,
                'measurements': order.rider_measurements,
            }
        else:
            recipient = {
                'type': 'customer',
                'id': request.user.id,
                'name': request.user.get_full_name() or request.user.username,
                'phone': request.user.phone,
                'email': request.user.email,
                'measurements': order.rider_measurements,
            }
        
        # Get rider info
        measurement_taken_by = None
        if order.rider:
            try:
                if hasattr(order.rider, 'rider_profile') and order.rider.rider_profile:
                    measurement_taken_by = {
                        'rider_id': order.rider.id,
                        'rider_name': order.rider.rider_profile.full_name or order.rider.username,
                    }
                else:
                    measurement_taken_by = {
                        'rider_id': order.rider.id,
                        'rider_name': order.rider.username,
                    }
            except:
                measurement_taken_by = {
                    'rider_id': order.rider.id,
                    'rider_name': order.rider.username if order.rider else None,
                }
        
        response_data = {
            'order_id': order.id,
            'order_number': order.order_number,
            'order_type': order.order_type,
            'order_status': order.status,
            'rider_status': order.rider_status,
            'recipient': recipient,
            'measurement_taken_at': order.measurement_taken_at.isoformat() if order.measurement_taken_at else None,
            'measurement_taken_by': measurement_taken_by,
            'has_measurements': True,
        }
        
        return api_response(
            success=True,
            message="Order measurements retrieved successfully",
            data=response_data,
            status_code=status.HTTP_200_OK
        )







class WorkOrderPDFView(APIView):
    """Generate and download work order PDF for tailors"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, order_id):
        from django.http import HttpResponse
        from .pdf_service import WorkOrderPDFService
        
        try:
            order = Order.objects.select_related('customer', 'tailor').prefetch_related(
                'order_items__fabric',
                'order_items__customization',
                'order_items__customization__collar_style',
                'order_items__customization__cuff_style',
                'order_items__customization__pocket_style',
            ).get(id=order_id)
        except Order.DoesNotExist:
            return api_response(success=False, message='Order not found',
                              status_code=status.HTTP_404_NOT_FOUND, request=request)
        
        if not user_can_manage_shop_order(request.user, order):
            return api_response(success=False,
                              message='You do not have permission to access this work order',
                              status_code=status.HTTP_403_FORBIDDEN, request=request)
        
        language = request.GET.get('lang', 'ar')
        if language not in ['ar', 'en']:
            language = 'ar'
        
        try:
            pdf_service = WorkOrderPDFService(order, language=language)
            pdf_bytes = pdf_service.generate()
            
            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            filename = f'work_order_{order.order_number}_{language}.pdf'
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error generating PDF: {str(e)}")
            return api_response(success=False, message='Error generating work order PDF',
                              errors=str(e), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                              request=request)

class OrderActionView(APIView):
    """
    Unified endpoint for performing actions on an order.
    POST /api/orders/{id}/action/
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Perform order action",
        description=(
            "Generic endpoint to perform various actions on an order (e.g., accept, "
            "record_measurements, pickup). For record_measurements, send data as "
            "{unit: 'cm'|'inches', family_member: int|null, measurements: object}. "
            "Unit defaults to cm when omitted. For start_stitching, "
            "you can pass stitching_completion_date and stitching_completion_time."
        ),
        tags=["Orders"]
    )
    @transaction.atomic
    def post(self, request, order_id):
        order = get_object_or_404(Order, id=order_id)
        action_key = request.data.get('action')
        action_data = request.data.get('data', {})

        if not action_key:
            return api_response(
                success=False,
                message="Action key is required.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            # 1. Get Action instance
            requested_role = request.data.get('role')
            action = OrderActionManager.get_action(
                action_key,
                order,
                request.user,
                action_data,
                requested_role=requested_role,
                request=request,
            )
            
            # 2. Validate (Role and State)
            action.validate()
            
            # 3. Execute logic
            result_msg = action.execute()
            
            # 4. Run post-execution tasks
            action.post_execute()

            # Return success response with updated order info and refreshed actions.
            response_serializer = OrderStatusUpdateResponseSerializer(order, context={'request': request})
            response_data = dict(response_serializer.data)
            status_info = response_data.get('status_info') or {}
            response_data['payment_method'] = order.payment_method
            response_data['payment_plan'] = order.payment_plan
            response_data['payment_option'] = order.payment_option
            response_data['payment_status'] = order.payment_status
            response_data['total_amount'] = str(order.total_amount)
            response_data['paid_amount'] = str(order.paid_amount)
            response_data['remaining_amount'] = str(order.remaining_amount)
            response_data['available_actions'] = status_info.get('available_actions', [])
            response_data['measurement_status'] = self._build_measurement_status(order)
            return api_response(
                success=True,
                message=result_msg or "Action performed successfully.",
                data=response_data,
                status_code=status.HTTP_200_OK
            )

        except ValidationError as e:
            return api_response(
                success=False,
                message=str(e.detail[0] if isinstance(e.detail, list) else e.detail),
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except PermissionDenied as e:
            return api_response(
                success=False,
                message=str(e),
                status_code=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Action error ({action_key}): {str(e)}", exc_info=True)
            return api_response(
                success=False,
                message="An unexpected error occurred while performing the action.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _build_measurement_status(self, order):
        """Build measurement summary for action responses."""
        if order.order_type not in ['fabric_with_stitching', 'stitching_only', 'measurement_service']:
            return None

        from django.db.models import Q
        items = order.order_items.select_related('family_member')
        total_items = items.count()
        measured_items = items.exclude(Q(measurements__isnull=True) | Q(measurements={})).count()
        remaining_items = total_items - measured_items

        pending_recipients = []
        seen_keys = set()
        pending_items = items.filter(Q(measurements__isnull=True) | Q(measurements={}))
        for item in pending_items:
            if item.family_member:
                key = f"family_member_{item.family_member_id}"
                if key in seen_keys:
                    continue
                pending_recipients.append({
                    'type': 'family_member',
                    'id': item.family_member_id,
                    'name': item.family_member.name,
                })
                seen_keys.add(key)
            else:
                key = f"customer_{order.customer_id}"
                if key in seen_keys:
                    continue
                pending_recipients.append({
                    'type': 'customer',
                    'id': order.customer_id,
                    'name': order.customer.get_full_name() or order.customer.username,
                })
                seen_keys.add(key)

        return {
            'all_measured': order.all_items_have_measurements,
            'total_items': total_items,
            'measured_items': measured_items,
            'remaining_items': remaining_items,
            'remaining_recipients': pending_recipients,
        }
