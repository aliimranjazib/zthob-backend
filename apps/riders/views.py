from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q
from drf_spectacular.utils import extend_schema

from apps.accounts.models import CustomUser
from apps.orders.models import Order
from apps.core.services import PhoneVerificationService
from apps.core.serializers import PhoneVerificationSerializer, OTPVerificationSerializer
from .models import RiderProfile, RiderOrderAssignment, RiderProfileReview, RiderDocument
from .serializers import (
    RiderRegisterSerializer,
    RiderProfileSerializer,
    RiderProfileUpdateSerializer,
    RiderProfileSubmissionSerializer,
    RiderProfileStatusSerializer,
    RiderDocumentUploadSerializer,
    RiderDocumentSerializer,
    RiderOrderListSerializer,
    RiderOrderDetailSerializer,
    RiderAcceptOrderSerializer,
    RiderAddMeasurementsSerializer,
    RiderUpdateOrderStatusSerializer,
)
from rest_framework.parsers import MultiPartParser, FormParser
from zthob.utils import api_response
from rest_framework_simplejwt.tokens import RefreshToken


# ============================================================================
# AUTHENTICATION VIEWS
# ============================================================================

class RiderRegisterView(APIView):
    """Rider registration with phone verification"""
    permission_classes = [AllowAny]
    
    @extend_schema(
        request=RiderRegisterSerializer,
        summary="Register new rider",
        description="Register a new rider account. Phone verification required after registration.",
        tags=["Rider Authentication"]
    )
    def post(self, request):
        serializer = RiderRegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            
            return api_response(
                success=True,
                message="Rider registration successful. Please verify your phone number.",
                data={
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email,
                        'role': user.role,
                    },
                    'tokens': {
                        'refresh': str(refresh),
                        'access_token': str(refresh.access_token)
                    }
                },
                status_code=status.HTTP_201_CREATED
            )
        return api_response(
            success=False,
            message="Registration failed",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class RiderSendOTPView(APIView):
    """Send OTP to rider's phone number"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        request=PhoneVerificationSerializer,
        summary="Send OTP to rider phone",
        description="Send OTP code to rider's phone number for verification",
        tags=["Rider Authentication"]
    )
    def post(self, request):
        # Verify user is a rider
        if request.user.role != 'RIDER':
            return api_response(
                success=False,
                message="Only riders can use this endpoint",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        serializer = PhoneVerificationSerializer(data=request.data)
        if serializer.is_valid():
            phone_number = serializer.validated_data['phone_number']
            verification, otp_code = PhoneVerificationService.create_verification(
                user=request.user,
                phone_number=phone_number
            )
            
            # Update rider profile phone number
            try:
                rider_profile = request.user.rider_profile
                rider_profile.phone_number = phone_number
                rider_profile.save()
            except RiderProfile.DoesNotExist:
                pass
            
            return api_response(
                success=True,
                message=f"OTP sent to {phone_number}",
                data={"otp": otp_code}  # Remove in production!
            )
        return api_response(
            success=False,
            message="Invalid phone number",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class RiderVerifyOTPView(APIView):
    """Verify OTP code for rider"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        request=OTPVerificationSerializer,
        summary="Verify rider OTP",
        description="Verify OTP code sent to rider's phone number",
        tags=["Rider Authentication"]
    )
    def post(self, request):
        # Verify user is a rider
        if request.user.role != 'RIDER':
            return api_response(
                success=False,
                message="Only riders can use this endpoint",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        serializer = OTPVerificationSerializer(data=request.data)
        if serializer.is_valid():
            otp_code = serializer.validated_data['otp_code']
            is_valid, message = PhoneVerificationService.verify_otp(
                user=request.user,
                otp_code=otp_code
            )
            
            return api_response(
                success=is_valid,
                message=message
            )
        return api_response(
            success=False,
            message="Invalid OTP format",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )


# ============================================================================
# PROFILE VIEWS
# ============================================================================

class RiderProfileView(APIView):
    """Get and update rider profile"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        responses=RiderProfileSerializer,
        summary="Get rider profile",
        description="Retrieve authenticated rider's profile information",
        tags=["Rider Profile"]
    )
    def get(self, request):
        if request.user.role != 'RIDER':
            return api_response(
                success=False,
                message="Only riders can access this endpoint",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        try:
            rider_profile = request.user.rider_profile
            serializer = RiderProfileSerializer(rider_profile, context={'request': request})
            return api_response(
                success=True,
                message="Profile retrieved successfully",
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )
        except RiderProfile.DoesNotExist:
            return api_response(
                success=False,
                message="Rider profile not found. Please contact support.",
                status_code=status.HTTP_404_NOT_FOUND
            )
    
    @extend_schema(
        request=RiderProfileUpdateSerializer,
        responses=RiderProfileSerializer,
        summary="Update rider profile",
        description="Update authenticated rider's profile information",
        tags=["Rider Profile"]
    )
    def put(self, request):
        if request.user.role != 'RIDER':
            return api_response(
                success=False,
                message="Only riders can access this endpoint",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        try:
            rider_profile = request.user.rider_profile
            serializer = RiderProfileUpdateSerializer(rider_profile, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                response_serializer = RiderProfileSerializer(rider_profile, context={'request': request})
                return api_response(
                    success=True,
                    message="Profile updated successfully",
                    data=response_serializer.data,
                    status_code=status.HTTP_200_OK
                )
            return api_response(
                success=False,
                message="Profile update failed",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except RiderProfile.DoesNotExist:
            return api_response(
                success=False,
                message="Rider profile not found. Please contact support.",
                status_code=status.HTTP_404_NOT_FOUND
            )


class RiderProfileSubmissionView(APIView):
    """Submit rider profile for admin review"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        request=RiderProfileSubmissionSerializer,
        responses=RiderProfileSerializer,
        summary="Submit profile for review",
        description="Submit rider profile for admin review. Profile must be complete before submission.",
        tags=["Rider Profile"]
    )
    def post(self, request):
        if request.user.role != 'RIDER':
            return api_response(
                success=False,
                message="Only riders can access this endpoint",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        try:
            rider_profile = request.user.rider_profile
        except RiderProfile.DoesNotExist:
            return api_response(
                success=False,
                message="Rider profile not found. Please contact support.",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        serializer = RiderProfileSubmissionSerializer(rider_profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            
            # Create or update review record
            review, created = RiderProfileReview.objects.get_or_create(
                profile=rider_profile,
                defaults={
                    'review_status': 'pending',
                    'submitted_at': timezone.now()
                }
            )
            if not created:
                review.review_status = 'pending'
                review.submitted_at = timezone.now()
                review.rejection_reason = ''  # Clear previous rejection reason
                review.save()
            
            response_serializer = RiderProfileSerializer(rider_profile, context={'request': request})
            return api_response(
                success=True,
                message="Profile submitted for review successfully. Please wait for admin approval.",
                data=response_serializer.data,
                status_code=status.HTTP_200_OK
            )
        
        return api_response(
            success=False,
            message="Validation failed",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class RiderProfileStatusView(APIView):
    """Check rider profile review status"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        responses=RiderProfileStatusSerializer,
        summary="Check review status",
        description="Check the review status of your rider profile",
        tags=["Rider Profile"]
    )
    def get(self, request):
        if request.user.role != 'RIDER':
            return api_response(
                success=False,
                message="Only riders can access this endpoint",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        try:
            rider_profile = request.user.rider_profile
            review = rider_profile.review
            serializer = RiderProfileStatusSerializer(review)
            return api_response(
                success=True,
                message="Review status retrieved successfully",
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )
        except RiderProfile.DoesNotExist:
            return api_response(
                success=False,
                message="Rider profile not found",
                status_code=status.HTTP_404_NOT_FOUND
            )
        except RiderProfileReview.DoesNotExist:
            return api_response(
                success=False,
                message="Review record not found. Please submit your profile for review.",
                status_code=status.HTTP_404_NOT_FOUND
            )


class RiderDocumentUploadView(APIView):
    """Upload rider documents (Iqama, License, Istimara, Insurance)"""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    @extend_schema(
        request=RiderDocumentUploadSerializer,
        responses=RiderDocumentSerializer,
        summary="Upload document",
        description="Upload a rider document (Iqama front/back, License front/back, Istimara front/back, Insurance card)",
        tags=["Rider Profile"]
    )
    def post(self, request):
        if request.user.role != 'RIDER':
            return api_response(
                success=False,
                message="Only riders can access this endpoint",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        try:
            rider_profile = request.user.rider_profile
        except RiderProfile.DoesNotExist:
            return api_response(
                success=False,
                message="Rider profile not found. Please contact support.",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        serializer = RiderDocumentUploadSerializer(
            data=request.data,
            context={'rider_profile': rider_profile, 'request': request}
        )
        if serializer.is_valid():
            document = serializer.save()
            response_serializer = RiderDocumentSerializer(document, context={'request': request})
            return api_response(
                success=True,
                message="Document uploaded successfully",
                data=response_serializer.data,
                status_code=status.HTTP_201_CREATED
            )
        
        return api_response(
            success=False,
            message="Document upload failed",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class RiderDocumentListView(APIView):
    """List all documents for authenticated rider"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        responses=RiderDocumentSerializer(many=True),
        summary="List documents",
        description="Get all documents uploaded by the authenticated rider",
        tags=["Rider Profile"]
    )
    def get(self, request):
        if request.user.role != 'RIDER':
            return api_response(
                success=False,
                message="Only riders can access this endpoint",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        try:
            rider_profile = request.user.rider_profile
            documents = rider_profile.documents.all()
            serializer = RiderDocumentSerializer(documents, many=True, context={'request': request})
            return api_response(
                success=True,
                message="Documents retrieved successfully",
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )
        except RiderProfile.DoesNotExist:
            return api_response(
                success=False,
                message="Rider profile not found. Please contact support.",
                status_code=status.HTTP_404_NOT_FOUND
            )


class RiderDocumentDeleteView(APIView):
    """Delete a rider document"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Delete document",
        description="Delete a specific document uploaded by the authenticated rider",
        tags=["Rider Profile"]
    )
    def delete(self, request, document_id):
        if request.user.role != 'RIDER':
            return api_response(
                success=False,
                message="Only riders can access this endpoint",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        try:
            rider_profile = request.user.rider_profile
            document = get_object_or_404(
                RiderDocument,
                id=document_id,
                rider_profile=rider_profile
            )
            document.delete()
            return api_response(
                success=True,
                message="Document deleted successfully",
                status_code=status.HTTP_200_OK
            )
        except RiderProfile.DoesNotExist:
            return api_response(
                success=False,
                message="Rider profile not found. Please contact support.",
                status_code=status.HTTP_404_NOT_FOUND
            )


# ============================================================================
# ORDER MANAGEMENT VIEWS
# ============================================================================

class RiderAvailableOrdersView(APIView):
    """List orders available for riders (payment_status=paid, no rider assigned)"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        responses=RiderOrderListSerializer(many=True),
        summary="List available orders",
        description="Get list of orders available for riders (paid orders without assigned rider). Rider must be approved.",
        tags=["Rider Orders"]
    )
    def get(self, request):
        if request.user.role != 'RIDER':
            return api_response(
                success=False,
                message="Only riders can access this endpoint",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        # Check if rider is approved
        try:
            rider_profile = request.user.rider_profile
            if not rider_profile.is_approved:
                return api_response(
                    success=False,
                    message="Your profile must be approved by admin before you can accept orders. Current status: " + rider_profile.review_status,
                    status_code=status.HTTP_403_FORBIDDEN
                )
        except RiderProfile.DoesNotExist:
            return api_response(
                success=False,
                message="Rider profile not found. Please contact support.",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # Get orders that are paid and don't have a rider assigned
        orders = Order.objects.filter(
            payment_status='paid',
            rider__isnull=True
        ).select_related(
            'customer',
            'tailor',
            'delivery_address'
        ).prefetch_related('order_items').order_by('-created_at')
        
        # Filter by status if provided
        status_filter = request.query_params.get('status')
        if status_filter:
            orders = orders.filter(status=status_filter)
        
        # Filter by order type if provided
        order_type = request.query_params.get('order_type')
        if order_type:
            orders = orders.filter(order_type=order_type)
        
        serializer = RiderOrderListSerializer(orders, many=True)
        return api_response(
            success=True,
            message="Available orders retrieved successfully",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )


class RiderMyOrdersView(APIView):
    """List orders assigned to the authenticated rider"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        responses=RiderOrderListSerializer(many=True),
        summary="List my orders",
        description="Get list of orders assigned to the authenticated rider",
        tags=["Rider Orders"]
    )
    def get(self, request):
        if request.user.role != 'RIDER':
            return api_response(
                success=False,
                message="Only riders can access this endpoint",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        orders = Order.objects.filter(
            rider=request.user
        ).select_related(
            'customer',
            'tailor',
            'delivery_address'
        ).prefetch_related('order_items').order_by('-created_at')
        
        # Filter by status if provided
        status_filter = request.query_params.get('status')
        if status_filter:
            orders = orders.filter(status=status_filter)
        
        serializer = RiderOrderListSerializer(orders, many=True)
        return api_response(
            success=True,
            message="Your orders retrieved successfully",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )


class RiderOrderDetailView(APIView):
    """Get detailed information about a specific order"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        responses=RiderOrderDetailSerializer,
        summary="Get order details",
        description="Retrieve detailed information about a specific order",
        tags=["Rider Orders"]
    )
    def get(self, request, order_id):
        if request.user.role != 'RIDER':
            return api_response(
                success=False,
                message="Only riders can access this endpoint",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        order = get_object_or_404(
            Order.objects.select_related(
                'customer',
                'tailor',
                'delivery_address',
                'rider'
            ).prefetch_related('order_items__fabric'),
            id=order_id
        )
        
        # Check if rider has access (either assigned or available)
        if order.rider and order.rider != request.user:
            return api_response(
                success=False,
                message="You don't have access to this order",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        serializer = RiderOrderDetailSerializer(order)
        return api_response(
            success=True,
            message="Order details retrieved successfully",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )


class RiderAcceptOrderView(APIView):
    """Rider accepts an available order"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        request=RiderAcceptOrderSerializer,
        responses=RiderOrderDetailSerializer,
        summary="Accept order",
        description="Rider accepts an available order for delivery. Rider must be approved.",
        tags=["Rider Orders"]
    )
    def post(self, request):
        if request.user.role != 'RIDER':
            return api_response(
                success=False,
                message="Only riders can access this endpoint",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        # Check if rider is approved
        try:
            rider_profile = request.user.rider_profile
            if not rider_profile.is_approved:
                return api_response(
                    success=False,
                    message="Your profile must be approved by admin before you can accept orders. Current status: " + rider_profile.review_status,
                    status_code=status.HTTP_403_FORBIDDEN
                )
        except RiderProfile.DoesNotExist:
            return api_response(
                success=False,
                message="Rider profile not found. Please contact support.",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        serializer = RiderAcceptOrderSerializer(data=request.data)
        if serializer.is_valid():
            order_id = serializer.validated_data['order_id']
            order = get_object_or_404(Order, id=order_id)
            
            # Verify order is available
            if order.payment_status != 'paid':
                return api_response(
                    success=False,
                    message="Order payment must be paid before rider can accept it",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            if order.rider is not None:
                return api_response(
                    success=False,
                    message="Order is already assigned to another rider",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Assign rider to order
            order.rider = request.user
            order.save()
            
            # Create rider assignment record
            assignment = RiderOrderAssignment.objects.create(
                order=order,
                rider=request.user,
                status='accepted',
                accepted_at=timezone.now()
            )
            
            # Update order status based on order type
            if order.order_type == 'fabric_only':
                # For fabric_only: rider picks from tailor, so status stays as is
                pass
            elif order.order_type == 'fabric_with_stitching':
                # For fabric_with_stitching: rider needs to take measurements first
                if order.status == 'confirmed':
                    order.status = 'measuring'
                    order.save()
            
            response_serializer = RiderOrderDetailSerializer(order)
            return api_response(
                success=True,
                message="Order accepted successfully",
                data=response_serializer.data,
                status_code=status.HTTP_200_OK
            )
        
        return api_response(
            success=False,
            message="Failed to accept order",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class RiderAddMeasurementsView(APIView):
    """Rider adds measurements for fabric_with_stitching orders"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        request=RiderAddMeasurementsSerializer,
        responses=RiderOrderDetailSerializer,
        summary="Add measurements",
        description="Rider adds measurements taken at customer location (for fabric_with_stitching orders)",
        tags=["Rider Orders"]
    )
    def post(self, request, order_id):
        if request.user.role != 'RIDER':
            return api_response(
                success=False,
                message="Only riders can access this endpoint",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        order = get_object_or_404(Order, id=order_id)
        
        # Verify rider has access
        if order.rider != request.user:
            return api_response(
                success=False,
                message="You don't have access to this order",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        # Verify order type
        if order.order_type != 'fabric_with_stitching':
            return api_response(
                success=False,
                message="Measurements can only be added for fabric_with_stitching orders",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = RiderAddMeasurementsSerializer(data=request.data)
        if serializer.is_valid():
            # Store previous status
            previous_status = order.status
            
            # Add measurements to order
            order.rider_measurements = serializer.validated_data['measurements']
            order.measurement_taken_at = timezone.now()
            
            # Update order status to allow tailor to proceed
            if order.status == 'measuring':
                order.status = 'cutting'  # Tailor can now start cutting
                order.save()
                
                # Create status history
                from apps.orders.models import OrderStatusHistory
                OrderStatusHistory.objects.create(
                    order=order,
                    status=order.status,
                    previous_status=previous_status,
                    changed_by=request.user,
                    notes=f"Measurements taken by rider. {serializer.validated_data.get('notes', '')}"
                )
            
            # Update assignment status
            try:
                assignment = order.rider_assignment
                assignment.status = 'in_progress'
                assignment.started_at = timezone.now()
                if serializer.validated_data.get('notes'):
                    assignment.notes = serializer.validated_data['notes']
                assignment.save()
            except RiderOrderAssignment.DoesNotExist:
                pass
            
            order.save()
            
            response_serializer = RiderOrderDetailSerializer(order)
            return api_response(
                success=True,
                message="Measurements added successfully. Tailor can now proceed with cutting.",
                data=response_serializer.data,
                status_code=status.HTTP_200_OK
            )
        
        return api_response(
            success=False,
            message="Failed to add measurements",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class RiderUpdateOrderStatusView(APIView):
    """Rider updates order status"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        request=RiderUpdateOrderStatusSerializer,
        responses=RiderOrderDetailSerializer,
        summary="Update order status",
        description="Rider updates order status (ready_for_delivery, delivered)",
        tags=["Rider Orders"]
    )
    def patch(self, request, order_id):
        if request.user.role != 'RIDER':
            return api_response(
                success=False,
                message="Only riders can access this endpoint",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        order = get_object_or_404(Order, id=order_id)
        
        # Verify rider has access
        if order.rider != request.user:
            return api_response(
                success=False,
                message="You don't have access to this order",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        serializer = RiderUpdateOrderStatusSerializer(data=request.data)
        if serializer.is_valid():
            # Store previous status before update
            previous_status = order.status
            new_status = serializer.validated_data['status']
            
            # Validate status transitions
            if new_status == 'ready_for_delivery':
                # For fabric_only: after picking from tailor
                if order.order_type == 'fabric_only' and order.status in ['confirmed', 'ready_for_delivery']:
                    order.status = 'ready_for_delivery'
                elif order.order_type == 'fabric_with_stitching':
                    # For fabric_with_stitching: can mark ready after tailor completes
                    if order.status in ['stitching', 'ready_for_delivery']:
                        order.status = 'ready_for_delivery'
                    else:
                        return api_response(
                            success=False,
                            message="Order must be in stitching status before marking as ready for delivery",
                            status_code=status.HTTP_400_BAD_REQUEST
                        )
                else:
                    return api_response(
                        success=False,
                        message="Invalid status transition",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
            
            elif new_status == 'delivered':
                if order.status != 'ready_for_delivery':
                    return api_response(
                        success=False,
                        message="Order must be ready for delivery before marking as delivered",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
                order.status = 'delivered'
                order.actual_delivery_date = timezone.now().date()
                
                # Update assignment
                try:
                    assignment = order.rider_assignment
                    assignment.status = 'completed'
                    assignment.completed_at = timezone.now()
                    if serializer.validated_data.get('notes'):
                        assignment.notes = serializer.validated_data['notes']
                    assignment.save()
                except RiderOrderAssignment.DoesNotExist:
                    pass
                
                # Update rider statistics
                try:
                    rider_profile = request.user.rider_profile
                    rider_profile.total_deliveries += 1
                    rider_profile.save()
                except RiderProfile.DoesNotExist:
                    pass
            
            order.save()
            
            # Create status history
            from apps.orders.models import OrderStatusHistory
            OrderStatusHistory.objects.create(
                order=order,
                status=order.status,
                previous_status=previous_status,
                changed_by=request.user,
                notes=serializer.validated_data.get('notes', '')
            )
            
            response_serializer = RiderOrderDetailSerializer(order)
            return api_response(
                success=True,
                message=f"Order status updated to {order.get_status_display()}",
                data=response_serializer.data,
                status_code=status.HTTP_200_OK
            )
        
        return api_response(
            success=False,
            message="Failed to update order status",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )

