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
        """Helper method to get tailor profile."""
        from ..models import TailorProfile
        try:
            return TailorProfile.objects.get(user=user)
        except TailorProfile.DoesNotExist:
            return None

class BaseTailorAuthenticatedView(BaseTailorAPIView):
    """Base view that requires tailor authentication."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from ..permissions import IsTailor
        self.permission_classes = [IsAuthenticated, IsTailor]
