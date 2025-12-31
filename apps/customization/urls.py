from django.urls import path
from .views import CustomStyleCategoryListView, CustomStyleListView

urlpatterns = [
    path('categories/', CustomStyleCategoryListView.as_view(), name='custom-style-categories'),
    path('styles/', CustomStyleListView.as_view(), name='custom-styles'),
]
