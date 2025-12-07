
from rest_framework.views import APIView
from rest_framework.decorators import api_view
from rest_framework.permissions import AllowAny,IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import authenticate
from django.db.models import Q
from rest_framework import status

from apps.accounts.models import CustomUser
from .serializers import (
    UserRegisterSerializer,
    UserProfileSerializer,
    UserLoginSerializer,
    ChangePasswordSerializer,
    PhoneLoginSerializer,
    PhoneVerifySerializer,
    )
from apps.core.services import PhoneVerificationService
from apps.core.models import PhoneVerification
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from zthob.utils import api_response
from drf_spectacular.utils import extend_schema

# Test deployment
class UserRegistrationView(APIView):
    serializer_class = UserRegisterSerializer
    permission_classes=[AllowAny]
    @extend_schema(
        responses=UserRegisterSerializer,
        tags=["Profile"],
        summary="Retrieve logged-in user profile"
    )
    def post(self,request):
        serializer=UserRegisterSerializer(data=request.data)
        if serializer.is_valid():
            user=serializer.save()
            refresh=RefreshToken.for_user(user)
            return api_response(success=True,
                                message='Registration successful',
                                data={'user':serializer.data,
                                      'tokens':{
                                          'refresh':str(refresh),
                                          'access_token':str(refresh.access_token)
                                      }
                                      },
                                status_code=status.HTTP_201_CREATED
                                )
        return api_response(success=False,
                            message='Registration Failed',
                            errors=serializer.errors,
                            status_code=status.HTTP_400_BAD_REQUEST,
                            )
        
class UserLoginView(APIView):
    serializer_class = UserLoginSerializer
    permission_classes=[AllowAny]

    def post(self,request):
        serializer=UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            username=serializer.validated_data['username']
            password=serializer.validated_data['password']
            user = CustomUser.objects.filter(Q(username=username)|Q(email=username)|Q(phone=username)).first()
            #user=authenticate(username=username,password=password)
            if user:
                refresh=RefreshToken.for_user(user)
                return api_response(success=True,
                                    message="Login successful",
                                    data={
                                          'tokens':{
                                              'refresh':str(refresh),
                                              'access_token':str(refresh.access_token)
                                          }
                                          
                                          },
                                    status_code=status.HTTP_200_OK,
                                    )
            else:
                return api_response(success=False,
                                    message='Invalid credentials',
                                    errors=serializer.errors,
                                    status_code=status.HTTP_401_UNAUTHORIZED
                                    )
            
        return api_response(success=False,
                            message='Login failed',
                            errors=serializer.errors,
                            status_code=status.HTTP_400_BAD_REQUEST
                            )
        
class UserProfileView(APIView):
    serializer_class = UserProfileSerializer
    permission_classes=[IsAuthenticated]

    def get(self,request):
        serializer=UserProfileSerializer(request.user)
        return api_response(success=True,
                            message="Profile fetched successfully",
                            data=serializer.data ,
                            status_code=status.HTTP_200_OK
                            )

    def put(self,request):
        serializer=UserProfileSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return api_response(success=True,
                                message="Profile updated successfully",
                                data=serializer.data,
                                status_code=status.HTTP_200_OK
                                )
        return api_response(success=False,
                            message='Profile update failed',
                            errors=serializer.errors,
                            status_code=status.HTTP_400_BAD_REQUEST
                            
                            )

