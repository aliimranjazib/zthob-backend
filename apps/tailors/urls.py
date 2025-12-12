from django.urls import path

from apps.core.views import SendOTPView, VerifyOTPView
from apps.tailors.views import (
    # Profile views
    TailorProfileView,
    TailorProfileSubmissionView,
    TailorProfileStatusView,
    TailorShopStatusView,
    
    # Catalog views
    TailorFabricCategoryListCreateView,
    TailorFabricCategoryDetailView,
    TailorFabricView,
    TailorFabricDetailView,
    TailorFabricTypeListCreateView,
    TailorFabricTypeRetrieveUpdateDestroyView,
    FabricImagePrimaryView,
    TailorFabricTagsListCreateView,
    TailorFabricTagsRetrieveUpdateDestroyView,
    FabricImageDeleteView,
    FabricImageAddView,
    FabricImageUpdateView,
    
    # Review views
    TailorProfileReviewListView,
    TailorProfileReviewDetailView,
    
    # Service Area views
    AvailableServiceAreasView,
    AdminServiceAreasView,
    AdminServiceAreaDetailView,
    
    # Address views
    TailorAddressView,
    TailorAddressCreateUpdateView,
    TailorAddressDeleteView,
    
    # Analytics views
    TailorAnalyticsView,
    
    # Order views
    TailorUpdateOrderStatusView,
)

urlpatterns = [
    # Profile URLs
    path('profile/', TailorProfileView.as_view(), name='tailor-profile'),
    path('profile/submit/', TailorProfileSubmissionView.as_view(), name='tailor-profile-submit'),
    path('profile/status/', TailorProfileStatusView.as_view(), name='tailor-profile-status'),
    path('shop/status/', TailorShopStatusView.as_view(), name='tailor-shop-status'),
    
    # Fabric URLs
    path('fabrics/', TailorFabricView.as_view(), name='tailor-fabrics'),
    path('fabrics/<int:pk>/', TailorFabricDetailView.as_view(), name='tailor-fabric-detail'),
    
    # Fabric Type URLs
    path('fabric-type/', TailorFabricTypeListCreateView.as_view(), name='fabrics-type'),
    path('fabric-type/<int:pk>/', TailorFabricTypeRetrieveUpdateDestroyView.as_view(), name='fabrics-type-detail'),
    
    # Fabric Tags URLs
    path('fabric-tags/', TailorFabricTagsListCreateView.as_view(), name='fabrics-tags'),
    path('fabric-tags/<int:pk>/', TailorFabricTagsRetrieveUpdateDestroyView.as_view(), name='fabrics-tags-detail'),
    
    # Fabric Category URLs
    path('category/', TailorFabricCategoryListCreateView.as_view(), name='fabric-category'),
    path('category/<int:pk>/', TailorFabricCategoryDetailView.as_view(), name='fabric-category-detail'),
    
    # Fabric Image URLs
    path('images/<int:image_id>/set-primary/', FabricImagePrimaryView.as_view(), name='fabric-image-set-primary'),
    path('images/<int:image_id>/delete/', FabricImageDeleteView.as_view(), name='fabric-image-delete'),
    path('images/<int:image_id>/update/', FabricImageUpdateView.as_view(), name='fabric-image-update'),
    path('fabrics/<int:fabric_id>/images/add/', FabricImageAddView.as_view(), name='fabric-image-add'),
    
    # Admin Review URLs
    path('admin/profiles/review/', TailorProfileReviewListView.as_view(), name='admin-profiles-review'),
    path('admin/profiles/review/<int:pk>/', TailorProfileReviewDetailView.as_view(), name='admin-profile-review-detail'),
    
    # Service Area URLs
    path('service-areas/available/', AvailableServiceAreasView.as_view(), name='available-service-areas'),
    
    # Admin Service Area URLs
    path('admin/service-areas/', AdminServiceAreasView.as_view(), name='admin-service-areas'),
    path('admin/service-areas/<int:pk>/', AdminServiceAreaDetailView.as_view(), name='admin-service-area-detail'),

    # Address URLs (single address per tailor)
    path('address/', TailorAddressView.as_view(), name='tailor-address'),
    path('address/manage/', TailorAddressCreateUpdateView.as_view(), name='tailor-address-manage'),
    path('address/delete/', TailorAddressDeleteView.as_view(), name='tailor-address-delete'),

    # Analytics URLs
    path('analytics/', TailorAnalyticsView.as_view(), name='tailor-analytics'),
    
    # Order URLs
    path('orders/<int:order_id>/update-status/', TailorUpdateOrderStatusView.as_view(), name='tailor-update-order-status'),

    path('phone/send-otp/', SendOTPView.as_view(), name='customer-send-otp'),
    path('phone/verify-otp/', VerifyOTPView.as_view(), name='customer-verify-otp'),
]

