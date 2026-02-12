from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CustomStyleCategoryListView, CustomStyleListView,
    UserStylePresetViewSet, MeasurementTemplateListView
)

# Create router for viewsets
router = DefaultRouter()
router.register(r'presets', UserStylePresetViewSet, basename='preset')

urlpatterns = [
    path('categories/', CustomStyleCategoryListView.as_view(), name='custom-style-categories'),
    path('styles/', CustomStyleListView.as_view(), name='custom-styles'),
    path('measurement-templates/', MeasurementTemplateListView.as_view(), name='measurement-templates'),
    path('', include(router.urls)),
]
