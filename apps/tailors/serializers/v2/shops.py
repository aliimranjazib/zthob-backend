from rest_framework import serializers

from apps.accounts.services.v2_auth import APP_ENTRY_OWNER
from apps.tailors.models import TailorProfile
from apps.tailors.serializers.owner_shops import (
    FlexibleJSONField,
    ServiceAreaIdField,
)


class V2ShopSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='shop_name')
    service_area = serializers.SerializerMethodField()
    shop_image_url = serializers.SerializerMethodField()
    experience_years = serializers.IntegerField(source='tailor_experience', allow_null=True)
    review_status = serializers.SerializerMethodField()
    submitted_at = serializers.SerializerMethodField()
    tailor_plus = serializers.SerializerMethodField()

    class Meta:
        model = TailorProfile
        fields = [
            'id',
            'business_id',
            'name',
            'contact_number',
            'address',
            'working_hours',
            'service_area',
            'shop_status',
            'is_verified',
            'is_pinned',
            'shop_image_url',
            'establishment_year',
            'experience_years',
            'review_status',
            'submitted_at',
            'created_at',
            'updated_at',
            'tailor_plus',
        ]

    def get_tailor_plus(self, obj):
        from apps.tailors.services.shop_plus import serialize_shop_tailor_plus
        return serialize_shop_tailor_plus(obj)

    def get_review_status(self, obj):
        review = getattr(obj, 'review', None)
        if review is None:
            return 'draft'
        return review.review_status

    def get_submitted_at(self, obj):
        review = getattr(obj, 'review', None)
        if review is None or review.submitted_at is None:
            return None
        return review.submitted_at.isoformat()

    def get_service_area(self, obj):
        review = getattr(obj, 'review', None)
        if review is None or not review.service_areas:
            return None
        area_id = review.service_areas[0]
        names = self.context.get('service_area_by_id') or {}
        area = names.get(area_id)
        if area is None:
            return {'id': area_id, 'name': None, 'city': None}
        return {'id': area.id, 'name': area.name, 'city': area.city}

    def get_shop_image_url(self, obj):
        if not obj.shop_image:
            return None
        request = self.context.get('request')
        from apps.core.media_utils import build_public_media_url
        return build_public_media_url(request, obj.shop_image.url)


class V2ShopCreateSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='shop_name')
    working_hours = FlexibleJSONField(required=False, allow_null=True)
    service_area_id = ServiceAreaIdField(
        required=False,
        allow_null=True,
        write_only=True,
        source='service_areas',
    )
    experience_years = serializers.IntegerField(
        source='tailor_experience',
        required=False,
        allow_null=True,
    )

    class Meta:
        model = TailorProfile
        fields = [
            'name',
            'contact_number',
            'address',
            'working_hours',
            'establishment_year',
            'experience_years',
            'shop_image',
            'shop_status',
            'is_pinned',
            'service_area_id',
        ]

    def validate_name(self, value):
        value = (value or '').strip()
        if not value:
            raise serializers.ValidationError('Shop name is required.')
        return value

    def create(self, validated_data):
        from apps.tailors.models import TailorProfileReview
        from apps.tailors.serializers.owner_shops import _find_empty_owner_stub
        from apps.tailors.services.v2.business import mark_business_shop_progress

        service_areas_id = validated_data.pop('service_areas', None)
        owner = self.context['owner']
        app_entry = self.context.get('app_entry')

        if app_entry == APP_ENTRY_OWNER:
            business = self.context.get('business')
            if business is None:
                raise serializers.ValidationError(
                    {'business': 'Create your business profile before adding shops.'}
                )
        else:
            business = None

        stub = _find_empty_owner_stub(owner)
        if stub is not None:
            for field, value in validated_data.items():
                setattr(stub, field, value)
            stub.business = business
            stub.save()
            shop = stub
        else:
            user_link = owner
            if TailorProfile.objects.filter(user=owner).exists():
                user_link = None
            shop = TailorProfile.objects.create(
                owner=owner,
                business=business,
                user=user_link,
                **validated_data,
            )

        if service_areas_id is not None:
            review, _created = TailorProfileReview.objects.get_or_create(
                profile=shop,
                defaults={'review_status': 'draft'},
            )
            review.service_areas = [service_areas_id]
            review.save(update_fields=['service_areas'])

        if business is not None:
            mark_business_shop_progress(business)
        return shop


class V2ShopUpdateSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='shop_name', required=False)
    working_hours = FlexibleJSONField(required=False, allow_null=True)
    service_area_id = ServiceAreaIdField(
        required=False,
        allow_null=True,
        write_only=True,
        source='service_areas',
    )
    experience_years = serializers.IntegerField(
        source='tailor_experience',
        required=False,
        allow_null=True,
    )

    class Meta:
        model = TailorProfile
        fields = [
            'name',
            'contact_number',
            'address',
            'working_hours',
            'establishment_year',
            'experience_years',
            'shop_image',
            'shop_status',
            'is_pinned',
            'service_area_id',
        ]

    def update(self, instance, validated_data):
        from apps.tailors.models import TailorProfileReview

        service_areas_id = validated_data.pop('service_areas', serializers.empty)
        shop = super().update(instance, validated_data)

        if service_areas_id is not serializers.empty and service_areas_id is not None:
            review, _created = TailorProfileReview.objects.get_or_create(
                profile=shop,
                defaults={'review_status': 'draft'},
            )
            review.service_areas = [service_areas_id]
            review.save(update_fields=['service_areas'])
        return shop


class V2ShopPinSerializer(serializers.ModelSerializer):
    class Meta:
        model = TailorProfile
        fields = ['is_pinned']
