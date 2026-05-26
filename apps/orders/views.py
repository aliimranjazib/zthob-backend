from django.shortcuts import get_object_or_404, render
from django.http import Http404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import ValidationError, PermissionDenied
from .actions import OrderActionManager
from django.db.models import Q
from drf_spectacular.utils import extend_schema
from .models import CheckoutSession, Order, OrderItem ,OrderStatusHistory
from .serializers import(
OrderItemSerializer,
OrderItemCreateSerializer,
OrderSerializer,
OrderCreateSerializer,
OrderUpdateSerializer,
OrderListSerializer,
	OrderStatusHistorySerializer,
	OrderPaymentStatusUpdateSerializer,
	OrderStatusUpdateResponseSerializer,
    CheckoutCreateOrderSerializer,
    CheckoutSessionSerializer,
	)
from apps.tailors.models import TailorProfile
from apps.customers.models import CustomerProfile
from zthob.utils import api_response 
import uuid

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

        if not request.user.is_admin:
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


class CheckoutCreateOrderView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=CheckoutCreateOrderSerializer,
        responses={201: OrderSerializer},
        summary="Create order from checkout",
        description=(
            "Create the real order from a bookingUniqueKey. COD creates a pending-payment "
            "order. Credit card requires payment_reference and creates a paid order."
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
        payment_reference = request_serializer.validated_data.get('payment_reference')

        checkout = get_object_or_404(
            CheckoutSession.objects.select_for_update().select_related('order'),
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

        if payment_method == 'credit_card':
            reference_used = (
                Order.objects.filter(payment_reference=payment_reference).exists()
                or CheckoutSession.objects.filter(payment_reference=payment_reference).exclude(id=checkout.id).exists()
            )
            if reference_used:
                return api_response(
                    success=False,
                    message="This payment reference has already been used.",
                    status_code=status.HTTP_400_BAD_REQUEST
                )

        order_data = dict(checkout.request_payload)
        order_data['customer'] = request.user.id
        order_data['payment_method'] = payment_method

        order_serializer = OrderCreateSerializer(data=order_data, context={'request': request})
        if not order_serializer.is_valid():
            return api_response(
                success=False,
                message="Order creation from checkout failed",
                errors=order_serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            order = order_serializer.save()
            if payment_method == 'credit_card':
                order.payment_status = 'paid'
                order.payment_reference = payment_reference
                order.save(update_fields=['payment_status', 'payment_reference', 'updated_at'])
            elif payment_method == 'cod':
                order.payment_status = 'pending'
                order.payment_reference = None
                order.save(update_fields=['payment_status', 'payment_reference', 'updated_at'])

            checkout.order = order
            checkout.status = 'order_created'
            checkout.payment_method = payment_method
            checkout.payment_reference = payment_reference if payment_method == 'credit_card' else None
            checkout.payment_confirmed_at = timezone.now() if payment_method == 'credit_card' else None
            checkout.save(update_fields=[
                'order',
                'status',
                'payment_method',
                'payment_reference',
                'payment_confirmed_at',
                'updated_at',
            ])

            response_serializer = OrderSerializer(order, context={'request': request})
            return api_response(
                success=True,
                message="Order created successfully from checkout",
                data=response_serializer.data,
                status_code=status.HTTP_201_CREATED
            )
        except ValidationError as e:
            return api_response(
                success=False,
                message="Order creation from checkout failed",
                errors={'detail': str(e)},
                status_code=status.HTTP_400_BAD_REQUEST
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

        order=get_object_or_404(Order, id=order_id)
        # Resource-based permission check
        is_customer = order.customer == request.user
        is_tailor = order.tailor == request.user
        is_rider = order.rider == request.user
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
                        
                elif request.user.is_tailor and order.tailor == request.user:
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
            is_tailor = order.tailor == request.user
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
            is_tailor = order.tailor == request.user
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
    permission_classes=[IsAuthenticated]
    
    @extend_schema(
        responses=OrderListSerializer(many=True),
        summary="Get available orders for tailor",
        description="Retrieve all non-completed orders assigned to tailor (excludes 'delivered' and 'cancelled' statuses). Includes both pending orders and orders that tailor has already accepted, allowing frontend to manage all active orders in one screen.",
        tags=["Tailor Orders"]
    )
    def get(self, request):
        try:
            tailor_profile = TailorProfile.objects.get(user=request.user)
            # Show all orders that are not completed yet (exclude delivered and cancelled)
            orders = Order.objects.filter(
                tailor=request.user
            ).exclude(
                status__in=['delivered', 'cancelled']
            ).select_related('customer', 'delivery_address', 'rider').prefetch_related('order_items__fabric').order_by('-created_at')
            
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
        except TailorProfile.DoesNotExist:
            return api_response(
                success=False,
                message="User is not a tailor",
                status_code=status.HTTP_400_BAD_REQUEST
            )


class TailorOrderListView(APIView):
    permission_classes=[IsAuthenticated]
    @extend_schema(
        responses=OrderListSerializer(many=True),
        summary="Get my tailor orders",
        description="Retrieve all orders that tailor has accepted (tailor_status != 'none'). These are orders tailor is working on.",
        tags=["Tailor Orders"]
    )

    def get(self,request):
        try:
            tailor_profile = TailorProfile.objects.get(user=request.user)
            
            # Base queryset: All orders for this tailor
            orders = Order.objects.filter(
                tailor=request.user
            ).select_related('customer', 'delivery_address', 'rider').prefetch_related('order_items__fabric').order_by('-created_at')
            
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
                        Q(tailor_status='accepted', order_type='fabric_with_stitching')
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
        except TailorProfile.DoesNotExist:
            return api_response(
                success=False,
                message="User is not a tailor",
                status_code=status.HTTP_400_BAD_REQUEST
            )


class TailorPaidOrdersView(APIView):
    """Get paid orders and pending COD orders for tailor"""
    permission_classes=[IsAuthenticated]
    
    @extend_schema(
        responses=OrderListSerializer(many=True),
        summary="Get processable orders",
        description="Retrieve paid orders and pending COD orders assigned to the authenticated tailor (ready for processing)",
        tags=["Tailor Orders"]
    )
    def get(self, request):
        try:
            tailor_profile = TailorProfile.objects.get(user=request.user)
            orders = Order.objects.filter(
                tailor=request.user,
            ).filter(
                Q(payment_status='paid') | Q(payment_method='cod', payment_status='pending')
            ).select_related(
                'customer',
                'delivery_address',
                'rider'
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
        except TailorProfile.DoesNotExist:
            return api_response(
                success=False,
                message="User is not a tailor",
                status_code=status.HTTP_400_BAD_REQUEST
            )


class TailorOrderDetailView(APIView):
    """Get detailed order information for tailor including rider measurements"""
    permission_classes=[IsAuthenticated]
    
    @extend_schema(
        responses=OrderSerializer,
        summary="Get order details",
        description="Retrieve detailed information about a specific order including rider measurements",
        tags=["Tailor Orders"]
    )
    def get(self, request, order_id):
        try:
            tailor_profile = TailorProfile.objects.get(user=request.user)
            order = get_object_or_404(
                Order.objects.select_related(
                    'customer',
                    'delivery_address',
                    'rider',
                    'family_member'
                ).prefetch_related('order_items__fabric', 'status_history'),
                id=order_id,
                tailor=request.user
            )
            
            serializer = OrderSerializer(order, context={'request': request, 'role': 'TAILOR'})
            
            return api_response(
                success=True,
                message="Order details retrieved successfully",
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )
        except TailorProfile.DoesNotExist:
            return api_response(
                success=False,
                message="User is not a tailor",
                status_code=status.HTTP_400_BAD_REQUEST
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
        
        if not request.user.is_tailor or order.tailor != request.user:
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
            "{family_member: int|null, measurements: object}. For start_stitching, "
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
            action = OrderActionManager.get_action(action_key, order, request.user, action_data, requested_role=requested_role)
            
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
            response_data['payment_status'] = order.payment_status
            response_data['total_amount'] = str(order.total_amount)
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
        if order.order_type not in ['fabric_with_stitching', 'measurement_service']:
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
