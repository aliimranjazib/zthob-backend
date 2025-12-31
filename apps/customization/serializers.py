from rest_framework import serializers
from .models import CustomStyleCategory, CustomStyle, UserStylePreset
from zthob.translations import translate_message, get_language_from_request


class CustomStyleSerializer(serializers.ModelSerializer):
    """
    Serializer for individual custom styles.
    Converts image path to full URL for API responses.
    Translates name based on Accept-Language header.
    """
    image_url = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    
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
    
    def get_name(self, obj):
        """
        Return translated name based on Accept-Language header.
        Falls back to original name if translation not found.
        """
        request = self.context.get('request')
        language = get_language_from_request(request)
        return translate_message(obj.name, language)
    
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
    Translates display_name based on Accept-Language header.
    """
    styles = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomStyleCategory
        fields = [
            'id',
            'name',
            'display_name',
            'display_order',
            'styles',
        ]
    
    def get_display_name(self, obj):
        """
        Return translated display name based on Accept-Language header.
        Falls back to original display_name if translation not found.
        """
        request = self.context.get('request')
        language = get_language_from_request(request)
        return translate_message(obj.display_name, language)
    
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
    Translates name and category_display_name based on Accept-Language header.
    """
    image_url = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_display_name = serializers.SerializerMethodField()
    
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
    
    def get_name(self, obj):
        """
        Return translated name based on Accept-Language header.
        """
        request = self.context.get('request')
        language = get_language_from_request(request)
        return translate_message(obj.name, language)
    
    def get_category_display_name(self, obj):
        """
        Return translated category display name based on Accept-Language header.
        """
        request = self.context.get('request')
        language = get_language_from_request(request)
        return translate_message(obj.category.display_name, language)
    
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
class UserStylePresetSerializer(serializers.ModelSerializer):
    """
    Serializer for user style presets with expanded style details
    """
    styles_details = serializers.SerializerMethodField()
    
    class Meta:
        model = UserStylePreset
        fields = [
            'id',
            'name',
            'description',
            'styles',
            'styles_details',
            'is_default',
            'usage_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['usage_count', 'created_at', 'updated_at']
    
    def get_styles_details(self, obj):
        """
        Expand style IDs to full style objects with images
        """
        if not obj.styles:
            return []
        
        result = []
        for selection in obj.styles:
            style_id = selection.get('style_id')
            category = selection.get('category')
            
            if style_id:
                try:
                    style = CustomStyle.objects.select_related('category').get(
                        id=style_id,
                        is_active=True
                    )
                    result.append({
                        'category': category,
                        'category_display': style.category.display_name,
                        'style_id': style.id,
                        'style_name': style.name,
                        'style_code': style.code,
                        'image_url': self.context['request'].build_absolute_uri(style.image.url) if style.image else None
                    })
                except CustomStyle.DoesNotExist:
                    pass
        
        return result


class UserStylePresetCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating/updating presets
    """
    class Meta:
        model = UserStylePreset
        fields = [
            'name',
            'description',
            'styles',
            'is_default',
        ]
    
    def validate_styles(self, value):
        """Validate styles array structure"""
        if not isinstance(value, list):
            raise serializers.ValidationError("styles must be an array")
        
        if not value:
            raise serializers.ValidationError("styles cannot be empty")
        
        for idx, style_selection in enumerate(value):
            if not isinstance(style_selection, dict):
                raise serializers.ValidationError(f"styles[{idx}] must be an object")
            
            # Check required fields
            if 'category' not in style_selection:
                raise serializers.ValidationError(f"styles[{idx}] missing 'category'")
            if 'style_id' not in style_selection:
                raise serializers.ValidationError(f"styles[{idx}] missing 'style_id'")
            
            # Validate style exists
            style_id = style_selection.get('style_id')
            try:
                CustomStyle.objects.get(id=style_id, is_active=True)
            except CustomStyle.DoesNotExist:
                raise serializers.ValidationError(f"Style with id {style_id} not found or inactive")
        
        return value
    
    def create(self, validated_data):
        """Auto-assign current user"""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)