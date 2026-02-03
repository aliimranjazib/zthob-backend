from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .permissions import IsRider
from . import models
from .serializers import (
    JoinTailorTeamSerializer,
    TailorBasicInfoSerializer,
)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsRider])
def join_tailor_team(request):
    """Rider joins a tailor's team using invitation code"""
    serializer = JoinTailorTeamSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if serializer.is_valid():
        result = serializer.save()
        
        association = result['association']
        tailor = result['tailor']
        created = result['created']
        
        # Get tailor info
        tailor_info = {
            'id': tailor.id,
            'shop_name': tailor.tailor_profile.shop_name if hasattr(tailor, 'tailor_profile') else tailor.username,
            'phone': tailor.tailor_profile.phone_number if hasattr(tailor, 'tailor_profile') else '',
        }
        
        message = 'Successfully joined tailor\'s team' if created else 'You are already part of this tailor\'s team'
        
        return Response({
            'message': message,
            'tailor': tailor_info
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsRider])
def rider_my_tailors(request):
    """Get list of tailors this rider is associated with"""
    associations = models.TailorRiderAssociation.objects.filter(
        rider=request.user,
        is_active=True
    ).select_related('tailor', 'tailor__tailor_profile').order_by('-created_at')
    
    tailors_data = []
    for assoc in associations:
        tailor_data = {
            'id': assoc.tailor.id,
            'shop_name': assoc.tailor.tailor_profile.shop_name if hasattr(assoc.tailor, 'tailor_profile') else assoc.tailor.username,
            'phone': assoc.tailor.tailor_profile.phone_number if hasattr(assoc.tailor, 'tailor_profile') else '',
            'joined_at': assoc.created_at
        }
        tailors_data.append(tailor_data)
    
    return Response({'tailors': tailors_data})
