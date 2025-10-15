# apps/tailors/views/service_areas.py
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser,AllowAny
from rest_framework import generics
from drf_spectacular.utils import extend_schema
from zthob.utils import api_response
from rest_framework import status

from ..models import ServiceArea
from ..serializers import (
    ServiceAreaSerializer,
    ServiceAreaBasicSerializer
)
from .base import BaseTailorAuthenticatedView

# =============================================================================
# SERVICE AREA VIEWS
# =============================================================================

@extend_schema(
    tags=["Service Areas"],
    description="Get all service areas available for delivery calculation"
)
class AvailableServiceAreasView(APIView):
    """Get all active service areas for delivery calculation."""
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Get all active service areas."""
        service_areas = ServiceArea.objects.filter(is_active=True).order_by('city', 'name')
        serializer = ServiceAreaBasicSerializer(service_areas, many=True)
        
        return api_response(
            success=True,
            message="Available service areas retrieved",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )

# =============================================================================
# ADMIN SERVICE AREA VIEWS
# =============================================================================

@extend_schema(
    tags=["Admin - Service Areas"],
    description="Admin management of service areas"
)
class AdminServiceAreasView(APIView):
    """Admin view for managing all service areas."""
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        """Get all service areas."""
        service_areas = ServiceArea.objects.all().order_by('city', 'name')
        serializer = ServiceAreaSerializer(service_areas, many=True)
        
        return api_response(
            success=True,
            message="Service areas retrieved",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )
    
    def post(self, request):
        """Create a new service area."""
        serializer = ServiceAreaSerializer(data=request.data)
        
        if serializer.is_valid():
            service_area = serializer.save()
            return api_response(
                success=True,
                message="Service area created successfully",
                data=serializer.data,
                status_code=status.HTTP_201_CREATED
            )
        
        return api_response(
            success=False,
            message="Validation failed",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )

@extend_schema(
    tags=["Admin - Service Areas"],
    description="Admin management of individual service areas"
)
class AdminServiceAreaDetailView(APIView):
    """Admin view for managing individual service areas."""
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get_object(self, pk):
        """Get service area by ID."""
        try:
            return ServiceArea.objects.get(pk=pk)
        except ServiceArea.DoesNotExist:
            return None
    
    def get(self, request, pk):
        """Get service area details."""
        service_area = self.get_object(pk)
        if not service_area:
            return api_response(
                success=False,
                message="Service area not found",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        serializer = ServiceAreaSerializer(service_area)
        return api_response(
            success=True,
            message="Service area details retrieved",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )
    
    def put(self, request, pk):
        """Update service area."""
        service_area = self.get_object(pk)
        if not service_area:
            return api_response(
                success=False,
                message="Service area not found",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        serializer = ServiceAreaSerializer(service_area, data=request.data, partial=True)
        
        if serializer.is_valid():
            updated_service_area = serializer.save()
            response_serializer = ServiceAreaSerializer(updated_service_area)
            
            return api_response(
                success=True,
                message="Service area updated successfully",
                data=response_serializer.data,
                status_code=status.HTTP_200_OK
            )
        
        return api_response(
            success=False,
            message="Validation failed",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    def delete(self, request, pk):
        """Delete service area."""
        service_area = self.get_object(pk)
        if not service_area:
            return api_response(
                success=False,
                message="Service area not found",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        
        service_area_name = service_area.name
        service_area.delete()
        
        return api_response(
            success=True,
            message=f"Service area '{service_area_name}' deleted successfully",
            status_code=status.HTTP_200_OK
        )
