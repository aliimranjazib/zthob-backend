from django.urls import path

from apps.tailors.views.v2.business import V2BusinessView
from apps.tailors.views.v2.fabrics import (
    V2FabricAnalyticsView,
    V2FabricProductAssignView,
    V2FabricProductDetailView,
    V2FabricProductListCreateView,
    V2ShopFabricDetailView,
    V2ShopFabricListView,
    V2ShopFabricStockMovementView,
)
from apps.tailors.views.v2.shops import V2ShopDetailView, V2ShopListCreateView, V2ShopPinView
from apps.tailors.views.v2.staff import (
    V2StaffAssignmentListCreateView,
    V2StaffDetailView,
    V2StaffListCreateView,
)

app_name = 'tailors_v2'

urlpatterns = [
    path('business/', V2BusinessView.as_view(), name='v2-business'),
    path('shops/', V2ShopListCreateView.as_view(), name='v2-shops'),
    path('shops/<int:shop_id>/', V2ShopDetailView.as_view(), name='v2-shop-detail'),
    path('shops/<int:shop_id>/pin/', V2ShopPinView.as_view(), name='v2-shop-pin'),
    path('staff/', V2StaffListCreateView.as_view(), name='v2-staff'),
    path('staff/<int:staff_id>/', V2StaffDetailView.as_view(), name='v2-staff-detail'),
    path(
        'staff/<int:staff_id>/assignments/',
        V2StaffAssignmentListCreateView.as_view(),
        name='v2-staff-assignments',
    ),
    path('fabrics/products/', V2FabricProductListCreateView.as_view(), name='v2-fabric-products'),
    path(
        'fabrics/products/<int:product_id>/',
        V2FabricProductDetailView.as_view(),
        name='v2-fabric-product-detail',
    ),
    path(
        'fabrics/products/<int:product_id>/assign/',
        V2FabricProductAssignView.as_view(),
        name='v2-fabric-product-assign',
    ),
    path(
        'shops/<int:shop_id>/fabrics/',
        V2ShopFabricListView.as_view(),
        name='v2-shop-fabrics',
    ),
    path(
        'shops/<int:shop_id>/fabrics/<int:shop_fabric_id>/',
        V2ShopFabricDetailView.as_view(),
        name='v2-shop-fabric-detail',
    ),
    path(
        'shops/<int:shop_id>/fabrics/<int:shop_fabric_id>/stock-movements/',
        V2ShopFabricStockMovementView.as_view(),
        name='v2-shop-fabric-stock-movements',
    ),
    path('analytics/fabrics/', V2FabricAnalyticsView.as_view(), name='v2-fabric-analytics'),
]
