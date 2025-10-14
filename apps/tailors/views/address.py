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
    TailorAddressUpdateSerializer
)
from ..permissions import IsTailor
from .base import BaseTailorAuthenticatedView
from zthob.utils import api_response

@extend_schema(
    tags=["Tailor Address"],
    description="Tailor address management operations"
)
class TailorAddressListView(BaseTailorAuthenticatedView):
    """List and create tailor addresses."""
    
    def get(self, request):
        """Get all addresses for the current tailor."""
        addresses = Address.objects.filter(user=request.user).order_by('-is_default', '-created_at')
        serializer = TailorAddressSerializer(addresses, many=True, context={'request': request})
        
        return api_response(
            success=True,
            message='Tailor addresses fetched successfully',
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )
    
    def post(self, request):
        """Create a new address for the tailor."""
        serializer = TailorAddressCreateSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            address = serializer.save()
            response_serializer = TailorAddressSerializer(address, context={'request': request})
            
            return api_response(
                success=True,
                message='Address created successfully',
                data=response_serializer.data,
                status_code=status.HTTP_201_CREATED
            )
        
        return api_response(
            success=False,
            message='Validation failed',
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )

@extend_schema(
    tags=["Tailor Address"],
    description="Tailor address detail operations"
)
class TailorAddressDetailView(BaseTailorAuthenticatedView):
    """Retrieve, update, and delete tailor addresses."""
    
    def get(self, request, pk):
        """Get a specific address."""
        address = get_object_or_404(Address, pk=pk, user=request.user)
        serializer = TailorAddressSerializer(address, context={'request': request})
        
        return api_response(
            success=True,
            message='Address fetched successfully',
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )
    
    def put(self, request, pk):
        """Update an address."""
        address = get_object_or_404(Address, pk=pk, user=request.user)
        serializer = TailorAddressUpdateSerializer(address, data=request.data, partial=True)
        
        if serializer.is_valid():
            updated_address = serializer.save()
            response_serializer = TailorAddressSerializer(updated_address, context={'request': request})
            
            return api_response(
                success=True,
                message='Address updated successfully',
                data=response_serializer.data,
                status_code=status.HTTP_200_OK
            )
        
        return api_response(
            success=False,
            message='Validation failed',
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    def delete(self, request, pk):
        """Delete an address."""
        address = get_object_or_404(Address, pk=pk, user=request.user)
        address.delete()
        
        return api_response(
            success=True,
            message='Address deleted successfully',
            data=None,
            status_code=status.HTTP_200_OK
        )

@extend_schema(
    tags=["Tailor Address"],
    description="Set default address for tailor"
)
class TailorAddressSetDefaultView(BaseTailorAuthenticatedView):
    """Set an address as default for the tailor."""
    
    def post(self, request, pk):
        """Set an address as default."""
        address = get_object_or_404(Address, pk=pk, user=request.user)
        
        # Unset other default addresses
        Address.objects.filter(user=request.user, is_default=True).update(is_default=False)
        
        # Set this address as default
        address.is_default = True
        address.save()
        
        serializer = TailorAddressSerializer(address, context={'request': request})
        
        return api_response(
            success=True,
            message='Default address set successfully',
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )
