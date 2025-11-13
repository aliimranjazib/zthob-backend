from django.urls import path
from .views import SystemSettingsView

app_name = 'core'

urlpatterns = [
    path('settings/', SystemSettingsView.as_view(), name='system-settings'),
]

