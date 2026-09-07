"""Serializers for owner-app account endpoints."""

from rest_framework import serializers

from apps.accounts.models import CustomUser
from apps.core.phone_utils import display_user_label, format_phone_for_display
from zthob.languages import SUPPORTED_LANGUAGES


class OwnerProfileSerializer(serializers.ModelSerializer):
    """Read-only owner personal profile (not shop profile)."""

    phone = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            'id',
            'phone',
            'first_name',
            'last_name',
            'full_name',
            'language',
            'date_of_birth',
            'role',
            'date_joined',
        ]
        read_only_fields = fields

    def get_phone(self, user):
        return format_phone_for_display(user.phone)

    def get_full_name(self, user):
        return display_user_label(user)


class OwnerProfileUpdateSerializer(serializers.ModelSerializer):
    """Safe partial update for owner personal profile."""

    name = serializers.CharField(
        required=False,
        allow_blank=True,
        write_only=True,
        help_text='Optional single field to set first_name and last_name',
    )

    class Meta:
        model = CustomUser
        fields = [
            'first_name',
            'last_name',
            'name',
            'language',
            'date_of_birth',
        ]
        extra_kwargs = {
            'first_name': {'required': False, 'allow_blank': True},
            'last_name': {'required': False, 'allow_blank': True},
            'language': {'required': False},
            'date_of_birth': {'required': False, 'allow_null': True},
        }

    def validate_language(self, value):
        if value not in SUPPORTED_LANGUAGES:
            raise serializers.ValidationError(
                f'Language must be one of: {", ".join(SUPPORTED_LANGUAGES)}'
            )
        return value

    def validate(self, attrs):
        name = attrs.pop('name', None)
        if name is not None:
            cleaned = name.strip()
            if cleaned:
                parts = cleaned.split(' ', 1)
                attrs['first_name'] = parts[0]
                attrs['last_name'] = parts[1] if len(parts) > 1 else ''
            else:
                attrs['first_name'] = ''
                attrs['last_name'] = ''
        return attrs

    def update(self, instance, validated_data):
        update_fields = []
        for field, value in validated_data.items():
            setattr(instance, field, value)
            update_fields.append(field)
        if update_fields:
            instance.save(update_fields=update_fields)
        return instance
