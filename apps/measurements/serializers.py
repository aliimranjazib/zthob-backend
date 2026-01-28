"""
API Serializers for Measurement Templates and Fields

Provides REST API serialization with language-aware responses.
"""
from rest_framework import serializers
from .models import MeasurementTemplate, MeasurementField


class MeasurementFieldSerializer(serializers.ModelSerializer):
    """Serializer for measurement fields with language support"""
    
    display_name = serializers.SerializerMethodField()
    help_text = serializers.SerializerMethodField()
    
    class Meta:
        model = MeasurementField
        fields = [
            'id',
            'field_key',
            'display_name',
            'display_name_en',
            'display_name_ar',
            'unit',
            'min_value',
            'max_value',
            'is_required',
            'order',
            'category',
            'help_text',
            'help_text_en',
            'help_text_ar',
        ]
        read_only_fields = ['id']
    
    def get_display_name(self, obj):
        """Return display name based on request language"""
        request = self.context.get('request')
        if request:
            language = request.headers.get('Accept-Language', 'en')
            if language.startswith('ar'):
                return obj.display_name_ar
        return obj.display_name_en
    
    def get_help_text(self, obj):
        """Return help text based on request language"""
        request = self.context.get('request')
        if request:
            language = request.headers.get('Accept-Language', 'en')
            if language.startswith('ar'):
                return obj.help_text_ar or obj.help_text_en
        return obj.help_text_en or obj.help_text_ar


class MeasurementFieldAdminSerializer(serializers.ModelSerializer):
    """Admin serializer with full field details for management"""
    
    template_name = serializers.CharField(source='template.name_en', read_only=True)
    value_range = serializers.SerializerMethodField()
    
    class Meta:
        model = MeasurementField
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_value_range(self, obj):
        """Return formatted value range string"""
        return f"{obj.min_value} - {obj.max_value} {obj.unit}"
    
    def validate(self, data):
        """Validate field configuration"""
        min_value = data.get('min_value')
        max_value = data.get('max_value')
        
        if min_value and max_value and min_value >= max_value:
            raise serializers.ValidationError({
                'min_value': 'Minimum value must be less than maximum value',
                'max_value': 'Maximum value must be greater than minimum value'
            })
        
        return data


class MeasurementTemplateListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for template lists"""
    
    name = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    field_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = MeasurementTemplate
        fields = [
            'id',
            'name',
            'name_en',
            'name_ar',
            'description',
            'garment_type',
            'field_count',
            'is_default',
            'updated_at',
        ]
    
    def get_name(self, obj):
        """Return name based on request language"""
        request = self.context.get('request')
        if request:
            language = request.headers.get('Accept-Language', 'en')
            if language.startswith('ar'):
                return obj.name_ar
        return obj.name_en
    
    def get_description(self, obj):
        """Return description based on request language"""
        request = self.context.get('request')
        if request:
            language = request.headers.get('Accept-Language', 'en')
            if language.startswith('ar'):
                return obj.description_ar or obj.description_en
        return obj.description_en or obj.description_ar


class MeasurementTemplateDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer with all fields for template detail view"""
    
    name = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    fields = MeasurementFieldSerializer(many=True, read_only=True, source='get_active_fields')
    field_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = MeasurementTemplate
        fields = [
            'id',
            'name',
            'name_en',
            'name_ar',
            'description',
            'description_en',
            'description_ar',
            'garment_type',
            'fields',
            'field_count',
            'is_default',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_name(self, obj):
        """Return name based on request language"""
        request = self.context.get('request')
        if request:
            language = request.headers.get('Accept-Language', 'en')
            if language.startswith('ar'):
                return obj.name_ar
        return obj.name_en
    
    def get_description(self, obj):
        """Return description based on request language"""
        request = self.context.get('request')
        if request:
            language = request.headers.get('Accept-Language', 'en')
            if language.startswith('ar'):
                return obj.description_ar or obj.description_en
        return obj.description_en or obj.description_ar


class MeasurementTemplateAdminSerializer(serializers.ModelSerializer):
    """Admin serializer with all fields including inactive ones"""
    
    fields = MeasurementFieldAdminSerializer(many=True, read_only=True)
    field_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = MeasurementTemplate
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, data):
        """Validate template configuration"""
        # Check if trying to set as default when another default exists
        if data.get('is_default') and data.get('is_active'):
            garment_type = data.get('garment_type')
            if garment_type:
                existing_default = MeasurementTemplate.objects.filter(
                    garment_type=garment_type,
                    is_default=True,
                    is_active=True
                ).exclude(pk=self.instance.pk if self.instance else None)
                
                if existing_default.exists():
                    raise serializers.ValidationError({
                        'is_default': (
                            f'A default template already exists for {garment_type}. '
                            f'Please deactivate it first.'
                        )
                    })
        
        return data


class MeasurementValidationSerializer(serializers.Serializer):
    """Serializer for validating customer measurements against template"""
    
    template_id = serializers.IntegerField(required=True)
    measurements = serializers.DictField(
        child=serializers.DecimalField(max_digits=6, decimal_places=2),
        required=True
    )
    
    def validate(self, data):
        """Validate measurements against template rules"""
        template_id = data.get('template_id')
        measurements = data.get('measurements')
        
        try:
            template = MeasurementTemplate.objects.prefetch_related('fields').get(
                id=template_id,
                is_active=True
            )
        except MeasurementTemplate.DoesNotExist:
            raise serializers.ValidationError({
                'template_id': 'Invalid or inactive template'
            })
        
        errors = {}
        active_fields = template.get_active_fields()
        
        # Check required fields
        for field in active_fields:
            if field.is_required and field.field_key not in measurements:
                errors[field.field_key] = f'{field.display_name_en} is required'
        
        # Validate each measurement value
        for field_key, value in measurements.items():
            try:
                field = active_fields.get(field_key=field_key)
                is_valid, error_msg = field.validate_value(value)
                if not is_valid:
                    errors[field_key] = error_msg
            except MeasurementField.DoesNotExist:
                errors[field_key] = f'Unknown measurement field: {field_key}'
        
        if errors:
            raise serializers.ValidationError({'measurements': errors})
        
        data['template'] = template
        return data
