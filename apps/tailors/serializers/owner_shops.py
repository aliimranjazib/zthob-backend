import json

from django.db.models import Q
from rest_framework import serializers

from apps.tailors.models import TailorProfile, ServiceArea


class FlexibleJSONField(serializers.JSONField):
    """Accept JSON objects or JSON strings (common with multipart/form-data)."""

    def to_internal_value(self, data):
        if isinstance(data, str):
            stripped = data.strip()
            if not stripped:
                return {}
            try:
                data = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise serializers.ValidationError('Must be valid JSON.') from exc
        return super().to_internal_value(data)


class ServiceAreaIdField(serializers.Field):
    """Accept service area as int, numeric string, or single-item list."""

    def to_internal_value(self, data):
        if data in (None, ''):
            return None
        if isinstance(data, (list, tuple)):
            if not data:
                return None
            data = data[0]
        if isinstance(data, str):
            stripped = data.strip()
            if not stripped:
                return None
            try:
                data = int(stripped)
            except ValueError as exc:
                raise serializers.ValidationError(
                    'Must be a valid service area ID.'
                ) from exc
        if not isinstance(data, int):
            raise serializers.ValidationError('Must be a valid service area ID.')
        try:
            ServiceArea.objects.get(id=data, is_active=True)
        except ServiceArea.DoesNotExist as exc:
            raise serializers.ValidationError(
                f'Invalid or inactive service area ID: {data}'
            ) from exc
        return data


def _find_empty_owner_stub(owner):
    return (
        TailorProfile.objects.filter(owner=owner, user=owner)
        .filter(Q(shop_name__isnull=True) | Q(shop_name=''))
        .first()
    )


class OwnerShopSerializer(serializers.ModelSerializer):
    shop_image_url = serializers.SerializerMethodField()
    service_area = serializers.SerializerMethodField()

    class Meta:
        model = TailorProfile
        fields = [
            'id',
            'shop_name',
            'contact_number',
            'address',
            'shop_status',
            'is_pinned',
            'is_verified',
            'shop_image',
            'shop_image_url',
            'working_hours',
            'establishment_year',
            'tailor_experience',
            'service_area',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'is_verified',
            'created_at',
            'updated_at',
        ]

    def get_shop_image_url(self, obj):
        if not obj.shop_image:
            return None
        request = self.context.get('request')
        from apps.core.media_utils import build_public_media_url
        return build_public_media_url(request, obj.shop_image.url)

    def get_service_area(self, obj):
        review = getattr(obj, 'review', None)
        if review is None:
            return None
        area_ids = review.service_areas or []
        if not area_ids:
            return None
        area_id = area_ids[0]
        names = self.context.get('service_area_by_id') or {}
        area = names.get(area_id)
        if area is None:
            return {'id': area_id, 'name': None, 'city': None}
        return {
            'id': area.id,
            'name': area.name,
            'city': area.city,
        }


class OwnerShopCreateSerializer(serializers.ModelSerializer):
    working_hours = FlexibleJSONField(required=False, allow_null=True)
    service_areas = ServiceAreaIdField(
        required=False,
        allow_null=True,
        write_only=True,
        help_text='Service area ID for the shop review record',
    )

    class Meta:
        model = TailorProfile
        fields = [
            'shop_name',
            'contact_number',
            'address',
            'working_hours',
            'establishment_year',
            'tailor_experience',
            'shop_image',
            'shop_status',
            'is_pinned',
            'service_areas',
        ]

    def validate_shop_name(self, value):
        value = (value or '').strip()
        if not value:
            raise serializers.ValidationError('Shop name is required.')
        return value

    def validate_contact_number(self, value):
        if value in (None, ''):
            return value
        from apps.core.phone_format import is_valid_saudi_phone

        phone = value.strip().replace(' ', '').replace('-', '')
        if not is_valid_saudi_phone(phone):
            raise serializers.ValidationError(
                'Phone number must be in Saudi Arabia format (05xxxxxxxx)'
            )
        return phone

    def create(self, validated_data):
        service_areas_id = validated_data.pop('service_areas', None)
        owner = self.context['owner']
        stub = _find_empty_owner_stub(owner)
        if stub is not None:
            for field, value in validated_data.items():
                setattr(stub, field, value)
            stub.save()
            shop = stub
        else:
            user_link = owner
            if TailorProfile.objects.filter(user=owner).exists():
                user_link = None
            shop = TailorProfile.objects.create(
                owner=owner,
                user=user_link,
                **validated_data,
            )

        if service_areas_id is not None:
            from apps.tailors.models import TailorProfileReview
            review, _created = TailorProfileReview.objects.get_or_create(
                profile=shop,
                defaults={'review_status': 'draft'},
            )
            review.service_areas = [service_areas_id]
            review.save(update_fields=['service_areas'])

        return shop


class OwnerShopUpdateSerializer(serializers.ModelSerializer):
    working_hours = FlexibleJSONField(required=False, allow_null=True)
    service_areas = ServiceAreaIdField(
        required=False,
        allow_null=True,
        write_only=True,
    )

    class Meta:
        model = TailorProfile
        fields = [
            'shop_name',
            'contact_number',
            'address',
            'working_hours',
            'establishment_year',
            'tailor_experience',
            'shop_image',
            'shop_status',
            'is_pinned',
            'service_areas',
        ]

    def validate_contact_number(self, value):
        if value in (None, ''):
            return value
        from apps.core.phone_format import is_valid_saudi_phone

        phone = value.strip().replace(' ', '').replace('-', '')
        if not is_valid_saudi_phone(phone):
            raise serializers.ValidationError(
                'Phone number must be in Saudi Arabia format (05xxxxxxxx)'
            )
        return phone

    def update(self, instance, validated_data):
        service_areas_id = validated_data.pop('service_areas', serializers.empty)
        shop = super().update(instance, validated_data)

        if service_areas_id is not serializers.empty and service_areas_id is not None:
            from apps.tailors.models import TailorProfileReview
            review, _created = TailorProfileReview.objects.get_or_create(
                profile=shop,
                defaults={'review_status': 'draft'},
            )
            review.service_areas = [service_areas_id]
            review.save(update_fields=['service_areas'])

        return shop


class OwnerShopPinSerializer(serializers.ModelSerializer):
    class Meta:
        model = TailorProfile
        fields = ['is_pinned']
