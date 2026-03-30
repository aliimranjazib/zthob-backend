# apps/tailors/models/__init__.py
from .profile import TailorProfile
from .catalog import (
    Fabric, 
    FabricType, 
    FabricCategory, 
    FabricTag, 
    FabricImage
)
from .review import TailorProfileReview
from .service_areas import ServiceArea
from .rating import TailorRating
from .employee import TailorEmployee

__all__ = [
    'TailorProfile',
    'Fabric', 
    'FabricType', 
    'FabricCategory', 
    'FabricTag', 
    'FabricImage',
    'TailorProfileReview',
    'ServiceArea',
    'TailorRating',
    'TailorEmployee',
]