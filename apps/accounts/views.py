
from rest_framework.views import APIView
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
    )
from rest_framework_simplejwt.tokens import RefreshToken
from zthob.utils import api_response
from drf_spectacular.utils import extend_schema


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