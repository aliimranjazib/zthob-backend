# apps/tailors/views/address.py
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from drf_spectacular.utils import extend_schema
from django.shortcuts import get_object_or_404

from apps.customers.models import Address
from ..serializers.address import (
    TailorAddressSerializer, 
    TailorAddressCreateSerializer, 
    TailorAddressUpdateSerializer,
    TailorAddressResponseSerializer
)
from ..permissions import IsShopStaff
from .base import BaseTailorAPIView
from zthob.utils import api_response

@extend_schema(
    tags=["Tailor Address"],
    description="Get tailor's single address"
)
class TailorAddressView(BaseTailorAPIView):
    """Get tailor's single address."""
    permission_classes = [IsAuthenticated, IsShopStaff]
    
    def get(self, request):
        """Get the tailor's address."""
        try:
            target_user = self.get_tailor_owner_user(request.user)
            if not target_user:
                return api_response(
                    success=False,
                    message='Tailor profile not found',
                    data=None,
                    status_code=status.HTTP_404_NOT_FOUND
                )
            # First try to get the default address
            address = Address.objects.filter(user=target_user, is_default=True).first()
            
            # If no default address, get the first address
            if not address:
                address = Address.objects.filter(user=target_user).first()
            
            if address:
                serializer = TailorAddressResponseSerializer(address)
                return api_response(
                    success=True,
                    message='Address fetched successfully',
                    data=serializer.data,
                    status_code=status.HTTP_200_OK
                )
            else:
                return api_response(
                    success=False,
                    message='No address found',
                    data=None,
                    status_code=status.HTTP_404_NOT_FOUND
                )
        except Exception as e:
            return api_response(
                success=False,
                message=f'Error fetching address: {str(e)}',
                data=None,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

@extend_schema(
    tags=["Tailor Address"],
    description="Create or update tailor's single address"
)
class TailorAddressCreateUpdateView(BaseTailorAPIView):
    """Create or update tailor's single address."""
    permission_classes = [IsAuthenticated, IsShopStaff]
    
    def post(self, request):
        """Create a new address for the tailor (replaces any existing one)."""
        if hasattr(request.user, 'tailor_employee') and not self.employee_has_permission(request.user, 'can_manage_shop_address'):
            return api_response(
                success=False,
                message='Permission denied',
                errors=None,
                status_code=status.HTTP_403_FORBIDDEN
            )
        target_user = self.get_tailor_owner_user(request.user)
        if not target_user:
            return api_response(
                success=False,
                message='Tailor profile not found',
                data=None,
                status_code=status.HTTP_404_NOT_FOUND
            )
        serializer = TailorAddressCreateSerializer(
            data=request.data,
            context={'request': request, 'target_user': target_user}
        )
        
        if serializer.is_valid():
            address = serializer.save()
            response_serializer = TailorAddressResponseSerializer(address)
            return api_response(
                success=True,
                message='Address created successfully',
                data=response_serializer.data,
                status_code=status.HTTP_201_CREATED
            )
        
        return api_response(
            success=False,
            message='Address creation failed',
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    def put(self, request):
        """Update the tailor's existing address."""
        try:
            if hasattr(request.user, 'tailor_employee') and not self.employee_has_permission(request.user, 'can_manage_shop_address'):
                return api_response(
                    success=False,
                    message='Permission denied',
                    errors=None,
                    status_code=status.HTTP_403_FORBIDDEN
                )
            target_user = self.get_tailor_owner_user(request.user)
            if not target_user:
                return api_response(
                    success=False,
                    message='Tailor profile not found',
                    data=None,
                    status_code=status.HTTP_404_NOT_FOUND
                )
            # First try to get the default address
            address = Address.objects.filter(user=target_user, is_default=True).first()
            
            # If no default address, get the first address
            if not address:
                address = Address.objects.filter(user=target_user).first()
            
            if address:
                serializer = TailorAddressUpdateSerializer(address, data=request.data, partial=True)
                
                if serializer.is_valid():
                    updated_address = serializer.save()
                    response_serializer = TailorAddressResponseSerializer(updated_address)
                    return api_response(
                        success=True,
                        message='Address updated successfully',
                        data=response_serializer.data,
                        status_code=status.HTTP_200_OK
                    )
                
                return api_response(
                    success=False,
                    message='Address update failed',
                    errors=serializer.errors,
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            else:
                return api_response(
                    success=False,
                    message='No address found to update',
                    data=None,
                    status_code=status.HTTP_404_NOT_FOUND
                )
        except Exception as e:
            return api_response(
                success=False,
                message=f'Error updating address: {str(e)}',
                data=None,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

@extend_schema(
    tags=["Tailor Address"],
    description="Delete tailor's address"
)
class TailorAddressDeleteView(BaseTailorAPIView):
    """Delete tailor's address."""
    permission_classes = [IsAuthenticated, IsShopStaff]
    
    def delete(self, request):
        """Delete the tailor's address."""
        try:
            if hasattr(request.user, 'tailor_employee') and not self.employee_has_permission(request.user, 'can_manage_shop_address'):
                return api_response(
                    success=False,
                    message='Permission denied',
                    data=None,
                    status_code=status.HTTP_403_FORBIDDEN
                )
            target_user = self.get_tailor_owner_user(request.user)
            if not target_user:
                return api_response(
                    success=False,
                    message='Tailor profile not found',
                    data=None,
                    status_code=status.HTTP_404_NOT_FOUND
                )
            # Delete all addresses for this user
            addresses = Address.objects.filter(user=target_user)
            deleted_count = addresses.count()
            
            if deleted_count > 0:
                addresses.delete()
                return api_response(
                    success=True,
                    message=f'Address deleted successfully ({deleted_count} address(es) removed)',
                    data=None,
                    status_code=status.HTTP_200_OK
                )
            else:
                return api_response(
                    success=False,
                    message='No address found to delete',
                    data=None,
                    status_code=status.HTTP_404_NOT_FOUND
                )
        except Exception as e:
            return api_response(
                success=False,
                message=f'Error deleting address: {str(e)}',
                data=None,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
