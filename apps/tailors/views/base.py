# apps/tailors/views/base.py
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from drf_spectacular.utils import extend_schema
from zthob.utils import api_response
from rest_framework import status

class BaseTailorAPIView(APIView):
    """Base API view for tailor-related operations."""
    permission_classes = [IsAuthenticated]
    
    def get_tailor_profile(self, user):
        """Helper method to get tailor profile (handles owners and employees)."""
        from ..shop_access import get_tailor_profile
        return get_tailor_profile(user)

    def get_tailor_owner_user(self, user):
        """Return the owner user for the resolved tailor shop."""
        profile = self.get_tailor_profile(user)
        return profile.user if profile else None

    def employee_has_permission(self, user, permission_key):
        """Return True when the active employee has the requested permission."""
        if hasattr(user, 'tailor_employee') and user.tailor_employee.is_active:
            return getattr(user.tailor_employee, permission_key, False)
        return False

class BaseTailorAuthenticatedView(BaseTailorAPIView):
    """Base view that requires tailor or shop staff authentication."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from ..permissions import IsShopStaff
        self.permission_classes = [IsAuthenticated, IsShopStaff]
