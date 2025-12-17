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
# Import serializers from serializers.py file directly
import importlib.util
import sys
from pathlib import Path

# Load serializers.py as a module with proper package context
_serializers_file = Path(__file__).parent / 'serializers.py'
_spec = importlib.util.spec_from_file_location("riders_serializers_file", _serializers_file)
_serializers_module = importlib.util.module_from_spec(_spec)

# Set up the module's package context for relative imports to work
_serializers_module.__package__ = 'apps.riders'
_serializers_module.__file__ = str(_serializers_file)

# Add apps.riders to sys.modules temporarily if needed
_original_module = sys.modules.get('apps.riders.serializers')
try:
    # Temporarily remove the directory-based module
    if 'apps.riders.serializers' in sys.modules:
        del sys.modules['apps.riders.serializers']
    
    # Execute the module
    _spec.loader.exec_module(_serializers_module)
    
    # Import the classes
    RiderRegisterSerializer = _serializers_module.RiderRegisterSerializer
    RiderProfileSerializer = _serializers_module.RiderProfileSerializer
    RiderProfileUpdateSerializer = _serializers_module.RiderProfileUpdateSerializer
    RiderProfileSubmissionSerializer = _serializers_module.RiderProfileSubmissionSerializer
    RiderProfileStatusSerializer = _serializers_module.RiderProfileStatusSerializer
    RiderDocumentUploadSerializer = _serializers_module.RiderDocumentUploadSerializer
    RiderDocumentSerializer = _serializers_module.RiderDocumentSerializer
    RiderOrderListSerializer = _serializers_module.RiderOrderListSerializer
    RiderOrderDetailSerializer = _serializers_module.RiderOrderDetailSerializer
    RiderAddMeasurementsSerializer = _serializers_module.RiderAddMeasurementsSerializer
    RiderUpdateOrderStatusSerializer = _serializers_module.RiderUpdateOrderStatusSerializer
