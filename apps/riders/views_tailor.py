from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from apps.tailors.permissions import IsTailor
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
        return Response({'codes': serializer.data})
    
    elif request.method == 'POST':
        serializer = CreateInvitationCodeSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            invitation_code = serializer.save()
            response_serializer = TailorInvitationCodeSerializer(invitation_code)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
    
    return Response({
        'message': 'Invitation code deactivated successfully'
    })


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
        rider_data = {
            'id': assoc.rider.id,
            'full_name': assoc.rider.rider_profile.full_name if hasattr(assoc.rider, 'rider_profile') else assoc.rider.username,
            'phone_number': assoc.rider.rider_profile.phone_number if hasattr(assoc.rider, 'rider_profile') else '',
            'vehicle_type': assoc.rider.rider_profile.vehicle_type if hasattr(assoc.rider, 'rider_profile') else '',
            'rating': float(assoc.rider.rider_profile.rating) if hasattr(assoc.rider, 'rider_profile') else 0.0,
            'is_available': assoc.rider.rider_profile.is_available if hasattr(assoc.rider, 'rider_profile') else False,
            'joined_at': assoc.created_at,
            'statistics': serializer.data['statistics']
        }
        riders_data.append(rider_data)
    
    return Response({'riders': riders_data})


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
    
    return Response({
        'message': 'Rider removed from your team successfully'
    })
