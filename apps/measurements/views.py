"""
API Views for Measurement Templates and Fields

Provides REST API endpoints for both customer-facing and admin operations.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.db.models import Count, Q
from zthob.utils import api_response
from .models import MeasurementTemplate, MeasurementField
from .serializers import (
    MeasurementTemplateListSerializer,
    MeasurementTemplateDetailSerializer,
    MeasurementTemplateAdminSerializer,
    MeasurementFieldSerializer,
    MeasurementFieldAdminSerializer,
    MeasurementValidationSerializer,
)


class MeasurementTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Customer-facing API for measurement templates
    
    GET /api/measurements/templates/ - List all active templates
    GET /api/measurements/templates/{id}/ - Get template details with fields
    POST /api/measurements/templates/validate/ - Validate measurements
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return only active templates with field count"""
        return MeasurementTemplate.objects.filter(
            is_active=True
        ).annotate(
            field_count=Count('fields', filter=Q(fields__is_active=True))
        ).prefetch_related('fields').order_by('garment_type', 'name_en')
    
    def get_serializer_class(self):
        """Use different serializers for list and detail views"""
        if self.action == 'list':
            return MeasurementTemplateListSerializer
        return MeasurementTemplateDetailSerializer
    
    def list(self, request):
        """List all active measurement templates"""
        queryset = self.get_queryset()
        
        # Optional filtering by garment type
        garment_type = request.query_params.get('garment_type')
        if garment_type:
            queryset = queryset.filter(garment_type=garment_type)
        
        # Get default template if requested
        default_only = request.query_params.get('default_only', '').lower() == 'true'
        if default_only:
            queryset = queryset.filter(is_default=True)
        
        serializer = self.get_serializer(queryset, many=True)
        
        return api_response(
            success=True,
            message='Measurement templates retrieved successfully',
            data={'templates': serializer.data},
            status_code=status.HTTP_200_OK
        )
    
    def retrieve(self, request, pk=None):
        """Get detailed template with all active fields"""
        try:
            template = self.get_queryset().get(pk=pk)
        except MeasurementTemplate.DoesNotExist:
            return api_response(
                success=False,
                message='Measurement template not found',
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        serializer = self.get_serializer(template)
        
        return api_response(
            success=True,
            message='Template details retrieved successfully',
            data={'template': serializer.data},
            status_code=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['post'])
    def validate(self, request):
        """
        Validate customer measurements against a template
        
        POST /api/measurements/templates/validate/
        {
            "template_id": 1,
            "measurements": {
                "chest": 100,
                "shoulder": 45,
                "thobe_length": 150
            }
        }
        """
        serializer = MeasurementValidationSerializer(data=request.data)
        
        if serializer.is_valid():
            return api_response(
                success=True,
                message='Measurements are valid',
                data={
                    'valid': True,
                    'template': MeasurementTemplateListSerializer(
                        serializer.validated_data['template']
                    ).data
                },
                status_code=status.HTTP_200_OK
            )
        
        return api_response(
            success=False,
            message='Measurement validation failed',
            data={
                'valid': False,
                'errors': serializer.errors
            },
            status_code=status.HTTP_400_BAD_REQUEST
        )


class MeasurementTemplateAdminViewSet(viewsets.ModelViewSet):
    """
    Admin API for managing measurement templates
    
    POST /api/admin/measurements/templates/ - Create template
    PUT /api/admin/measurements/templates/{id}/ - Update template
    DELETE /api/admin/measurements/templates/{id}/ - Soft delete (deactivate)
    """
    permission_classes = [IsAdminUser]
    serializer_class = MeasurementTemplateAdminSerializer
    
    def get_queryset(self):
        """Return all templates including inactive ones for admins"""
        return MeasurementTemplate.objects.annotate(
            field_count=Count('fields', filter=Q(fields__is_active=True))
        ).prefetch_related('fields').order_by('-created_at')
    
    def create(self, request):
        """Create new measurement template"""
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            template = serializer.save()
            return api_response(
                success=True,
                message=f'Template "{template.name_en}" created successfully',
                data={'template': serializer.data},
                status_code=status.HTTP_201_CREATED
            )
        
        return api_response(
            success=False,
            message='Failed to create template',
            data={'errors': serializer.errors},
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    def update(self, request, pk=None):
        """Update existing template"""
        try:
            template = self.get_queryset().get(pk=pk)
        except MeasurementTemplate.DoesNotExist:
            return api_response(
                success=False,
                message='Template not found',
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        serializer = self.get_serializer(template, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return api_response(
                success=True,
                message=f'Template "{template.name_en}" updated successfully',
                data={'template': serializer.data},
                status_code=status.HTTP_200_OK
            )
        
        return api_response(
            success=False,
            message='Failed to update template',
            data={'errors': serializer.errors},
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    def destroy(self, request, pk=None):
        """Soft delete template (set inactive)"""
        try:
            template = self.get_queryset().get(pk=pk)
        except MeasurementTemplate.DoesNotExist:
            return api_response(
                success=False,
                message='Template not found',
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # Soft delete by marking inactive
        template.is_active = False
        template.is_default = False  # Remove default status
        template.save()
        
        return api_response(
            success=True,
            message=f'Template "{template.name_en}" deactivated successfully',
            status_code=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """
        Duplicate a template with all its fields
        
        POST /api/admin/measurements/templates/{id}/duplicate/
        """
        try:
            original = self.get_queryset().get(pk=pk)
        except MeasurementTemplate.DoesNotExist:
            return api_response(
                success=False,
                message='Template not found',
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # Create duplicate template
        duplicate = MeasurementTemplate.objects.create(
            name_en=f"{original.name_en} (Copy)",
            name_ar=f"{original.name_ar} (نسخة)",
            description_en=original.description_en,
            description_ar=original.description_ar,
            garment_type=original.garment_type,
            is_default=False,
            is_active=False,
        )
        
        # Duplicate all fields
        for field in original.fields.all():
            MeasurementField.objects.create(
                template=duplicate,
                field_key=field.field_key,
                display_name_en=field.display_name_en,
                display_name_ar=field.display_name_ar,
                unit=field.unit,
                min_value=field.min_value,
                max_value=field.max_value,
                is_required=field.is_required,
                order=field.order,
                category=field.category,
                help_text_en=field.help_text_en,
                help_text_ar=field.help_text_ar,
                is_active=field.is_active,
            )
        
        serializer = self.get_serializer(duplicate)
        
        return api_response(
            success=True,
            message=f'Template duplicated successfully as "{duplicate.name_en}"',
            data={'template': serializer.data},
            status_code=status.HTTP_201_CREATED
        )


class MeasurementFieldAdminViewSet(viewsets.ModelViewSet):
    """
    Admin API for managing measurement fields
    
    POST /api/admin/measurements/fields/ - Add field to template
    PUT /api/admin/measurements/fields/{id}/ - Update field
    DELETE /api/admin/measurements/fields/{id}/ - Delete field
    """
    permission_classes = [IsAdminUser]
    serializer_class = MeasurementFieldAdminSerializer
    queryset = MeasurementField.objects.select_related('template').all()
    
    def create(self, request):
        """Add new field to a template"""
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            field = serializer.save()
            return api_response(
                success=True,
                message=f'Field "{field.display_name_en}" added successfully',
                data={'field': serializer.data},
                status_code=status.HTTP_201_CREATED
            )
        
        return api_response(
            success=False,
            message='Failed to create field',
            data={'errors': serializer.errors},
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    def update(self, request, pk=None):
        """Update existing field"""
        try:
            field = self.get_queryset().get(pk=pk)
        except MeasurementField.DoesNotExist:
            return api_response(
                success=False,
                message='Field not found',
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        serializer = self.get_serializer(field, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return api_response(
                success=True,
                message=f'Field "{field.display_name_en}" updated successfully',
                data={'field': serializer.data},
                status_code=status.HTTP_200_OK
            )
        
        return api_response(
            success=False,
            message='Failed to update field',
            data={'errors': serializer.errors},
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    def destroy(self, request, pk=None):
        """Delete field permanently"""
        try:
            field = self.get_queryset().get(pk=pk)
        except MeasurementField.DoesNotExist:
            return api_response(
                success=False,
                message='Field not found',
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        field_name = field.display_name_en
        field.delete()
        
        return api_response(
            success=True,
            message=f'Field "{field_name}" deleted successfully',
            status_code=status.HTTP_200_OK
        )
