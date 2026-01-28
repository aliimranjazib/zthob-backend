"""
URL Configuration for Measurement API
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    MeasurementTemplateViewSet,
    MeasurementTemplateAdminViewSet,
    MeasurementFieldAdminViewSet,
)

# Customer-facing API router
router = DefaultRouter()
router.register(r'templates', MeasurementTemplateViewSet, basename='measurement-template')

# Admin API router
admin_router = DefaultRouter()
admin_router.register(r'templates', MeasurementTemplateAdminViewSet, basename='admin-measurement-template')
admin_router.register(r'fields', MeasurementFieldAdminViewSet, basename='admin-measurement-field')

urlpatterns = [
    # Customer API: /api/measurements/
    path('', include(router.urls)),
    
    # Admin API: /api/admin/measurements/
    path('admin/', include(admin_router.urls)),
]
