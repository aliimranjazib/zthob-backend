from rest_framework import serializers
from .models import CustomStyleCategory, CustomStyle


class CustomStyleSerializer(serializers.ModelSerializer):
    """
    Serializer for individual custom styles.
    Converts image path to full URL for API responses.
    """
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomStyle
        fields = [
            'id',
            'name',
            'code',
            'image_url',
            'description',
            'display_order',
            'extra_price',
        ]
    
    def get_image_url(self, obj):
        """
        Convert image path to full URL.
        Returns: Full URL like 'https://yourbackend.com/media/custom_styles/collar_1.png'
        """
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class CustomStyleCategorySerializer(serializers.ModelSerializer):
    """
    Serializer for style categories with nested styles.
    Used for GET /api/customization/categories/ endpoint.
    """
    styles = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomStyleCategory
        fields = [
            'id',
            'name',
            'display_name',
            'display_order',
            'styles',
        ]
    
    def get_styles(self, obj):
        """
        Get only active styles for this category, ordered by display_order.
        """
        active_styles = obj.styles.filter(is_active=True).order_by('display_order', 'name')
        return CustomStyleSerializer(active_styles, many=True, context=self.context).data


class CustomStyleListSerializer(serializers.ModelSerializer):
    """
    Simple serializer for listing styles without category details.
    Used for GET /api/customization/styles/?category=collar endpoint.
    """
    image_url = serializers.SerializerMethodField()
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_display_name = serializers.CharField(source='category.display_name', read_only=True)
    
    class Meta:
        model = CustomStyle
        fields = [
            'id',
            'category_name',
            'category_display_name',
            'name',
            'code',
            'image_url',
            'description',
            'display_order',
            'extra_price',
        ]
    
    def get_image_url(self, obj):
        """
        Convert image path to full URL.
        """
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None