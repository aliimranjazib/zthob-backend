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
from zthob.utils import api_response

@extend_schema(
    tags=["Tailor Address"],
    description="Get tailor's single address"
)
class TailorAddressView(APIView):
    """Get tailor's single address."""
    permission_classes = [IsAuthenticated, IsTailor]
    
    def get(self, request):
        """Get the tailor's address."""
        try:
            address = Address.objects.get(user=request.user)
            serializer = TailorAddressSerializer(address)
            return api_response(
                success=True,
                message='Address fetched successfully',
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )
        except Address.DoesNotExist:
            return api_response(
                success=False,
                message='No address found',
                data=None,
                status_code=status.HTTP_404_NOT_FOUND
            )

@extend_schema(
    tags=["Tailor Address"],
    description="Create or update tailor's single address"
)
class TailorAddressCreateUpdateView(APIView):
    """Create or update tailor's single address."""
    permission_classes = [IsAuthenticated, IsTailor]
    
    def post(self, request):
        """Create a new address for the tailor (replaces any existing one)."""
        serializer = TailorAddressCreateSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            address = serializer.save()
            response_serializer = TailorAddressSerializer(address)
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
            address = Address.objects.get(user=request.user)
            serializer = TailorAddressUpdateSerializer(address, data=request.data, partial=True)
            
            if serializer.is_valid():
                updated_address = serializer.save()
                response_serializer = TailorAddressSerializer(updated_address)
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
        except Address.DoesNotExist:
            return api_response(
                success=False,
                message='No address found to update',
                data=None,
                status_code=status.HTTP_404_NOT_FOUND
            )

@extend_schema(
    tags=["Tailor Address"],
    description="Delete tailor's address"
)
class TailorAddressDeleteView(APIView):
    """Delete tailor's address."""
    permission_classes = [IsAuthenticated, IsTailor]
    
    def delete(self, request):
        """Delete the tailor's address."""
        try:
            address = Address.objects.get(user=request.user)
            address.delete()
            return api_response(
                success=True,
                message='Address deleted successfully',
                data=None,
                status_code=status.HTTP_200_OK
            )
        except Address.DoesNotExist:
            return api_response(
                success=False,
                message='No address found to delete',
                data=None,
                status_code=status.HTTP_404_NOT_FOUND
            )
