# apps/tailors/views/service_areas.py
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser,AllowAny
from rest_framework import generics
from drf_spectacular.utils import extend_schema
from zthob.utils import api_response
from rest_framework import status

from ..models import ServiceArea, TailorServiceArea, TailorProfile
from ..serializers import (
    ServiceAreaSerializer,
    ServiceAreaBasicSerializer,
    TailorServiceAreaSerializer,
    TailorServiceAreaCreateSerializer,
    ServiceAreaWithTailorCountSerializer
)
from .base import BaseTailorAuthenticatedView

# =============================================================================
# TAILOR SERVICE AREA VIEWS
# =============================================================================

@extend_schema(
    tags=["Tailor Service Areas"],
    description="Get all service areas available for selection"
)
class AvailableServiceAreasView(APIView):
    """Get all active service areas for tailors to choose from."""
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

@extend_schema(
    tags=["Tailor Service Areas"],
    description="Manage tailor's service areas"
)
class TailorServiceAreasView(BaseTailorAuthenticatedView):
    """Manage tailor's service areas."""
    
    def get(self, request):
        """Get all service areas for the authenticated tailor."""
        try:
            tailor_profile = TailorProfile.objects.get(user=request.user)
        except TailorProfile.DoesNotExist:
            return api_response(
                success=False,
                message="Tailor profile not found",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        service_areas = TailorServiceArea.objects.filter(
            tailor=tailor_profile
        ).select_related('service_area').order_by('-is_primary', 'service_area__city', 'service_area__name')
        
        serializer = TailorServiceAreaSerializer(service_areas, many=True)
        
        return api_response(
            success=True,
            message="Tailor service areas retrieved",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )
    
    def post(self, request):
        """Add a new service area for the tailor."""
        try:
            tailor_profile = TailorProfile.objects.get(user=request.user)
        except TailorProfile.DoesNotExist:
            return api_response(
                success=False,
                message="Tailor profile not found",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        serializer = TailorServiceAreaCreateSerializer(
            data=request.data,
            context={'tailor': tailor_profile}
        )
        
        if serializer.is_valid():
            # Check if service area already exists for this tailor
            service_area = serializer.validated_data['service_area']
            if TailorServiceArea.objects.filter(
                tailor=tailor_profile, 
                service_area=service_area
            ).exists():
                return api_response(
                    success=False,
                    message="Service area already added",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            tailor_service_area = serializer.save(tailor=tailor_profile)
            response_serializer = TailorServiceAreaSerializer(tailor_service_area)
            
            return api_response(
                success=True,
                message="Service area added successfully",
                data=response_serializer.data,
                status_code=status.HTTP_201_CREATED
            )
        
        return api_response(
            success=False,
            message="Validation failed",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )

@extend_schema(
    tags=["Tailor Service Areas"],
    description="Update or delete a specific service area"
)
class TailorServiceAreaDetailView(BaseTailorAuthenticatedView):
    """Update or delete a specific service area for the tailor."""
    
    def get_object(self, pk, user):
        """Get tailor service area that belongs to the authenticated tailor."""
        try:
            tailor_profile = TailorProfile.objects.get(user=user)
            return TailorServiceArea.objects.get(
                pk=pk, 
                tailor=tailor_profile
            )
        except (TailorProfile.DoesNotExist, TailorServiceArea.DoesNotExist):
            return None
    
    def get(self, request, pk):
        """Get specific service area details."""
        tailor_service_area = self.get_object(pk, request.user)
        if not tailor_service_area:
            return api_response(
                success=False,
                message="Service area not found",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        serializer = TailorServiceAreaSerializer(tailor_service_area)
        return api_response(
            success=True,
            message="Service area details retrieved",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )
    
    def put(self, request, pk):
        """Update service area details."""
        tailor_service_area = self.get_object(pk, request.user)
        if not tailor_service_area:
            return api_response(
                success=False,
                message="Service area not found",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        serializer = TailorServiceAreaCreateSerializer(
            tailor_service_area,
            data=request.data,
            partial=True,
            context={'tailor': tailor_service_area.tailor}
        )
        
        if serializer.is_valid():
            updated_service_area = serializer.save()
            response_serializer = TailorServiceAreaSerializer(updated_service_area)
            
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
        """Remove service area from tailor."""
        tailor_service_area = self.get_object(pk, request.user)
        if not tailor_service_area:
            return api_response(
                success=False,
                message="Service area not found",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        service_area_name = tailor_service_area.service_area.name
        tailor_service_area.delete()
        
        return api_response(
            success=True,
            message=f"Service area '{service_area_name}' removed successfully",
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
        """Get all service areas with tailor counts."""
        service_areas = ServiceArea.objects.all().order_by('city', 'name')
        serializer = ServiceAreaWithTailorCountSerializer(service_areas, many=True)
        
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
        
        serializer = ServiceAreaWithTailorCountSerializer(service_area)
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
            response_serializer = ServiceAreaWithTailorCountSerializer(updated_service_area)
            
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
        
        # Check if any tailors are using this service area
        if service_area.tailors.exists():
            return api_response(
                success=False,
                message="Cannot delete service area. Some tailors are still using it.",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        service_area_name = service_area.name
        service_area.delete()
        
        return api_response(
            success=True,
            message=f"Service area '{service_area_name}' deleted successfully",
            status_code=status.HTTP_200_OK
        )
