from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db.models import Q
from drf_spectacular.utils import extend_schema
from .models import Order, OrderItem ,OrderStatusHistory
from .serializers import(
OrderItemSerializer,
OrderItemCreateSerializer,
OrderSerializer,
OrderCreateSerializer,
OrderUpdateSerializer,
OrderListSerializer,
OrderStatusHistorySerializer,
OrderPaymentStatusUpdateSerializer,
)
from apps.tailors.models import TailorProfile
from apps.customers.models import CustomerProfile
from zthob.utils import api_response 

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

        data=request.data.copy()
        data['customer'] = request.user.id
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
            except serializer.ValidationError as e:
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
        if request.user.role == 'USER':
            if order.customer != request.user:
                raise PermissionError('You can only view your own orders')

        elif request.user.role == 'TAILOR':
            if order.tailor != request.user:
                raise PermissionError('You can only view order that is assigned to you')

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
                if request.user.role == 'USER':
                    # Customers can only cancel orders (pending -> cancelled)
                    if new_status != 'cancelled':
                        raise PermissionError("Customers can only cancel orders. Only tailors can update order status.")
                    
                    # Only allow cancellation when status is pending
                    if new_status == 'cancelled' and order.status != 'pending':
                        raise PermissionError("Orders can only be cancelled when status is pending")
                        
                elif request.user.role == 'TAILOR':
                    # Tailors cannot cancel orders (only customers can cancel)
                    if new_status == 'cancelled':
                        raise PermissionError("Tailors cannot cancel orders. Only customers can cancel their orders.")
                        
                elif request.user.role == 'ADMIN':
                    # Admins can do everything - no restrictions
                    pass
                else:
                    raise PermissionError("Invalid user role")
            
            serializer=OrderUpdateSerializer(order,data=request.data, partial=True)
            if serializer.is_valid():
                updated_order=serializer.save()
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
        responses=OrderSerializer,
        summary="Update order status",
        description="Update order status with automatic history tracking",
        tags=["Orders"]
    )

    def patch(self, request, order_id):

        try:
            order=get_object_or_404(Order,id=order_id)
            
            # Role-based permission checks
            if request.user.role == 'USER':
                # Customers can only update their own orders
                if order.customer != request.user:
                    raise PermissionError("You can only update your own orders")
                
                # Customers can only cancel orders (pending -> cancelled)
                new_status = request.data.get('status')
                if new_status and new_status != 'cancelled':
                    raise PermissionError("Customers can only cancel orders. Only tailors can update order status.")
                
                # Only allow cancellation when status is pending
                if new_status == 'cancelled' and order.status != 'pending':
                    raise PermissionError("Orders can only be cancelled when status is pending")
                    
            elif request.user.role == 'TAILOR':
                # Tailors can only update orders assigned to them
                if order.tailor != request.user:
                    raise PermissionError("You can only update orders assigned to you")
                
                # Tailors cannot cancel orders (only customers can cancel)
                new_status = request.data.get('status')
                if new_status and new_status == 'cancelled':
                    raise PermissionError("Tailors cannot cancel orders. Only customers can cancel their orders.")
                    
            elif request.user.role == 'ADMIN':
                # Admins can do everything - no restrictions
                pass
            else:
                raise PermissionError("Invalid user role")
            
            serializer=OrderUpdateSerializer(order, data=request.data,partial=True, context={'request':request})
            if serializer.is_valid():
                updated_order=serializer.save()
                response_serializer=OrderSerializer(updated_order,context={'request': request})
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
            
            # Check permissions
            if request.user.role == 'USER':
                if order.customer != request.user:
                    raise PermissionError("You can only view your own order history")
            elif request.user.role == 'TAILOR':
                if order.tailor != request.user:
                    raise PermissionError("You can only view history for orders assigned to you")
            
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
        orders = Order.objects.filter(customer=request.user).select_related('tailor', 'delivery_address').order_by('-created_at')
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
class TailorOrderListView(APIView):
    permission_classes=[IsAuthenticated]
    @extend_schema(
        responses=OrderListSerializer(many=True),
        summary="Get my tailor orders",
        description="Retrieve all orders assigned to the authenticated tailor. Filter by payment_status=paid to see only paid orders.",
        tags=["Tailor Orders"]
    )

    def get(self,request):
        try:
            tailor_profile = TailorProfile.objects.get(user=request.user)
            orders = Order.objects.filter(tailor=request.user).select_related('customer', 'delivery_address', 'rider').prefetch_related('order_items').order_by('-created_at')
            
            # Filter by payment status (default: show all, but can filter for paid only)
            payment_status = request.query_params.get('payment_status')
            if payment_status:
                orders = orders.filter(payment_status=payment_status)
            
            # Filter by order status
            status_filter = request.query_params.get('status')
            if status_filter:
                orders = orders.filter(status=status_filter)
            
            # Filter by order type
            order_type = request.query_params.get('order_type')
            if order_type:
                orders = orders.filter(order_type=order_type)
            
            serializer = OrderListSerializer(orders, many=True, context={'request': request})
            
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
    """Get orders with payment_status=paid for tailor"""
    permission_classes=[IsAuthenticated]
    
    @extend_schema(
        responses=OrderListSerializer(many=True),
        summary="Get paid orders",
        description="Retrieve all paid orders assigned to the authenticated tailor (ready for processing)",
        tags=["Tailor Orders"]
    )
    def get(self, request):
        try:
            tailor_profile = TailorProfile.objects.get(user=request.user)
            orders = Order.objects.filter(
                tailor=request.user,
                payment_status='paid'
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
            
            serializer = OrderListSerializer(orders, many=True, context={'request': request})
            
            return api_response(
                success=True,
                message="Paid orders retrieved successfully",
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
            
            serializer = OrderSerializer(order, context={'request': request})
            
            # Add rider measurements info if available
            data = serializer.data
            if order.rider_measurements:
                data['rider_measurements'] = order.rider_measurements
                data['measurement_taken_at'] = order.measurement_taken_at.isoformat() if order.measurement_taken_at else None
            
            return api_response(
                success=True,
                message="Order details retrieved successfully",
                data=data,
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
            if request.user.role == 'USER':
                if order.customer != request.user:
                    raise PermissionError('You can only update payment status of your own orders')
            elif request.user.role == 'ADMIN':
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

            response_serializer=OrderSerializer(order, context={'request':request})
            return api_response(
                success=True,
                message="Payment status updated successfully",
                data=response_serializer.data,
                status_code=status.HTTP_200_OK

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
                message="An error occurred while updating payment status",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )










