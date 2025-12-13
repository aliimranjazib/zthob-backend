from rest_framework import serializers
from .models import FCMDeviceToken, NotificationLog


class FCMDeviceTokenSerializer(serializers.ModelSerializer):
    """Serializer for FCM device token registration"""
    
    class Meta:
        model = FCMDeviceToken
        fields = [
            'id',
            'token',
            'device_type',
            'device_id',
            'is_active',
            'last_used_at',
            'created_at',
        ]
        read_only_fields = ['id', 'last_used_at', 'created_at']
        extra_kwargs = {
            'token': {'validators': []}  # Disable default unique validator, we handle it in create()
        }
    
    def validate_token(self, value):
        """Validate token - allow reassignment to different users"""
        # We allow tokens that exist for other users since we'll reassign them in create()
        # The actual uniqueness check and reassignment logic is in create()
        return value
    
    def create(self, validated_data):
        """Create or update FCM token - handles token reassignment between users"""
        user = self.context['request'].user
        token = validated_data['token']
        device_id = validated_data.get('device_id')
        device_type = validated_data.get('device_type', 'android')
        
        # Check if token already exists
        existing_token = FCMDeviceToken.objects.filter(token=token).first()
        
        if existing_token:
            # Token exists - handle reassignment or update
            if existing_token.user != user:
                # Token belongs to different user - REASSIGN IT
                # This handles the case: User A logs out, User B logs in on same device
                existing_token.user = user
                existing_token.is_active = True
                existing_token.device_type = device_type
                if device_id:
                    existing_token.device_id = device_id
                existing_token.save(update_fields=['user', 'is_active', 'device_type', 'device_id', 'last_used_at'])
                return existing_token
            else:
                # Same user, just reactivate and update
                existing_token.is_active = True
                existing_token.device_type = device_type
                if device_id:
                    existing_token.device_id = device_id
                existing_token.save(update_fields=['is_active', 'device_type', 'device_id', 'last_used_at'])
                return existing_token
        
        # Check if user already has a token for this device_id (different token for same device)
        if device_id:
            existing_device_token = FCMDeviceToken.objects.filter(
                user=user,
                device_id=device_id
            ).first()
            
            if existing_device_token:
                # User has different token for this device - update to new token
                # Deactivate old token if it's different
                if existing_device_token.token != token:
                    existing_device_token.token = token
                    existing_device_token.is_active = True
                    existing_device_token.device_type = device_type
                    existing_device_token.save(update_fields=['token', 'is_active', 'device_type', 'last_used_at'])
                    return existing_device_token
                else:
                    # Same token, just reactivate
                    existing_device_token.is_active = True
                    existing_device_token.device_type = device_type
                    existing_device_token.save(update_fields=['is_active', 'device_type', 'last_used_at'])
                    return existing_device_token
        
        # Create new token
        validated_data['user'] = user
        return super().create(validated_data)


class NotificationLogSerializer(serializers.ModelSerializer):
    """Serializer for notification logs"""
    
    class Meta:
        model = NotificationLog
        fields = [
            'id',
            'notification_type',
            'category',
            'title',
            'body',
            'data',
            'status',
            'error_message',
            'sent_at',
            'is_read',
            'read_at',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'read_at']