class ChangePasswordView(APIView):
    serializer_class = ChangePasswordSerializer
    permission_classes=[IsAuthenticated]
    def post(self,request):
        serializer=ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            user=request.user
            if user.check_password(serializer.validated_data['old_password']):
                user.set_password(serializer.validated_data['new_password'])
                user.save()
                return api_response(
                    success=True,
                    message="Password changed successfully")
            else:
                return api_response(
                    success=False,
                    message="Current password is incorrect",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
        return api_response(
            success=False,
            message="Password change failed",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )

class UserLogoutView(APIView):
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=["Profile"],
        summary="Logout user and invalidate refresh token"
    )
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh_token')
            if not refresh_token:
                return api_response(
                    success=False,
                    message="Refresh token is required",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            token = RefreshToken(refresh_token)
            token.blacklist()
            
            return api_response(
                success=True,
                message="Logout successful",
                status_code=status.HTTP_200_OK
            )
        except TokenError:
            return api_response(
                success=False,
                message="Invalid or expired token",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return api_response(
                success=False,
                message="Logout failed",
                errors=str(e),
                status_code=status.HTTP_400_BAD_REQUEST
            )

@api_view(['GET'])
def test_deployment(request):
    return api_response(success=True, message="Deployment test successful")

class PhoneLoginView(APIView):
    """Send OTP to phone number for login/registration"""
    permission_classes = [AllowAny]
    
    @extend_schema(
        request=PhoneLoginSerializer,
        responses={200: PhoneLoginSerializer},
        tags=["Authentication"],
        summary="Send OTP to phone number",
        description="Send OTP code to phone number for phone-based authentication. Works for both new and existing users."
    )
    def post(self, request):
        serializer = PhoneLoginSerializer(data=request.data)
        if serializer.is_valid():
            phone = serializer.validated_data['phone']
            
            # Create verification and send OTP
            try:
                verification, otp_code, sms_success, sms_message, user = PhoneVerificationService.create_verification_for_phone(
                    phone_number=phone
                )
                
                response_data = {
                    "phone": phone,
                    "sms_sent": sms_success,
                    "expires_in": 300  # 5 minutes
                }
                
                if sms_success:
                    return api_response(
                        success=True,
                        message=f"OTP sent to {phone}",
                        data=response_data,
                        status_code=status.HTTP_200_OK,
                        request=request
                    )
                else:
                    # Still return success but warn about SMS failure
                    # OTP is still generated and can be used for testing
                    return api_response(
                        success=True,
                        message=f"OTP generated for {phone}, but SMS sending failed. Please check server logs.",
                        data=response_data,
                        status_code=status.HTTP_200_OK,
                        request=request
                    )
            except Exception as e:
                return api_response(
                    success=False,
                    message="Failed to send OTP",
                    errors=str(e),
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    request=request
                )
        
        return api_response(
            success=False,
            message="Invalid phone number",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST,
            request=request
        )

class PhoneVerifyView(APIView):
    """Verify OTP and complete login/registration"""
    permission_classes = [AllowAny]
    
    @extend_schema(
        request=PhoneVerifySerializer,
        responses={200: PhoneVerifySerializer},
        tags=["Authentication"],
        summary="Verify OTP and login/register",
        description="Verify OTP code and complete phone-based authentication. Creates new user if doesn't exist."
    )
    def post(self, request):
        serializer = PhoneVerifySerializer(data=request.data)
        if serializer.is_valid():
            phone = serializer.validated_data['phone']
            otp_code = serializer.validated_data['otp_code']
            name = serializer.validated_data.get('name', '')
            role = serializer.validated_data.get('role', 'USER')
            date_of_birth = serializer.validated_data.get('date_of_birth', None)
            
            # Check if user exists and was already verified (before verification)
            # This determines if they're a new or returning user
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            local_phone = PhoneVerificationService.normalize_phone_to_local(phone)
            user_before_verify = User.objects.filter(phone=local_phone).first()
            
            # Check if user was already verified before this verification
            # If phone_verified is True, they've logged in before
            was_already_verified = user_before_verify and user_before_verify.phone_verified
            
            # Also check if there are any previous verified verifications
            has_previous_verification = False
            if user_before_verify:
                has_previous_verification = PhoneVerification.objects.filter(
                    user=user_before_verify,
                    is_verified=True
                ).exclude(otp_code=otp_code).exists()
            
            # User is new if they were never verified before
            is_new_user = not was_already_verified and not has_previous_verification
            
            # Verify OTP
            is_valid, message, user = PhoneVerificationService.verify_otp_for_phone(
                phone_number=phone,
                otp_code=otp_code
            )
            
            if not is_valid or not user:
                return api_response(
                    success=False,
                    message=message or "Invalid or expired OTP",
                    status_code=status.HTTP_400_BAD_REQUEST,
                    request=request
                )
            
            # Update user with provided information if this is a new user
            if is_new_user:
                if name:
                    name_parts = name.strip().split(' ', 1)
                    user.first_name = name_parts[0]
                    user.last_name = name_parts[1] if len(name_parts) > 1 else ''
                if role:
                    user.role = role
                if date_of_birth:
                    user.date_of_birth = date_of_birth
                user.save()
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            # Prepare user data
            user_data = {
                'id': user.id,
                'phone': user.phone,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'role': user.role,
                'phone_verified': user.phone_verified,
                'date_of_birth': user.date_of_birth.isoformat() if user.date_of_birth else None
            }
            
            response_data = {
                'tokens': {
                    'access_token': str(refresh.access_token),
                    'refresh_token': str(refresh)
                },
                'user': user_data,
                'is_new_user': is_new_user
            }
            
            status_code = status.HTTP_201_CREATED if is_new_user else status.HTTP_200_OK
            success_message = "Registration and login successful" if is_new_user else "Login successful"
            
            return api_response(
                success=True,
                message=success_message,
                data=response_data,
                status_code=status_code,
                request=request
            )
        
        return api_response(
            success=False,
            message="OTP verification failed",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST,
            request=request
        )

class PhoneResendOTPView(APIView):
    """Resend OTP to phone number"""
    permission_classes = [AllowAny]
    
    @extend_schema(
        request=PhoneLoginSerializer,
        responses={200: PhoneLoginSerializer},
        tags=["Authentication"],
        summary="Resend OTP to phone number",
        description="Resend OTP code to phone number if user didn't receive it or it expired."
    )
    def post(self, request):
        serializer = PhoneLoginSerializer(data=request.data)
        if serializer.is_valid():
            phone = serializer.validated_data['phone']
            
            # Create verification and send OTP
            try:
                verification, otp_code, sms_success, sms_message, user = PhoneVerificationService.create_verification_for_phone(
                    phone_number=phone
                )
                
                response_data = {
                    "phone": phone,
                    "sms_sent": sms_success,
                    "expires_in": 300  # 5 minutes
                }
                
                if sms_success:
                    return api_response(
                        success=True,
                        message=f"OTP resent to {phone}",
                        data=response_data,
                        status_code=status.HTTP_200_OK,
                        request=request
                    )
                else:
                    return api_response(
                        success=True,
                        message=f"OTP generated for {phone}, but SMS sending failed. Please check server logs.",
                        data=response_data,
                        status_code=status.HTTP_200_OK,
                        request=request
                    )
            except Exception as e:
                return api_response(
                    success=False,
                    message="Failed to resend OTP",
                    errors=str(e),
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    request=request
                )
        
        return api_response(
            success=False,
            message="Invalid phone number",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST,
            request=request
        )