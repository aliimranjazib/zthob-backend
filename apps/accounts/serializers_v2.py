from rest_framework import serializers

from apps.core.phone_format import is_valid_saudi_phone
from apps.tailors.models import Business


class V2PhoneVerifySerializer(serializers.Serializer):
    phone = serializers.CharField(required=False, allow_blank=True)
    verification_id = serializers.UUIDField(required=False)
    otp_code = serializers.CharField(required=True)
    name = serializers.CharField(required=False, allow_blank=True, default='')
    role = serializers.ChoiceField(
        choices=['USER', 'TAILOR', 'RIDER', 'ADMIN'],
        required=False,
        default='TAILOR',
    )
    app_entry = serializers.ChoiceField(
        choices=[('owner', 'Owner'), ('staff', 'Staff'), ('tailor', 'Tailor')],
        required=False,
        allow_null=True,
    )


class V2ProfileSerializer(serializers.Serializer):
    full_name = serializers.CharField(required=False, allow_blank=True)
    language = serializers.ChoiceField(
        choices=[('ar', 'Arabic'), ('en', 'English')],
        required=False,
    )


class V2SwitchShopSerializer(serializers.Serializer):
    shop_id = serializers.IntegerField(min_value=1)
    app_entry = serializers.ChoiceField(
        choices=[('owner', 'Owner'), ('staff', 'Staff'), ('tailor', 'Tailor')],
        required=False,
        allow_null=True,
    )


class V2BusinessSerializer(serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = Business
        fields = [
            'id',
            'name',
            'contact_phone',
            'contact_email',
            'city',
            'logo_url',
            'default_language',
            'timezone',
            'currency',
            'status',
            'setup_step',
            'is_setup_complete',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'status',
            'setup_step',
            'is_setup_complete',
            'created_at',
            'updated_at',
        ]

    def get_logo_url(self, obj):
        if not obj.logo:
            return None
        request = self.context.get('request')
        if request is None:
            return obj.logo.url
        return request.build_absolute_uri(obj.logo.url)


class V2BusinessWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Business
        fields = [
            'name',
            'contact_phone',
            'contact_email',
            'city',
            'logo',
            'default_language',
            'timezone',
            'currency',
        ]

    def validate_name(self, value):
        value = (value or '').strip()
        if not value:
            raise serializers.ValidationError('Business name is required.')
        return value

    def validate_contact_phone(self, value):
        if value in (None, ''):
            return value
        phone = value.strip().replace(' ', '').replace('-', '')
        if not is_valid_saudi_phone(phone):
            raise serializers.ValidationError(
                'Phone number must be in Saudi Arabia format (05xxxxxxxx)'
            )
        return phone
