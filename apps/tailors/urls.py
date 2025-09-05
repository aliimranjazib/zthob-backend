from django.urls import path

from apps.tailors.views import TailorFabricCategoryListCreateView, TailorFabricCategoryDetailView, TailorProfileView, TailorFabricView

urlpatterns = [
    path('profile/',TailorProfileView.as_view(),name='tailor-profile'),
    path('fabrics/', TailorFabricView.as_view(), name='tailor-fabrics'),
    path('category/',TailorFabricCategoryListCreateView.as_view(),name='fabric-category'),
    path('category/<int:pk>/', TailorFabricCategoryDetailView.as_view(), name='fabric-category-detail'),
]
