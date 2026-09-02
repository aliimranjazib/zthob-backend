# apps/tailors/models/__init__.py
from .profile import TailorProfile
from .catalog import (
    Fabric,
    FabricType,
    FabricCategory,
    FabricTag,
    FabricImage,
    FabricCountry,
)
from .review import TailorProfileReview
from .service_areas import ServiceArea
from .rating import TailorRating
from .employee import TailorEmployee
from .staff import TailorStaffMember, ShopStaffAssignment, STAFF_PERMISSION_KEYS

__all__ = [
    'TailorProfile',
    'Fabric', 
    'FabricType', 
    'FabricCategory', 
    'FabricTag', 
    'FabricImage',
    'FabricCountry',
    'TailorProfileReview',
    'ServiceArea',
    'TailorRating',
    'TailorEmployee',
    'TailorStaffMember',
    'ShopStaffAssignment',
    'STAFF_PERMISSION_KEYS',
]
