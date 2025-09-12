from django.urls import path

from apps.tailors.views import (
    TailorFabricCategoryListCreateView,
    TailorFabricCategoryDetailView,
    TailorProfileView,
    TailorFabricView,
    FabricImagePrimaryView,
    FabricImageDeleteView
)

urlpatterns = [
    path('profile/', TailorProfileView.as_view(), name='tailor-profile'),
    path('fabrics/', TailorFabricView.as_view(), name='tailor-fabrics'),
    path('category/', TailorFabricCategoryListCreateView.as_view(), name='fabric-category'),
    path('category/<int:pk>/', TailorFabricCategoryDetailView.as_view(), name='fabric-category-detail'),
    path('images/<int:image_id>/set-primary/', FabricImagePrimaryView.as_view(), name='fabric-image-set-primary'),
    path('images/<int:image_id>/delete/', FabricImageDeleteView.as_view(), name='fabric-image-delete'),
]
