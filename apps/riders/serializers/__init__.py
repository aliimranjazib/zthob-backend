# Re-export serializers from parent serializers.py file
# Use importlib to load the file directly and avoid circular imports
import importlib.util
import sys
from pathlib import Path

# Get the parent serializers.py file
_parent_dir = Path(__file__).parent.parent
_serializers_py = _parent_dir / 'serializers.py'

# Load it as a module
_spec = importlib.util.spec_from_file_location("riders_serializers_py", _serializers_py)
_module = importlib.util.module_from_spec(_spec)
_module.__package__ = 'apps.riders'
_module.__file__ = str(_serializers_py)

# Temporarily handle the import conflict
_was_in_modules = 'apps.riders.serializers' in sys.modules
_old_module = sys.modules.get('apps.riders.serializers') if _was_in_modules else None

try:
    # Remove from sys.modules temporarily to avoid conflict
    if _was_in_modules:
        del sys.modules['apps.riders.serializers']
    
    # Execute the module
    _spec.loader.exec_module(_module)
    
    # Re-export all serializers
    RiderDocumentSerializer = _module.RiderDocumentSerializer
    RiderRegisterSerializer = _module.RiderRegisterSerializer
    RiderProfileSerializer = _module.RiderProfileSerializer
    RiderProfileUpdateSerializer = _module.RiderProfileUpdateSerializer
    RiderProfileSubmissionSerializer = _module.RiderProfileSubmissionSerializer
    RiderDocumentUploadSerializer = _module.RiderDocumentUploadSerializer
    RiderProfileReviewSerializer = _module.RiderProfileReviewSerializer
    RiderProfileReviewUpdateSerializer = _module.RiderProfileReviewUpdateSerializer
    RiderProfileStatusSerializer = _module.RiderProfileStatusSerializer
    RiderOrderListSerializer = _module.RiderOrderListSerializer
    RiderOrderDetailSerializer = _module.RiderOrderDetailSerializer
    RiderAcceptOrderSerializer = _module.RiderAcceptOrderSerializer
    RiderAddMeasurementsSerializer = _module.RiderAddMeasurementsSerializer
    RiderUpdateOrderStatusSerializer = _module.RiderUpdateOrderStatusSerializer
finally:
    # Restore if needed
    if _old_module:
        sys.modules['apps.riders.serializers'] = _old_module

__all__ = [
    'RiderDocumentSerializer',
    'RiderRegisterSerializer',
    'RiderProfileSerializer',
    'RiderProfileUpdateSerializer',
    'RiderProfileSubmissionSerializer',
    'RiderDocumentUploadSerializer',
    'RiderProfileReviewSerializer',
    'RiderProfileReviewUpdateSerializer',
    'RiderProfileStatusSerializer',
    'RiderOrderListSerializer',
    'RiderOrderDetailSerializer',
    'RiderAcceptOrderSerializer',
    'RiderAddMeasurementsSerializer',
    'RiderUpdateOrderStatusSerializer',
]
