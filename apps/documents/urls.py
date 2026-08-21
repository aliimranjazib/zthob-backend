from django.urls import path

from apps.documents import studio_views

app_name = 'documents'

urlpatterns = [
    path('pdf-layout/', studio_views.layout_studio_page, name='pdf-layout-studio'),
    path('pdf-layout/api/', studio_views.layout_studio_api_get, name='pdf-layout-api-get'),
    path('pdf-layout/api/save/', studio_views.layout_studio_api_save, name='pdf-layout-api-save'),
    path(
        'pdf-layout/api/measurements/',
        studio_views.layout_studio_api_save_measurements,
        name='pdf-layout-api-measurements',
    ),
    path('pdf-layout/preview/', studio_views.layout_studio_preview, name='pdf-layout-preview'),
]
