from .shops import (
    OwnerShopDetailView,
    OwnerShopListCreateView,
    OwnerShopPinView,
)
from .staff import (
    OwnerStaffAssignmentDetailView,
    OwnerStaffAssignmentListCreateView,
    OwnerStaffDetailView,
    OwnerStaffListCreateView,
)
from .orders import (
    OwnerOrderDetailView,
    OwnerOrderListView,
    OwnerReportsView,
)

__all__ = [
    'OwnerShopListCreateView',
    'OwnerShopDetailView',
    'OwnerShopPinView',
    'OwnerStaffListCreateView',
    'OwnerStaffDetailView',
    'OwnerStaffAssignmentListCreateView',
    'OwnerStaffAssignmentDetailView',
    'OwnerOrderListView',
    'OwnerOrderDetailView',
    'OwnerReportsView',
]
