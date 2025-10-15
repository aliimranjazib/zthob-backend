# apps/tailors/serializers/service_areas.py
from rest_framework import serializers
from ..models import ServiceArea

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

