# apps/tailors/views/__init__.py
from .profile import (
    TailorProfileView,
    TailorMeasurementFeeView,
    TailorProfileSubmissionView,
    TailorProfileStatusView,
    TailorShopStatusView
)
from .catalog import (
    TailorFabricTypeListCreateView,
    TailorFabricTypeRetrieveUpdateDestroyView,
    TailorFabricTagsListCreateView,
    TailorFabricTagsRetrieveUpdateDestroyView,
    TailorFabricCategoryListCreateView,
    TailorFabricCategoryDetailView,
    TailorFabricCountryListView,
    AdminFabricCountryListCreateView,
    AdminFabricCountryDetailView,
    TailorFabricView,
    TailorFabricDetailView,
    FabricImagePrimaryView,
    FabricImageDeleteView,
    FabricImageAddView,
    FabricImageUpdateView
)
from .review import (
    TailorProfileReviewListView,
    TailorProfileReviewDetailView
)
from .service_areas import (
    AvailableServiceAreasView,
    AdminServiceAreasView,
    AdminServiceAreaDetailView
)
from .address import (
    TailorAddressView,
    TailorAddressCreateUpdateView,
    TailorAddressDeleteView
)
from .analytics import (
    TailorAnalyticsView
)
from .orders import (
    TailorAcceptOrderView,
    TailorUpdateOrderStatusView,
    TailorAddMeasurementsView
)
from .order_download import TailorOrderDownloadPDFView
from .config import TailorConfigView
from .tailor_pos import (
    TailorCustomerListView,
    TailorCreateCustomerView,
    TailorPOSCustomerOrdersView,
    TailorPOSCustomerOrderDetailView
)
from .pos_family import (
    TailorPOSFamilyMemberListCreateView,
    TailorPOSFamilyMemberDetailView,
)
from .rating import (
    SubmitTailorRatingView,
    TailorRatingListView
)
from .home import TailorHomeAPIView
from .employee import (
    TailorEmployeeListCreateView,
    TailorEmployeeDetailView,
)

# Export all views
__all__ = [
    # Home/Dashboard
    'TailorHomeAPIView',
    
    # Profile views
    'TailorProfileView',
    'TailorMeasurementFeeView',
    'TailorProfileSubmissionView',
    'TailorProfileStatusView',
    'TailorShopStatusView',
    
    # Catalog views
    'TailorFabricTypeListCreateView',
    'TailorFabricTypeRetrieveUpdateDestroyView',
    'TailorFabricTagsListCreateView',
    'TailorFabricTagsRetrieveUpdateDestroyView',
    'TailorFabricCategoryListCreateView',
    'TailorFabricCategoryDetailView',
    'TailorFabricCountryListView',
    'AdminFabricCountryListCreateView',
    'AdminFabricCountryDetailView',
    'TailorFabricView',
    'TailorFabricDetailView',
    'FabricImagePrimaryView',
    'FabricImageDeleteView',
    'FabricImageAddView',
    'FabricImageUpdateView',
    
    # Review views
    'TailorProfileReviewListView',
    'TailorProfileReviewDetailView',
    
    # Service Area views
    'AvailableServiceAreasView',
    'AdminServiceAreasView',
    'AdminServiceAreaDetailView',
    
    # Address views
    'TailorAddressView',
    'TailorAddressCreateUpdateView',
    'TailorAddressDeleteView',
    
    # Analytics views
    'TailorAnalyticsView',
    
    'TailorAcceptOrderView',
    'TailorUpdateOrderStatusView',
    'TailorAddMeasurementsView',
    'TailorOrderDownloadPDFView',
    'TailorConfigView',
    
    # POS views
    'TailorCustomerListView',
    'TailorCreateCustomerView',
    'TailorPOSCustomerOrdersView',
    'TailorPOSCustomerOrderDetailView',
    'TailorPOSFamilyMemberListCreateView',
    'TailorPOSFamilyMemberDetailView',

    # Rating views
    'SubmitTailorRatingView',
    'TailorRatingListView',

    # Employee views
    'TailorEmployeeListCreateView',
    'TailorEmployeeDetailView',
]
