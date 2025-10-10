# apps/tailors/serializers/service_areas.py
from rest_framework import serializers
from ..models import ServiceArea, TailorServiceArea

class ServiceAreaSerializer(serializers.ModelSerializer):
    """Serializer for service areas."""
    
    class Meta:
        model = ServiceArea
        fields = [
            'id', 'name', 'city', 'is_active', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class ServiceAreaBasicSerializer(serializers.ModelSerializer):
    """Basic serializer for service areas (for dropdowns, etc.)."""
    
    class Meta:
        model = ServiceArea
        fields = ['id', 'name', 'city']

class TailorServiceAreaSerializer(serializers.ModelSerializer):
    """Serializer for tailor service areas."""
    service_area = ServiceAreaBasicSerializer(read_only=True)
    service_area_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = TailorServiceArea
        fields = [
            'id', 'service_area', 'service_area_id', 'is_primary',
            'delivery_fee', 'estimated_delivery_days', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_service_area_id(self, value):
        """Validate that the service area exists and is active."""
        try:
            service_area = ServiceArea.objects.get(id=value, is_active=True)
        except ServiceArea.DoesNotExist:
            raise serializers.ValidationError("Service area not found or inactive.")
        return value
    
    def validate(self, data):
        """Validate that only one primary service area per tailor."""
        tailor = self.context.get('tailor')
        is_primary = data.get('is_primary', False)
        
        if is_primary and tailor:
            # Check if there's already a primary service area
            existing_primary = TailorServiceArea.objects.filter(
                tailor=tailor, is_primary=True
            ).exclude(pk=self.instance.pk if self.instance else None)
            
            if existing_primary.exists():
                raise serializers.ValidationError(
                    "Only one service area can be marked as primary."
                )
        
        return data
    
    def create(self, validated_data):
        """Create tailor service area."""
        service_area_id = validated_data.pop('service_area_id')
        service_area = ServiceArea.objects.get(id=service_area_id)
        validated_data['service_area'] = service_area
        return super().create(validated_data)

class TailorServiceAreaCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating tailor service areas."""
    
    class Meta:
        model = TailorServiceArea
        fields = [
            'service_area', 'is_primary', 'delivery_fee', 'estimated_delivery_days'
        ]
    
    def validate(self, data):
        """Validate that only one primary service area per tailor."""
        tailor = self.context.get('tailor')
        is_primary = data.get('is_primary', False)
        
        if is_primary and tailor:
            # Check if there's already a primary service area
            existing_primary = TailorServiceArea.objects.filter(
                tailor=tailor, is_primary=True
            )
            
            if existing_primary.exists():
                raise serializers.ValidationError(
                    "Only one service area can be marked as primary."
                )
        
        return data

class ServiceAreaWithTailorCountSerializer(serializers.ModelSerializer):
    """Serializer for service areas with tailor count (admin view)."""
    tailor_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ServiceArea
        fields = [
            'id', 'name', 'city', 'is_active', 
            'tailor_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_tailor_count(self, obj):
        """Get the number of tailors serving this area."""
        return obj.tailors.count()
