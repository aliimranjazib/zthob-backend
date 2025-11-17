from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from django.shortcuts import get_object_or_404

from zthob.utils import api_response
from .models import FCMDeviceToken, NotificationLog
from .serializers import FCMDeviceTokenSerializer, NotificationLogSerializer


class RegisterFCMTokenView(APIView):
    """Register or update FCM device token"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        request=FCMDeviceTokenSerializer,
        responses=FCMDeviceTokenSerializer,
        summary="Register FCM Token",
        description="Register or update Firebase Cloud Messaging device token for push notifications",
        tags=["Notifications"]
    )
    def post(self, request):
        serializer = FCMDeviceTokenSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            fcm_token = serializer.save()
            return api_response(
                success=True,
                message="FCM token registered successfully",
                data=serializer.data,
                status_code=status.HTTP_201_CREATED
            )
        
        return api_response(
            success=False,
            message="Failed to register FCM token",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    @extend_schema(
        request=FCMDeviceTokenSerializer,
        responses=FCMDeviceTokenSerializer,
        summary="Update FCM Token",
        description="Update existing FCM device token",
        tags=["Notifications"]
    )
    def put(self, request, token_id=None):
        # If token_id is provided, update specific token
        if token_id:
            fcm_token = get_object_or_404(
                FCMDeviceToken,
                id=token_id,
                user=request.user
            )
            serializer = FCMDeviceTokenSerializer(
                fcm_token,
                data=request.data,
                partial=True,
                context={'request': request}
            )
        else:
            # Update based on token value
            token = request.data.get('token')
            if not token:
                return api_response(
                    success=False,
                    message="Token is required",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            fcm_token = FCMDeviceToken.objects.filter(
                token=token,
                user=request.user
            ).first()
            
            if not fcm_token:
                return api_response(
                    success=False,
                    message="FCM token not found",
                    status_code=status.HTTP_404_NOT_FOUND
                )
            
            serializer = FCMDeviceTokenSerializer(
                fcm_token,
                data=request.data,
                partial=True,
                context={'request': request}
            )
        
        if serializer.is_valid():
            serializer.save()
            return api_response(
                success=True,
                message="FCM token updated successfully",
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )
        
        return api_response(
            success=False,
            message="Failed to update FCM token",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class UnregisterFCMTokenView(APIView):
    """Unregister (deactivate) FCM device token"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Unregister FCM Token",
        description="Deactivate FCM device token",
        tags=["Notifications"]
    )
    def post(self, request):
        token = request.data.get('token')
        device_id = request.data.get('device_id')
        
        if not token and not device_id:
            return api_response(
                success=False,
                message="Either token or device_id is required",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        if token:
            fcm_tokens = FCMDeviceToken.objects.filter(
                token=token,
                user=request.user
            )
        else:
            fcm_tokens = FCMDeviceToken.objects.filter(
                device_id=device_id,
                user=request.user
            )
        
        if not fcm_tokens.exists():
            return api_response(
                success=False,
                message="FCM token not found",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # Deactivate tokens
        count = fcm_tokens.update(is_active=False)
        
        return api_response(
            success=True,
            message=f"Successfully unregistered {count} FCM token(s)",
            status_code=status.HTTP_200_OK
        )


class NotificationLogListView(APIView):
    """Get notification logs for authenticated user"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        responses=NotificationLogSerializer(many=True),
        summary="Get Notification Logs",
        description="Retrieve notification history for the authenticated user",
        tags=["Notifications"]
    )
    def get(self, request):
        notification_logs = NotificationLog.objects.filter(
            user=request.user
        ).order_by('-created_at')[:50]  # Limit to last 50
        
        serializer = NotificationLogSerializer(notification_logs, many=True)
        
        return api_response(
            success=True,
            message="Notification logs retrieved successfully",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )

