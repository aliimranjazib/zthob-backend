from rest_framework import serializers
from .models import PhoneVerification

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



