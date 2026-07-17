from django.urls import path
from .views import SystemSettingsView, SliderListView, VersionView, MobileVersionView

app_name = 'core'

urlpatterns = [
    path('settings/', SystemSettingsView.as_view(), name='system-settings'),
    path('sliders/', SliderListView.as_view(), name='slider-list'),
    path('version/', VersionView.as_view(), name='version'),
    path('mobile-version/', MobileVersionView.as_view(), name='mobile-version'),
]

