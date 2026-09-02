from rest_framework import serializers

from apps.tailors.models import TailorProfile, ServiceArea


class OwnerShopSerializer(serializers.ModelSerializer):
    shop_image_url = serializers.SerializerMethodField()

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


class OwnerShopCreateSerializer(serializers.ModelSerializer):
    service_areas = serializers.IntegerField(
        required=False,
        allow_null=True,
        write_only=True,
        help_text='Optional service area ID for the shop review record',
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

    def validate_service_areas(self, value):
        if value in (None, ''):
            return None
        try:
            ServiceArea.objects.get(id=value, is_active=True)
        except ServiceArea.DoesNotExist as exc:
            raise serializers.ValidationError(
                f'Invalid or inactive service area ID: {value}'
            ) from exc
        return value

    def create(self, validated_data):
        service_areas_id = validated_data.pop('service_areas', None)
        owner = self.context['owner']
        user_link = owner
        from apps.tailors.models import TailorProfile as TailorProfileModel
        if TailorProfileModel.objects.filter(user=owner).exists():
            user_link = None

        shop = TailorProfile.objects.create(
            owner=owner,
            user=user_link,
            **validated_data,
        )

        if service_areas_id is not None:
            from apps.tailors.models import TailorProfileReview
            TailorProfileReview.objects.get_or_create(
                profile=shop,
                defaults={
                    'review_status': 'draft',
                    'service_areas': [service_areas_id],
                },
            )

        return shop


class OwnerShopUpdateSerializer(serializers.ModelSerializer):
    service_areas = serializers.IntegerField(
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

    def validate_service_areas(self, value):
        if value in (None, ''):
            return None
        try:
            ServiceArea.objects.get(id=value, is_active=True)
        except ServiceArea.DoesNotExist as exc:
            raise serializers.ValidationError(
                f'Invalid or inactive service area ID: {value}'
            ) from exc
        return value

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
