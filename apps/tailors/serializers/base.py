# apps/tailors/serializers/base.py
from rest_framework import serializers
from django.core.validators import FileExtensionValidator

# Shared validators
IMAGE_VALIDATOR = [FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png"])]

# Shared serializers
class ImageWithMetadataSerializer(serializers.Serializer):
    """Serializer for image upload with metadata."""
    image = serializers.ImageField(
        validators=IMAGE_VALIDATOR
    )
    is_primary = serializers.BooleanField(default=False)
    order = serializers.IntegerField(default=0)
