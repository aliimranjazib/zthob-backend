from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from .services import PhoneVerificationService
from .serializers import PhoneVerificationSerializer, OTPVerificationSerializer, SystemSettingsSerializer, SliderSerializer
from .models import SystemSettings, Slider
from zthob.utils import api_response
from rest_framework import status

class BasePhoneVerificationView(APIView):
    """Base view for phone verification - can be used by any app"""
    permission_classes = [IsAuthenticated]

class SendOTPView(BasePhoneVerificationView):
    """Send OTP to phone number - works for any user type"""
    
    def post(self, request):
        serializer = PhoneVerificationSerializer(data=request.data)
        if serializer.is_valid():
            phone_number = serializer.validated_data['phone_number']
            verification, otp_code, sms_success, sms_message = PhoneVerificationService.create_verification(
                user=request.user,
                phone_number=phone_number
            )
            
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
        else:
            return api_response(
                success=False,
                message="Invalid phone number",
                errors=serializer.errors
            )

class VerifyOTPView(BasePhoneVerificationView):
    """Verify OTP code - works for any user type"""
    
    def post(self, request):
        serializer = OTPVerificationSerializer(data=request.data)
        if serializer.is_valid():
            otp_code = serializer.validated_data['otp_code']
            
            # Use the service to verify OTP
            is_valid, message = PhoneVerificationService.verify_otp(
                user=request.user,
                otp_code=otp_code
            )
            
            return api_response(
                success=is_valid,
                message=message
            )
        else:
            return api_response(
                success=False,
                message="Invalid OTP format",
                errors=serializer.errors
            )


class SystemSettingsView(APIView):
    """Get system settings (tax rate, delivery fees, etc.)"""
    permission_classes = [AllowAny]  # Public endpoint for frontend calculations
    
    @extend_schema(
        responses={200: SystemSettingsSerializer},
        summary="Get system settings",
        description="Get current system settings including tax rate and delivery fees. Public endpoint for frontend calculations.",
        tags=["System Configuration"]
    )
    def get(self, request):
        """Get active system settings"""
        settings = SystemSettings.get_active_settings()
        serializer = SystemSettingsSerializer(settings)
        
        return api_response(
            success=True,
            message="System settings retrieved successfully",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )


class SliderListView(APIView):
    """Get all active sliders for mobile app"""
    permission_classes = [AllowAny]  # Public endpoint
    
    @extend_schema(
        responses={200: SliderSerializer(many=True)},
        summary="Get active sliders",
        description="Get all active slider/banner images with text and button information for mobile app display.",
        tags=["Sliders"]
    )
    def get(self, request):
        """Get all active sliders ordered by display order"""
        sliders = Slider.objects.filter(is_active=True).order_by('order', '-created_at')
        serializer = SliderSerializer(sliders, many=True, context={'request': request})
        
        return api_response(
            success=True,
            message="Sliders retrieved successfully",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )
