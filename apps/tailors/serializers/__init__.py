# apps/tailors/serializers/__init__.py
from .profile import (
    TailorProfileSerializer,
    TailorProfileUpdateSerializer,
    TailorProfileSubmissionSerializer
)
from .catalog import (
    FabricSerializer,
    FabricCreateSerializer,
    FabricUpdateSerializer,
    FabricImageSerializer,
    FabricTypeSerializer,
    FabricTypeBasicSerializer,
    FabricCategorySerializer,
    FabricCategoryBasicSerializer,
    FabricTagSerializer,
    FabricTagBasicSerializer
)
from .review import (
    TailorProfileReviewSerializer,
    TailorProfileReviewUpdateSerializer,
    TailorProfileStatusSerializer
)
from .service_areas import (
    ServiceAreaSerializer,
    ServiceAreaBasicSerializer
)
from .address import (
    TailorAddressSerializer,
    TailorAddressCreateSerializer,
    TailorAddressUpdateSerializer
)
from .base import ImageWithMetadataSerializer
from .analytics import (
    TailorAnalyticsSerializer,
    DailyEarningsSerializer,
    WeeklyTrendSerializer,
    AnalyticsPeriodSerializer
)
from .orders import (
    TailorUpdateOrderStatusSerializer
)
from .tailor_pos import (
    TailorCustomerSerializer,
    CreateCustomerSerializer
)

# Export all serializers
__all__ = [
    # Profile serializers
    'TailorProfileSerializer',
    'TailorProfileUpdateSerializer',
    'TailorProfileSubmissionSerializer',
    
    # Catalog serializers
    'FabricSerializer',
    'FabricCreateSerializer',
    'FabricUpdateSerializer',
    'FabricImageSerializer',
    'FabricTypeSerializer',
    'FabricTypeBasicSerializer',
    'FabricCategorySerializer',
    'FabricCategoryBasicSerializer',
    'FabricTagSerializer',
    'FabricTagBasicSerializer',
    
    # Review serializers
    'TailorProfileReviewSerializer',
    'TailorProfileReviewUpdateSerializer',
    'TailorProfileStatusSerializer',
    
    # Service Area serializers
    'ServiceAreaSerializer',
    'ServiceAreaBasicSerializer',
    
    # Address serializers
    'TailorAddressSerializer',
    'TailorAddressCreateSerializer',
    'TailorAddressUpdateSerializer',
    
    # Base serializers
    'ImageWithMetadataSerializer',
    
    # Analytics serializers
    'TailorAnalyticsSerializer',
    'DailyEarningsSerializer',
    'WeeklyTrendSerializer',
    'AnalyticsPeriodSerializer',
    
    # Order serializers
    'TailorUpdateOrderStatusSerializer',
    
    # POS serializers
    'TailorCustomerSerializer',
    'CreateCustomerSerializer',
]
