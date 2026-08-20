from rest_framework import serializers

from apps.core.media_utils import build_public_media_url
from apps.orders.customer_fabric import MAX_CUSTOMER_FABRIC_IMAGE_BYTES
from apps.orders.models import CustomerFabricImage


class CustomerFabricUploadSerializer(serializers.ModelSerializer):
    """Upload a single photo of customer-provided fabric."""

    class Meta:
        model = CustomerFabricImage
        fields = ['image']

    def validate_image(self, value):
        if value.size > MAX_CUSTOMER_FABRIC_IMAGE_BYTES:
            raise serializers.ValidationError('Image size exceeds 5MB limit.')
        return value

    def create(self, validated_data):
        validated_data['uploaded_by'] = self.context['request'].user
        return super().create(validated_data)


class CustomerFabricUploadResponseSerializer(serializers.ModelSerializer):
    path = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()

    class Meta:
        model = CustomerFabricImage
        fields = ['id', 'path', 'url']

    def get_path(self, obj):
        return obj.image.name if obj.image else None

    def get_url(self, obj):
        request = self.context.get('request')
        if obj.image:
            return build_public_media_url(request, obj.image.url)
        return None
