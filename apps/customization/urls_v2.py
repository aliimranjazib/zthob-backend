from django.urls import path

from .views import UserStylePresetV2ListView

urlpatterns = [
    path('presets/', UserStylePresetV2ListView.as_view(), name='customization-presets-v2'),
]
