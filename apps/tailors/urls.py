from django.urls import path

from apps.tailors.views import (
    TailorFabricCategoryListCreateView,
    TailorFabricCategoryDetailView,
    TailorProfileView,
    TailorFabricView,
    TailorFabricDetailView,
    TailorFabricTypeListCreateView,
    TailorFabricTypeRetrieveUpdateDestroyView,
    FabricImagePrimaryView,
    TailorFabricTagsListCreateView,
    TailorFabricTagsRetrieveUpdateDestroyView,
    FabricImageDeleteView
)

urlpatterns = [
    path('profile/', TailorProfileView.as_view(), name='tailor-profile'),
    path('fabrics/', TailorFabricView.as_view(), name='tailor-fabrics'),
    path('fabrics/<int:pk>/', TailorFabricDetailView.as_view(), name='tailor-fabric-detail'),
    path('fabric-type/', TailorFabricTypeListCreateView.as_view(),name='fabrics-type'),
    path('fabric-type/<int:pk>/', TailorFabricTypeRetrieveUpdateDestroyView.as_view(),name='fabrics-type-detail'),
    path('fabric-tags/', TailorFabricTagsListCreateView.as_view(),name='fabrics-tags'),
    path('fabric-tags/<int:pk>/', TailorFabricTagsRetrieveUpdateDestroyView.as_view(),name='fabrics-tags-detail'),

    path('category/', TailorFabricCategoryListCreateView.as_view(), name='fabric-category'),
    path('category/<int:pk>/', TailorFabricCategoryDetailView.as_view(), name='fabric-category-detail'),
    path('images/<int:image_id>/set-primary/', FabricImagePrimaryView.as_view(), name='fabric-image-set-primary'),
    path('images/<int:image_id>/delete/', FabricImageDeleteView.as_view(), name='fabric-image-delete'),
]
