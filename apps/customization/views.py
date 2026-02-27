from rest_framework import generics, permissions, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import CustomStyleCategory, CustomStyle, UserStylePreset, MeasurementTemplate
from .serializers import (
    CustomStyleCategorySerializer,
    CustomStyleListSerializer,
    UserStylePresetSerializer,
    UserStylePresetCreateSerializer,
    MeasurementTemplateSerializer
)


class CustomStyleCategoryListView(generics.ListAPIView):
    """
    GET /api/customization/categories/
    Returns all active style categories with their styles
    """
    serializer_class = CustomStyleCategorySerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        """Only return active categories that have active styles"""
        return CustomStyleCategory.objects.filter(
            is_active=True,
            styles__is_active=True
        ).distinct().prefetch_related('styles')


class CustomStyleListView(generics.ListAPIView):
    """
    GET /api/customization/styles/
    GET /api/customization/styles/?category=collar
    Returns styles, optionally filtered by category
    """
    serializer_class = CustomStyleListSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        """Filter styles by category if provided"""
        queryset = CustomStyle.objects.filter(is_active=True).select_related('category')
        
        # Filter by category if provided in query params
        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(category__name=category)
        
        return queryset.order_by('category__display_order', 'display_order', 'name')


class UserStylePresetViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user style presets
    
    list: Get all presets for current user
    create: Create a new preset
    retrieve: Get a specific preset
    update: Update a preset
    destroy: Delete a preset
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Only return presets for the current user"""
        return UserStylePreset.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        """Use different serializers for read vs write operations"""
        if self.action in ['create', 'update', 'partial_update']:
            return UserStylePresetCreateSerializer
        return UserStylePresetSerializer
    
    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """Set this preset as user's default"""
        preset = self.get_object()
        preset.set_as_default()
        serializer = self.get_serializer(preset)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def use(self, request, pk=None):
        """Increment usage counter when preset is used"""
        preset = self.get_object()
        preset.increment_usage()
        serializer = self.get_serializer(preset)
        return Response(serializer.data)


class MeasurementTemplateListView(generics.ListAPIView):
    """
    GET /api/customization/measurement-templates/
    Returns all active measurement templates with their fields.
    Used by tailor/customer apps to build dynamic measurement forms.
    """
    serializer_class = MeasurementTemplateSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return MeasurementTemplate.objects.filter(
            is_active=True
        ).prefetch_related('fields').order_by('display_order', 'name')
