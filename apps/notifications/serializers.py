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
    
    def create(self, validated_data):
        """Create or update FCM token"""
        user = self.context['request'].user
        token = validated_data['token']
        device_id = validated_data.get('device_id')
        
        # Check if token already exists
        existing_token = FCMDeviceToken.objects.filter(token=token).first()
        
        if existing_token:
            # Update existing token
            if existing_token.user != user:
                # Token belongs to different user, update it
                existing_token.user = user
                existing_token.is_active = True
                if device_id:
                    existing_token.device_id = device_id
                existing_token.save()
                return existing_token
            else:
                # Same user, just update last_used_at
                existing_token.is_active = True
                if device_id:
                    existing_token.device_id = device_id
                existing_token.save()
                return existing_token
        
        # Check if user already has a token for this device_id
        if device_id:
            existing_device_token = FCMDeviceToken.objects.filter(
                user=user,
                device_id=device_id
            ).first()
            
            if existing_device_token:
                # Update existing device token
                existing_device_token.token = token
                existing_device_token.is_active = True
                existing_device_token.save()
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
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']

