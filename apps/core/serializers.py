from rest_framework import serializers
from .models import SystemSettings, PhoneVerification

class PhoneVerificationSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20, required=True)
    
    def validate_phone_number(self, value):
        if not value.startswith('+'):
            raise serializers.ValidationError('Phone number must start with +')
        if len(value) < 10:
            raise serializers.ValidationError('Phone number too short')
        return value

class OTPVerificationSerializer(serializers.Serializer):
    otp_code = serializers.CharField(max_length=6, required=True)
    
    def validate_otp_code(self, value):
        if not value.isdigit() or len(value) != 6:
            raise serializers.ValidationError('OTP must be 6 digits')
        return value


class SystemSettingsSerializer(serializers.ModelSerializer):
    """Serializer for SystemSettings - read-only public API"""
    tax_rate_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = SystemSettings
        fields = [
            'tax_rate',
            'tax_rate_percentage',
            'delivery_fee_under_10km',
            'delivery_fee_10km_and_above',
            'distance_threshold_km',
            'free_delivery_threshold',
        ]
        read_only_fields = [
            'tax_rate',
            'tax_rate_percentage',
            'delivery_fee_under_10km',
            'delivery_fee_10km_and_above',
            'distance_threshold_km',
            'free_delivery_threshold',
        ]
    
    def get_tax_rate_percentage(self, obj):
        """Return tax rate as percentage"""
        return f"{obj.tax_rate * 100:.2f}%"
