from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from apps.tailors.permissions import IsTailor
from zthob.utils import api_response
from . import models
from .serializers import (
    TailorInvitationCodeSerializer,
    CreateInvitationCodeSerializer,
    TailorRiderAssociationSerializer,
)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated, IsTailor])
def tailor_invitation_codes(request):
    """
    GET: List all invitation codes for the tailor
    POST: Create a new invitation code
    """
    if request.method == 'GET':
        codes = models.TailorInvitationCode.objects.filter(
            tailor=request.user
        ).order_by('-created_at')
        
        serializer = TailorInvitationCodeSerializer(codes, many=True)
        return api_response(
            success=True,
            message="Invitation codes retrieved successfully",
            data={'codes': serializer.data},
            status_code=status.HTTP_200_OK,
            request=request
        )
    
    elif request.method == 'POST':
        serializer = CreateInvitationCodeSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            invitation_code = serializer.save()
            response_serializer = TailorInvitationCodeSerializer(invitation_code)
            return api_response(
                success=True,
                message="Invitation code created successfully",
                data=response_serializer.data,
                status_code=status.HTTP_201_CREATED,
                request=request
            )
        
        return api_response(
            success=False,
            message="Invalid data",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST,
            request=request
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsTailor])
def deactivate_invitation_code(request, code):
    """Deactivate an invitation code"""
    invitation_code = get_object_or_404(
        models.TailorInvitationCode,
        code=code.upper(),
        tailor=request.user
    )
    
    invitation_code.is_active = False
    invitation_code.save()
    
    return api_response(
        success=True,
        message="Invitation code deactivated successfully",
        status_code=status.HTTP_200_OK,
        request=request
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsTailor])
def tailor_my_riders(request):
    """Get list of riders associated with this tailor"""
    associations = models.TailorRiderAssociation.objects.filter(
        tailor=request.user,
        is_active=True
    ).select_related(
        'rider',
        'rider__rider_profile',
        'joined_via_code'
    ).order_by('-priority', '-created_at')
    
    # Build response with rider info and statistics
    riders_data = []
    for assoc in associations:
        serializer = TailorRiderAssociationSerializer(assoc)
        rider_profile = getattr(assoc.rider, 'rider_profile', None)
        rider_data = {
            'id': assoc.rider.id,
            'full_name': getattr(rider_profile, 'full_name', assoc.rider.username),
            'phone_number': getattr(rider_profile, 'phone_number', getattr(assoc.rider, 'phone', '')),
            'vehicle_type': getattr(rider_profile, 'vehicle_type', ''),
            'rating': float(getattr(rider_profile, 'rating', 0.0)),
            'is_available': getattr(rider_profile, 'is_available', False),
            'joined_at': assoc.created_at,
            'statistics': serializer.data['statistics']
        }
        riders_data.append(rider_data)
    
    return api_response(
        success=True,
        message="Riders retrieved successfully",
        data={'riders': riders_data},
        status_code=status.HTTP_200_OK,
        request=request
    )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsTailor])
def remove_rider_from_team(request, rider_id):
    """Remove a rider from tailor's team (deactivate association)"""
    association = get_object_or_404(
        models.TailorRiderAssociation,
        tailor=request.user,
        rider_id=rider_id
    )
    
    association.is_active = False
    association.save()
    
    return api_response(
        success=True,
        message="Rider removed from your team successfully",
        status_code=status.HTTP_200_OK,
        request=request
    )
