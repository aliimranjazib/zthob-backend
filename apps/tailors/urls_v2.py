from django.urls import path

from apps.tailors.views.v2.business import V2BusinessView
from apps.tailors.views.v2.shops import (
    V2ShopDetailView,
    V2ShopListCreateView,
    V2ShopPinView,
    V2ShopPublishReadinessView,
    V2ShopPublishView,
)
from apps.tailors.views.v2.staff import (
    V2StaffAssignmentDetailView,
    V2StaffAssignmentListCreateView,
    V2StaffDetailView,
    V2StaffListCreateView,
)

app_name = 'tailors_v2'

urlpatterns = [
    path('business/', V2BusinessView.as_view(), name='v2-business'),
    path('shops/', V2ShopListCreateView.as_view(), name='v2-shops'),
    path('shops/<int:shop_id>/', V2ShopDetailView.as_view(), name='v2-shop-detail'),
    path(
        'shops/<int:shop_id>/publish-readiness/',
        V2ShopPublishReadinessView.as_view(),
        name='v2-shop-publish-readiness',
    ),
    path(
        'shops/<int:shop_id>/publish/',
        V2ShopPublishView.as_view(),
        name='v2-shop-publish',
    ),
    path('shops/<int:shop_id>/pin/', V2ShopPinView.as_view(), name='v2-shop-pin'),
    path('staff/', V2StaffListCreateView.as_view(), name='v2-staff'),
    path('staff/<int:staff_id>/', V2StaffDetailView.as_view(), name='v2-staff-detail'),
    path(
        'staff/<int:staff_id>/assignments/',
        V2StaffAssignmentListCreateView.as_view(),
        name='v2-staff-assignments',
    ),
    path(
        'staff/<int:staff_id>/assignments/<int:assignment_id>/',
        V2StaffAssignmentDetailView.as_view(),
        name='v2-staff-assignment-detail',
    ),
]
