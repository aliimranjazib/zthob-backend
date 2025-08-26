
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny,IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import authenticate
from rest_framework import status
from .serializers import (
    UserRegisterSerializer,
    UserProfileSerializer,
    UserLoginSerializer,
    ChangePasswordSerializer,
    )
from rest_framework_simplejwt.tokens import RefreshToken
from zthob.utils import api_response
from drf_yasg.utils import swagger_auto_schema

class UserRegistrationView(APIView):
    permission_classes=[AllowAny]
    @swagger_auto_schema(
    tags=['Accounts - Authentication'],
    request_body=UserRegisterSerializer,
    responses={201: UserProfileSerializer}
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
    permission_classes=[AllowAny]
    @swagger_auto_schema(
        tags=['Accounts - Authentication'],
        request_body=UserLoginSerializer,
        responses={200:UserProfileSerializer}
    )
    def post(self,request):
        serializer=UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            username=serializer.validated_data['username']
            password=serializer.validated_data['password']
            user=authenticate(username=username,password=password)
            if user:
                refresh=RefreshToken.for_user(user)
                return api_response(success=True,
                                    message="Login successful",
                                    data={'user':UserProfileSerializer(user).data,
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
    permission_classes=[IsAuthenticated]
    @swagger_auto_schema(
        tags=['Accounts - User Profile'],
        response={200:UserProfileSerializer}
    )
    def get(self,request):
        serializer=UserProfileSerializer(request.user)
        return api_response(success=True,
                            message="Profile fetched successfully",
                            data=serializer.data ,
                            status_code=status.HTTP_200_OK
                            )
    @swagger_auto_schema(
       tags=['Accounts - User Profile'],
       request_body=UserProfileSerializer,
       responses={200:UserProfileSerializer} 
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
    permission_classes=[IsAuthenticated]
    @swagger_auto_schema(
        tags=['Accounts - Change Password'],
        request_body=ChangePasswordSerializer,
        responses={200:UserProfileSerializer}
    )
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