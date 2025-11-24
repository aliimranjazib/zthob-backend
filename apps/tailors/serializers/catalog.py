# apps/tailors/serializers/catalog.py
from rest_framework import serializers
from ..models import (
    Fabric, FabricImage, FabricType, 
    FabricCategory, FabricTag
)
from ..models.base import SEASON_CHOICES
from .base import ImageWithMetadataSerializer

# Fabric Type Serializers
class FabricTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = FabricType
        fields = ['id', 'name', 'created_at', 'updated_at']

class FabricTypeBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = FabricType
        fields = ['id', 'name']

# Fabric Category Serializers
class FabricCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = FabricCategory
        fields = ["id", "name", "slug", "is_active", "created_at", "updated_at"]

class FabricCategoryBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = FabricCategory
        fields = ['id', 'name', 'is_active']

# Fabric Tag Serializers
class FabricTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = FabricTag
        fields = ['id', 'name', 'slug', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at']

class FabricTagBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = FabricTag
        fields = ['id', 'name']
        read_only_fields = ['id']

# Fabric Image Serializers
class FabricImageSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = FabricImage
        fields = ["id", "image", "order", "is_primary"]

    def get_image(self, obj) -> str | None:
        request = self.context.get("request", None)
        if request:
            return request.build_absolute_uri(obj.image.url) if obj.image else None
        return obj.image.url if obj.image else None

# Fabric Serializers
class FabricSerializer(serializers.ModelSerializer):
    gallery = FabricImageSerializer(many=True, read_only=True)
    category = FabricCategoryBasicSerializer(read_only=True)
    fabric_type = FabricTypeBasicSerializer(read_only=True)
    fabric_tag = FabricTagBasicSerializer(read_only=True)
    is_low_stock = serializers.ReadOnlyField()
    is_out_of_stock = serializers.ReadOnlyField()
    
    class Meta:
        model = Fabric
        fields = [
            "id", "category", "name", "description", "seasons",
            "fabric_type", "fabric_tag", "sku", "price", "stitching_price", "stock",
            "is_low_stock", "is_out_of_stock", "is_active", 
            "created_at", "updated_at", "gallery",
        ]
        read_only_fields = ["id", "sku", "created_at", "updated_at"]

class FabricCreateSerializer(serializers.ModelSerializer):
    images = serializers.ListField(
        child=ImageWithMetadataSerializer(),
        required=True,
        write_only=True,
        help_text="List of images with metadata (is_primary, order)"
    )
    tags = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
        write_only=True,
        help_text="List of fabric tag IDs"
    )

    class Meta:
        model = Fabric
        fields = [
            "category", "name", "seasons", "fabric_type",
            "description", "price", "stitching_price", "stock", "is_active", "images", "tags",
        ]

    def validate_images(self, images):
        # Check that we have at least one image
        if not images:
            raise serializers.ValidationError("At least one image must be provided")
        
        # Check maximum 4 images limit
        if len(images) > 4:
            raise serializers.ValidationError("Maximum 4 images are allowed per fabric")
        
        # Check for file size limits and format validation
        for i, img_data in enumerate(images):
            if 'image' not in img_data:
                raise serializers.ValidationError(f"No image provided for image {i}")
            
            image = img_data['image']
            
            # Check file size (5MB limit)
            if image.size > 5 * 1024 * 1024:
                raise serializers.ValidationError(f"Image size exceeds 5MB limit: {image.name}")
            
            # Check file format (jpg, jpeg, png)
            allowed_extensions = ['jpg', 'jpeg', 'png']
            file_extension = image.name.split('.')[-1].lower()
            if file_extension not in allowed_extensions:
                raise serializers.ValidationError(f"Invalid file format for {image.name}. Only JPG, JPEG, and PNG files are allowed.")
        
        # Ensure only one primary image
        primary_images = [img for img in images if img.get('is_primary', False)]
        if len(primary_images) > 1:
            raise serializers.ValidationError("Only one image can be marked as primary")
        elif not primary_images:
            # If no primary image is marked, set the first one as primary
            images[0]['is_primary'] = True
        
        # Validate order values
        orders = [img.get('order', 0) for img in images]
        if len(set(orders)) != len(orders):
            # If duplicate orders exist, reassign them sequentially
            for i, img in enumerate(images):
                img['order'] = i
        
        return images

    def validate_tags(self, tags):
        """Validate that all provided tag IDs exist and are active."""
        if not tags:
            return tags
        
        from ..models import FabricTag
        
        # Get all active tag IDs
        active_tag_ids = set(FabricTag.objects.filter(is_active=True).values_list('id', flat=True))
        provided_tag_ids = set(tags)
        
        # Check if all provided tags exist and are active
        invalid_tags = provided_tag_ids - active_tag_ids
        if invalid_tags:
            raise serializers.ValidationError(f"Invalid or inactive tag IDs: {list(invalid_tags)}")
        
        return tags

    def create(self, validated_data):
        request = self.context.get("request")
        tailor_profile = getattr(request.user, "tailor_profile", None)
        
        # Extract images and tags data
        images_data = validated_data.pop('images', [])
        tags_data = validated_data.pop('tags', [])
        
        # Create the fabric without the legacy fabric_image field
        fabric = Fabric.objects.create(
            tailor=tailor_profile,
            created_by=request.user,
            **validated_data,
        )
        
        # Add tags to the fabric
        if tags_data:
            from ..models import FabricTag
            tags = FabricTag.objects.filter(id__in=tags_data, is_active=True)
            fabric.tags.set(tags)
        
        # Create gallery images from all images
        for img_data in sorted(images_data, key=lambda x: x.get('order', 0)):
            FabricImage.objects.create(
                fabric=fabric,
                image=img_data['image'],
                is_primary=img_data.get('is_primary', False),
                order=img_data.get('order', 0),
            )

        return fabric

class FabricUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating existing fabrics."""
    
    fabric_type = serializers.PrimaryKeyRelatedField(
        queryset=FabricType.objects.all(),
        required=False,
        help_text="Fabric type ID"
    )
    seasons = serializers.ChoiceField(
        choices=SEASON_CHOICES,
        required=False,
        help_text="Best suited season for this fabric"
    )
    tags = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
        write_only=True,
        help_text="List of fabric tag IDs"
    )
    
    class Meta:
        model = Fabric
        fields = [
            "category", "fabric_type", "seasons", "name",
            "description", "price", "stitching_price", "stock", "is_active", "tags",
        ]
    
    def validate_tags(self, tags):
        """Validate that all provided tag IDs exist and are active."""
        if not tags:
            return tags
        
        from ..models import FabricTag
        
        # Get all active tag IDs
        active_tag_ids = set(FabricTag.objects.filter(is_active=True).values_list('id', flat=True))
        provided_tag_ids = set(tags)
        
        # Check if all provided tags exist and are active
        invalid_tags = provided_tag_ids - active_tag_ids
        if invalid_tags:
            raise serializers.ValidationError(f"Invalid or inactive tag IDs: {list(invalid_tags)}")
        
        return tags
    
    def update(self, instance, validated_data):
        """Update fabric instance with validated data."""
        # Extract tags data
        tags_data = validated_data.pop('tags', None)
        
        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update tags if provided
        if tags_data is not None:
            from ..models import FabricTag
            tags = FabricTag.objects.filter(id__in=tags_data, is_active=True)
            instance.tags.set(tags)
        
        return instance
