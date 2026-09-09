from django.urls import path

from apps.fabrics.views.v2.analytics import V2FabricAnalyticsView
from apps.fabrics.views.v2.listings import (
    V2ShopFabricDetailView,
    V2ShopFabricListView,
    V2ShopFabricStockMovementView,
)
from apps.fabrics.views.v2.products import (
    V2FabricProductAssignView,
    V2FabricProductDetailView,
    V2FabricProductImageAddView,
    V2FabricProductImageDeleteView,
    V2FabricProductImagePrimaryView,
    V2FabricProductImageUpdateView,
    V2FabricProductListCreateView,
)

app_name = 'fabrics_v2'

urlpatterns = [
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
        'fabrics/products/<int:product_id>/images/add/',
        V2FabricProductImageAddView.as_view(),
        name='v2-fabric-product-image-add',
    ),
    path(
        'fabrics/products/<int:product_id>/images/<int:image_id>/set-primary/',
        V2FabricProductImagePrimaryView.as_view(),
        name='v2-fabric-product-image-set-primary',
    ),
    path(
        'fabrics/products/<int:product_id>/images/<int:image_id>/update/',
        V2FabricProductImageUpdateView.as_view(),
        name='v2-fabric-product-image-update',
    ),
    path(
        'fabrics/products/<int:product_id>/images/<int:image_id>/delete/',
        V2FabricProductImageDeleteView.as_view(),
        name='v2-fabric-product-image-delete',
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
