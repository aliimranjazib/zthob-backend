from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from zthob.utils import api_response
from .permissions import IsRider
from . import models
from .serializers import JoinTailorTeamSerializer
from .services.shop_riders import build_rider_team_shop_payload


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
        created = result['created']

        tailor_info = build_rider_team_shop_payload(association, include_roles=False)

        message = (
            'Successfully joined tailor\'s team'
            if created
            else 'You are already part of this tailor\'s team'
        )

        return api_response(
            success=True,
            message=message,
            data={'tailor': tailor_info},
            status_code=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
            request=request
        )

    return api_response(
        success=False,
        message="Invalid invitation code",
        errors=serializer.errors,
        status_code=status.HTTP_400_BAD_REQUEST,
        request=request
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsRider])
def rider_my_tailors(request):
    """Get list of tailor shops this rider is associated with"""
    associations = (
        models.TailorRiderAssociation.objects.filter(
            rider=request.user,
            is_active=True,
        )
        .select_related('shop', 'tailor', 'tailor__tailor_profile')
        .order_by('-created_at')
    )

    tailors_data = [
        build_rider_team_shop_payload(assoc, include_roles=True)
        for assoc in associations
    ]

    return api_response(
        success=True,
        message="Tailors retrieved successfully",
        data={'tailors': tailors_data},
        status_code=status.HTTP_200_OK,
        request=request
    )
