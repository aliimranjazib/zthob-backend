from django.urls import path

from apps.core.views import SendOTPView, VerifyOTPView
from apps.customers.views import AddressListView, AddressCreateView, AddressDetailView, CustomerProfileAPIView, FabricCatalogAPIView, FamilyMemberListView, FamilyMemberDetailView, TailorFabricsAPIView, TailorListAPIView, FabricFavoriteToggleView, FabricFavoriteListView


urlpatterns = [
    path('customerprofile/',CustomerProfileAPIView.as_view(),name='customer_profile'),
    path('allfabrics/',FabricCatalogAPIView.as_view(),name='all-fabrics'),
    path("addresses/", AddressListView.as_view(), name="address-list"),
    path("addresses/create/", AddressCreateView.as_view(), name="address-create"),
    path("addresses/<int:pk>/", AddressDetailView.as_view(), name="address-detail"),
    path('family/', FamilyMemberListView.as_view(), name='family-member-list'),
    path('family/<int:pk>/', FamilyMemberDetailView.as_view(), name='family-member-detail'),
    path('phone/send-otp/', SendOTPView.as_view(), name='customer-send-otp'),
    path('phone/verify-otp/', VerifyOTPView.as_view(), name='customer-verify-otp'),
    path('tailors/', TailorListAPIView.as_view(), name='tailor-list'),
    path('tailors/<int:tailor_id>/fabrics',TailorFabricsAPIView.as_view(),name='tailor-fabrics'),
    # Fabric Favorites
    path('fabrics/<int:fabric_id>/favorite/', FabricFavoriteToggleView.as_view(), name='fabric-favorite-toggle'),
    path('favorites/', FabricFavoriteListView.as_view(), name='favorites-list'),
]
