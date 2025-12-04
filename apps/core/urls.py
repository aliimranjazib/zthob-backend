from django.urls import path
from .views import SystemSettingsView, SliderListView, VersionView

app_name = 'core'

urlpatterns = [
    path('settings/', SystemSettingsView.as_view(), name='system-settings'),
    path('sliders/', SliderListView.as_view(), name='slider-list'),
    path('version/', VersionView.as_view(), name='version'),
]

