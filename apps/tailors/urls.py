from django.urls import path

from apps.core.views import SendOTPView, VerifyOTPView
from apps.documents.views import OrderDocumentPreviewView
from apps.tailors.views import (
    # Profile views
    TailorProfileView,
    TailorMeasurementFeeView,
    TailorProfileSubmissionView,
    TailorProfileStatusView,
    TailorShopStatusView,
    
    # Catalog views
    TailorFabricCategoryListCreateView,
    TailorFabricCategoryDetailView,
    TailorFabricCountryListView,
    AdminFabricCountryListCreateView,
    AdminFabricCountryDetailView,
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
    TailorAddMeasurementsView,
    TailorOrderDownloadPDFView,
    TailorConfigView,
    
    # POS views
    TailorCustomerListView,
    TailorCreateCustomerView,
    TailorPOSCustomerOrdersView,
    TailorPOSCustomerOrderDetailView,
    TailorPOSFamilyMemberListCreateView,
    TailorPOSFamilyMemberDetailView,

    # Rating views
    SubmitTailorRatingView,
    TailorRatingListView,

    # Employee views
    TailorEmployeeListCreateView,
    TailorEmployeeDetailView,

    # Owner views
    OwnerShopListCreateView,
    OwnerShopDetailView,
    OwnerShopPinView,
    OwnerStaffListCreateView,
    OwnerStaffDetailView,
    OwnerStaffAssignmentListCreateView,
    OwnerStaffAssignmentDetailView,

    # Owner orders/reports
    OwnerOrderListView,
    OwnerOrderDetailView,
    OwnerReportsView,

    # Home/Dashboard
    TailorHomeAPIView,
)

urlpatterns = [
    # Dashboard Home
    path('home/', TailorHomeAPIView.as_view(), name='tailor-home'),

    # Profile URLs
    path('profile/', TailorProfileView.as_view(), name='tailor-profile'),
    path('measurement-fee/', TailorMeasurementFeeView.as_view(), name='tailor-measurement-fee'),
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

    # Fabric Country URLs
    path('fabric-countries/', TailorFabricCountryListView.as_view(), name='fabric-countries'),
    path('admin/fabric-countries/', AdminFabricCountryListCreateView.as_view(), name='admin-fabric-countries'),
    path('admin/fabric-countries/<int:pk>/', AdminFabricCountryDetailView.as_view(), name='admin-fabric-country-detail'),
    
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
    path('orders/<int:order_id>/measurements/', TailorAddMeasurementsView.as_view(), name='tailor-add-measurements'),
    path('orders/<int:order_id>/download-pdf/', TailorOrderDownloadPDFView.as_view(), name='tailor-order-download-pdf'),
    path('orders/<int:order_id>/document-preview/', OrderDocumentPreviewView.as_view(), name='tailor-order-document-preview'),
    path('config/', TailorConfigView.as_view(), name='tailor-config'),

    # POS URLs
    path('pos/customers/', TailorCustomerListView.as_view(), name='tailor-pos-customers'),
    path('pos/customers/create/', TailorCreateCustomerView.as_view(), name='tailor-pos-create-customer'),
    path('pos/customers/<int:customer_id>/orders/', TailorPOSCustomerOrdersView.as_view(), name='tailor-pos-customer-orders'),
    path('pos/customers/<int:customer_id>/orders/<int:order_id>/', TailorPOSCustomerOrderDetailView.as_view(), name='tailor-pos-customer-order-detail'),
    path('pos/customers/<int:customer_id>/family/', TailorPOSFamilyMemberListCreateView.as_view(), name='tailor-pos-family-list'),
    path('pos/customers/<int:customer_id>/family/<int:family_member_id>/', TailorPOSFamilyMemberDetailView.as_view(), name='tailor-pos-family-detail'),

    path('phone/send-otp/', SendOTPView.as_view(), name='customer-send-otp'),
    path('phone/verify-otp/', VerifyOTPView.as_view(), name='customer-verify-otp'),

    # Employee URLs
    path('employees/', TailorEmployeeListCreateView.as_view(), name='tailor-employees'),
    path('employees/<int:pk>/', TailorEmployeeDetailView.as_view(), name='tailor-employee-detail'),

    # Owner shop management
    path('owner/shops/', OwnerShopListCreateView.as_view(), name='owner-shops'),
    path('owner/shops/<int:shop_id>/', OwnerShopDetailView.as_view(), name='owner-shop-detail'),
    path('owner/shops/<int:shop_id>/pin/', OwnerShopPinView.as_view(), name='owner-shop-pin'),

    # Owner staff roster
    path('owner/staff/', OwnerStaffListCreateView.as_view(), name='owner-staff'),
    path('owner/staff/<int:staff_id>/', OwnerStaffDetailView.as_view(), name='owner-staff-detail'),
    path(
        'owner/staff/<int:staff_id>/assignments/',
        OwnerStaffAssignmentListCreateView.as_view(),
        name='owner-staff-assignments',
    ),
    path(
        'owner/staff/<int:staff_id>/assignments/<int:assignment_id>/',
        OwnerStaffAssignmentDetailView.as_view(),
        name='owner-staff-assignment-detail',
    ),

    path('owner/orders/', OwnerOrderListView.as_view(), name='owner-orders'),
    path('owner/orders/<int:order_id>/', OwnerOrderDetailView.as_view(), name='owner-order-detail'),
    path('owner/reports/', OwnerReportsView.as_view(), name='owner-reports'),
]
