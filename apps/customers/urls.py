from django.urls import path

from apps.customers.views import AddressListCreateAPIView, CustomerProfileAPIView, FabricCatalogAPIView, FamilyMemberAPIView


urlpatterns = [
    path('customerprofile/',CustomerProfileAPIView.as_view(),name='customer_profile'),
    path('allfabrics/',FabricCatalogAPIView.as_view(),name='all-fabrics'),
    path("addresses/", AddressListCreateAPIView.as_view(), name="address-list-create"),
    path("addresses/<int:pk>/", AddressListCreateAPIView.as_view(), name="address-detail"),
    path('family/', FamilyMemberAPIView.as_view(),name='family-member-list'),
    path('family/<int:pk>/', FamilyMemberAPIView.as_view(),name='family-member-detail')
    
    
]
