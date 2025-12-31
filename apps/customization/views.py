from rest_framework import generics, permissions
from rest_framework.response import Response
from .models import CustomStyleCategory, CustomStyle
from .serializers import (
    CustomStyleCategorySerializer,
    CustomStyleListSerializer
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
