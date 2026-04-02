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
        from ..models import TailorProfile
        # Check if owner
        profile = TailorProfile.objects.filter(user=user).first()
        if profile:
            return profile
        # Check if employee
        if hasattr(user, 'tailor_employee'):
            return user.tailor_employee.tailor
        return None

class BaseTailorAuthenticatedView(BaseTailorAPIView):
    """Base view that requires tailor or shop staff authentication."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from ..permissions import IsShopStaff
        self.permission_classes = [IsAuthenticated, IsShopStaff]