finally:
    # Restore original module if it existed
    if _original_module:
        sys.modules['apps.riders.serializers'] = _original_module
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
                        'name': user.get_full_name() or user.username,
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
            verification, otp_code, sms_success, sms_message = PhoneVerificationService.create_verification(
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
            
            # Include SMS status in response for debugging
            response_data = {
                "sms_sent": sms_success,
                "sms_message": sms_message if not sms_success else "SMS sent successfully"
            }
            
            if sms_success:
                return api_response(
                    success=True,
                    message=f"OTP sent to {phone_number}",
                    data=response_data
                )
            else:
                # Still return success but warn about SMS failure
                return api_response(
                    success=True,
                    message=f"OTP generated for {phone_number}, but SMS sending failed. Please check server logs.",
                    data=response_data
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
        
        rider_profile, created = RiderProfile.objects.get_or_create(
            user=request.user,
            defaults={
                'is_active': True,
                'is_available': True,
            }
        )
        
        # Create review record if it doesn't exist
        if created:
            RiderProfileReview.objects.get_or_create(
                profile=rider_profile,
                defaults={'review_status': 'draft'}
            )
        
        serializer = RiderProfileSerializer(rider_profile, context={'request': request})
        return api_response(
            success=True,
            message="Profile retrieved successfully",
            data=serializer.data,
            status_code=status.HTTP_200_OK
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
        
        rider_profile, created = RiderProfile.objects.get_or_create(
            user=request.user,
            defaults={
                'is_active': True,
                'is_available': True,
            }
        )
        
        # Create review record if it doesn't exist
        if created:
            RiderProfileReview.objects.get_or_create(
                profile=rider_profile,
                defaults={'review_status': 'draft'}
            )
        
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
        
        # Get orders that are paid, don't have a rider assigned, and tailor has confirmed
        # Riders should only see orders after tailor has accepted them
        # AND rider_status must be 'none' (not yet accepted by any rider)
        orders = Order.objects.filter(
            payment_status='paid',
            rider__isnull=True,
            rider_status='none',  # Only show orders not yet accepted by any rider
        ).filter(
            # Show if main status is confirmed/in_progress OR if tailor has accepted it
            Q(status__in=['confirmed', 'in_progress', 'ready_for_delivery']) | 
            Q(tailor_status__in=['accepted', 'in_progress', 'stitching_started', 'stitched'])
        ).select_related(
            'customer',
            'tailor',
            'delivery_address'
        ).prefetch_related('order_items__fabric').order_by('-created_at')
        
        # Filter by status if provided
        status_filter = request.query_params.get('status')
        if status_filter:
            orders = orders.filter(status=status_filter)
        
        # Filter by order type if provided
        order_type = request.query_params.get('order_type')
        if order_type:
            orders = orders.filter(order_type=order_type)
        
        serializer = RiderOrderListSerializer(orders, many=True, context={'request': request})
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
        description="Get list of orders assigned to the authenticated rider. Includes orders with rider_status='none' (assigned but not yet accepted) so riders can accept manually assigned orders.",
        tags=["Rider Orders"]
    )
    def get(self, request):
        if request.user.role != 'RIDER':
            return api_response(
                success=False,
                message="Only riders can access this endpoint",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        # Show all orders assigned to this rider, including those with rider_status='none' 
        # (which means assigned but not yet accepted - allows rider to accept them)
        # This ensures manually assigned orders are visible even if rider_status wasn't updated
        orders = Order.objects.filter(
            rider=request.user
        ).select_related(
            'customer',
            'tailor',
            'delivery_address'
        ).prefetch_related('order_items__fabric').order_by('-created_at')
        
        # Filter by status if provided
        status_filter = request.query_params.get('status')
        if status_filter:
            orders = orders.filter(status=status_filter)
        
        serializer = RiderOrderListSerializer(orders, many=True, context={'request': request})
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
                'rider',
                'family_member'  # Prefetch family_member for order_recipient
            ).prefetch_related(
                'order_items__fabric',
                'order_items__fabric__gallery',  # Prefetch gallery images for fabric images
                'tailor__addresses'  # Prefetch tailor addresses for structured address
            ),
            id=order_id
        )
        
        # Check if rider has access (either assigned or available)
        if order.rider and order.rider != request.user:
            return api_response(
                success=False,
                message="You don't have access to this order",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        # Riders should not see orders that are still pending (not yet accepted by tailor)
        # Unless the rider is already assigned to it (shouldn't happen normally)
        if order.tailor_status == 'none' and order.rider != request.user:
            return api_response(
                success=False,
                message="Order is still pending tailor confirmation. Please wait for the tailor to accept the order.",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        serializer = RiderOrderDetailSerializer(order, context={'request': request})
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
        request=None,
        responses={200: RiderOrderDetailSerializer},
        summary="Accept order",
        description="Rider accepts an available order for delivery. Rider must be approved. Order ID is provided in the URL path parameter.",
        tags=["Rider Orders"],
        parameters=[
            {
                'name': 'order_id',
                'in': 'path',
                'required': True,
                'description': 'Order ID to accept',
                'schema': {'type': 'integer'}
            }
        ]
    )
    def post(self, request, order_id):
        """Accept order - order_id comes from URL path"""
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
        
        # Get order from URL parameter
        order = get_object_or_404(Order, id=order_id)
        
        # Verify order is available
        if order.payment_status != 'paid':
            return api_response(
                success=False,
                message="Order payment must be paid before rider can accept it",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # Riders should not accept orders that are still pending (not yet accepted by tailor)
        if order.tailor_status == 'none':
            return api_response(
                success=False,
                message="Order is still pending tailor confirmation. Please wait for the tailor to accept the order.",
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
        
        # Use transition service to update rider status to 'accepted'
        from apps.orders.services import OrderStatusTransitionService
        
        success, error_msg, updated_order = OrderStatusTransitionService.transition(
            order=order,
            new_rider_status='accepted',
            user_role='RIDER',
            user=request.user,
            notes='Rider accepted the order'
        )
        
        if not success:
            # If transition fails, still keep the rider assignment but log the error
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to update rider status when accepting order: {error_msg}")
        else:
            order = updated_order
        
        # Send push notification for rider assignment
        try:
            from apps.notifications.services import NotificationService
            NotificationService.send_rider_assignment_notification(
                order=order,
                rider=request.user
            )
        except Exception as e:
            # Log error but don't fail the assignment
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send rider assignment notification: {str(e)}")
        
        # Send push notification for order status change
        try:
            from apps.notifications.services import NotificationService
            NotificationService.send_order_status_notification(
                order=order,
                old_status=order.status,  # History will track the actual change
                new_status=order.status,
                changed_by=request.user
            )
        except Exception as e:
            # Log error but don't fail the assignment
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send order status notification: {str(e)}")
        
        response_serializer = RiderOrderDetailSerializer(order)
        return api_response(
            success=True,
            message="Order accepted successfully",
            data=response_serializer.data,
            status_code=status.HTTP_200_OK
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
        
        order = get_object_or_404(
            Order.objects.select_related('family_member', 'customer'),
            id=order_id
        )
        
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
            measurements_data = serializer.validated_data['measurements']
            
            # Add measurements to order
            order.rider_measurements = measurements_data
            order.measurement_taken_at = timezone.now()
            
            # If order is for a family member, also save measurements to family member profile
            recipient_name = None
            if order.family_member:
                order.family_member.measurements = measurements_data
                order.family_member.save()
                recipient_name = order.family_member.name
            else:
                recipient_name = order.customer.get_full_name() or order.customer.username if order.customer else 'Customer'
            
            # Use transition service to update rider status to 'measurement_taken'
            from apps.orders.services import OrderStatusTransitionService
            
            notes_text = f"Measurements taken by rider for {recipient_name}. {serializer.validated_data.get('notes', '')}"
            
            success, error_msg, updated_order = OrderStatusTransitionService.transition(
                order=order,
                new_rider_status='measurement_taken',
                user_role='RIDER',
                user=request.user,
                notes=notes_text
            )
            
            if not success:
                return api_response(
                    success=False,
                    message=error_msg,
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            order = updated_order
            
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
            
            # Send notification that measurements are taken
            try:
                from apps.notifications.services import NotificationService
                NotificationService.send_measurement_taken_notification(
                    order=order,
                    rider=request.user
                )
            except Exception as e:
                # Log error but don't fail the measurement addition
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to send measurement taken notification: {str(e)}")
            
            response_serializer = RiderOrderDetailSerializer(order, context={'request': request})
            return api_response(
                success=True,
                message=f"Measurements added successfully for {recipient_name}. Tailor can now proceed with cutting.",
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
        
        serializer = RiderUpdateOrderStatusSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(
                success=False,
                message="Failed to update order status",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        new_rider_status = serializer.validated_data['rider_status']
        notes = serializer.validated_data.get('notes', '')
        
        # If unassigned and rider wants to accept, allow assignment here
        if order.rider is None and new_rider_status == 'accepted':
            # Check rider profile approval
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
            
            if order.payment_status != 'paid':
                return api_response(
                    success=False,
                    message="Order payment must be paid before rider can accept it",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Rider can only accept if tailor has already accepted
            if order.tailor_status == 'none':
                return api_response(
                    success=False,
                    message="Order is still pending tailor confirmation. Please wait for the tailor to accept the order.",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Assign rider and create assignment
            order.rider = request.user
            order.save()
            assignment = RiderOrderAssignment.objects.create(
                order=order,
                rider=request.user,
                status='accepted',
                accepted_at=timezone.now(),
                notes=notes
            )
            
            # Use transition service to set rider_status=accepted
            from apps.orders.services import OrderStatusTransitionService
            success, error_msg, updated_order = OrderStatusTransitionService.transition(
                order=order,
                new_rider_status='accepted',
                user_role='RIDER',
                user=request.user,
                notes=notes or 'Rider accepted the order'
            )
            
            if not success:
                return api_response(
                    success=False,
                    message=error_msg,
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            order = updated_order
            
            # Use lightweight response serializer for status updates
            from apps.orders.serializers import OrderStatusUpdateResponseSerializer
            response_serializer = OrderStatusUpdateResponseSerializer(order, context={'request': request})
            return api_response(
                success=True,
                message="Order accepted successfully",
                data=response_serializer.data,
                status_code=status.HTTP_200_OK
            )
        
        # Verify rider has access for subsequent updates
        if order.rider != request.user:
            return api_response(
                success=False,
                message="You don't have access to this order",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        # Security check: For fabric_with_stitching orders, prevent setting measurement_taken
        # without actually adding measurements via the /measurements/ endpoint
        if new_rider_status == 'measurement_taken' and order.order_type == 'fabric_with_stitching':
            if not order.rider_measurements or not order.measurement_taken_at:
                return api_response(
                    success=False,
                    message="Cannot mark measurements as taken without adding measurements",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
        
        # Use transition service
        from apps.orders.services import OrderStatusTransitionService
        
        success, error_msg, updated_order = OrderStatusTransitionService.transition(
            order=order,
            new_rider_status=new_rider_status,
            user_role='RIDER',
            user=request.user,
            notes=notes
        )
        
        if not success:
            return api_response(
                success=False,
                message=error_msg,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        order = updated_order
        
        # If delivered, update assignment and rider stats
        if order.rider_status == 'delivered':
            order.actual_delivery_date = timezone.now().date()
            order.save()
            
            # Update assignment
            try:
                assignment = order.rider_assignment
                assignment.status = 'completed'
                assignment.completed_at = timezone.now()
                if notes:
                    assignment.notes = notes
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
        else:
            # Update assignment for other statuses if it exists
            try:
                assignment = order.rider_assignment
                assignment.status = 'in_progress'
                if new_rider_status == 'accepted':
                    assignment.accepted_at = timezone.now()
                if notes:
                    assignment.notes = notes
                assignment.save()
            except RiderOrderAssignment.DoesNotExist:
                pass
        
        # Send push notification for order status change
        try:
            from apps.notifications.services import NotificationService
            NotificationService.send_order_status_notification(
                order=order,
                old_status=order.status,  # History will have the old status
                new_status=order.status,
                changed_by=request.user
            )
        except Exception as e:
            # Log error but don't fail the update
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send order status notification: {str(e)}")
        
        # Use lightweight response serializer for status updates
        from apps.orders.serializers import OrderStatusUpdateResponseSerializer
        response_serializer = OrderStatusUpdateResponseSerializer(order, context={'request': request})
        return api_response(
            success=True,
            message=f"Order rider status updated to {order.get_rider_status_display()}",
            data=response_serializer.data,
            status_code=status.HTTP_200_OK
        )


# ============================================================================
# ANALYTICS VIEWS
# ============================================================================

@extend_schema(
    tags=["Rider Analytics"],
    description="Get comprehensive analytics for the authenticated rider including deliveries, completion rates, and trends"
)
class RiderAnalyticsView(APIView):
    """
    API endpoint for rider analytics dashboard.
    
    Provides:
    - Total delivery fees from completed deliveries
    - Daily deliveries breakdown
    - Total completed deliveries count
    - Completion percentage
    - Weekly delivery trends
    
    Query Parameters:
    - days: Number of days for daily deliveries (default: 30, max: 365)
    - weeks: Number of weeks for trends (default: 12, max: 52)
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        description="Get comprehensive rider analytics",
        parameters=[
            {
                'name': 'days',
                'in': 'query',
                'description': 'Number of days for daily deliveries breakdown (default: 30, max: 365)',
                'required': False,
                'schema': {'type': 'integer', 'minimum': 1, 'maximum': 365, 'default': 30}
            },
            {
                'name': 'weeks',
                'in': 'query',
                'description': 'Number of weeks for weekly trends (default: 12, max: 52)',
                'required': False,
                'schema': {'type': 'integer', 'minimum': 1, 'maximum': 52, 'default': 12}
            }
        ],
        responses={
            200: 'apps.riders.serializers.analytics.RiderAnalyticsSerializer',
            400: {"description": "Invalid query parameters"},
            403: {"description": "User is not a rider"}
        }
    )
    def get(self, request):
        """
        Get comprehensive analytics for the authenticated rider.
        """
        from apps.riders.services import RiderAnalyticsService
        from apps.riders.serializers.analytics import RiderAnalyticsSerializer
        
        # Check if user is a rider
        if request.user.role != 'RIDER':
            return api_response(
                success=False,
                message="Only riders can access this endpoint",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        # Get query parameters with defaults and validation
        try:
            days = int(request.query_params.get('days', 30))
            weeks = int(request.query_params.get('weeks', 12))
            
            # Validate ranges
            if days < 1 or days > 365:
                return api_response(
                    success=False,
                    message="Days parameter must be between 1 and 365",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            if weeks < 1 or weeks > 52:
                return api_response(
                    success=False,
                    message="Weeks parameter must be between 1 and 52",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
        except ValueError:
            return api_response(
                success=False,
                message="Invalid query parameters. Days and weeks must be integers.",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # Get analytics data
        try:
            analytics_data = RiderAnalyticsService.get_comprehensive_analytics(
                rider_user=request.user,
                days=days,
                weeks=weeks
            )
            
            # Serialize the data
            serializer = RiderAnalyticsSerializer(analytics_data)
            
            return api_response(
                success=True,
                message="Analytics data retrieved successfully",
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )
        except Exception as e:
            return api_response(
                success=False,
                message=f"Error retrieving analytics: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

