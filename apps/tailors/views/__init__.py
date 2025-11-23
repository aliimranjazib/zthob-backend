# apps/tailors/views/__init__.py
from .profile import (
    TailorProfileView,
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
    TailorFabricView,
    TailorFabricDetailView,
    FabricImagePrimaryView,
    FabricImageDeleteView
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

# Export all views
__all__ = [
    # Profile views
    'TailorProfileView',
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
    'TailorFabricView',
    'TailorFabricDetailView',
    'FabricImagePrimaryView',
    'FabricImageDeleteView',
    
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
]
