from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .services import PhoneVerificationService
from .serializers import PhoneVerificationSerializer, OTPVerificationSerializer
from zthob.utils import api_response

class BasePhoneVerificationView(APIView):
    """Base view for phone verification - can be used by any app"""
    permission_classes = [IsAuthenticated]

class SendOTPView(BasePhoneVerificationView):
    """Send OTP to phone number - works for any user type"""
    
    def post(self, request):
        serializer = PhoneVerificationSerializer(data=request.data)
        if serializer.is_valid():
            phone_number = serializer.validated_data['phone_number']
            verification, otp_code = PhoneVerificationService.create_verification(
                user=request.user,
                phone_number=phone_number
            )
            return api_response(
                success=True,
                message=f"OTP sent to {phone_number}",
                data={"otp": otp_code}  # Remove this in production!
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
