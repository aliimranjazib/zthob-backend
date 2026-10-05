from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from apps.finance.shop_session import finance_shop_required_message
from apps.tailors.permissions import IsShopStaff
from apps.riders.services.shop_riders import (
    require_rider_session_shop,
    resolve_tailor_user_for_rider_api,
)
from zthob.utils import api_response
from . import models
from .serializers import (
    TailorInvitationCodeSerializer,
    CreateInvitationCodeSerializer,
    TailorRiderAssociationSerializer,
    TailorRiderAssociationUpdateSerializer,
)


def _session_shop_or_error(request):
    try:
        shop, _shop_id = require_rider_session_shop(request)
        return shop, None
    except ValidationError as exc:
        detail = exc.detail
        if isinstance(detail, list):
            message = str(detail[0])
        elif isinstance(detail, dict):
            first = next(iter(detail.values()))
            message = str(first[0] if isinstance(first, list) else first)
        else:
            message = str(detail)
        return None, api_response(
            success=False,
            message=message or finance_shop_required_message(),
            status_code=status.HTTP_400_BAD_REQUEST,
            request=request,
        )


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated, IsShopStaff])
def tailor_invitation_codes(request):
    """
    GET: List all invitation codes for the tailor
    POST: Create a new invitation code
    """
    shop, error_response = _session_shop_or_error(request)
    if error_response:
        return error_response

    tailor_user = resolve_tailor_user_for_rider_api(request)
    if not tailor_user:
        return api_response(
            success=False,
            message="Tailor shop not found",
            status_code=status.HTTP_404_NOT_FOUND,
            request=request,
        )

    if request.method == 'GET':
        codes = models.TailorInvitationCode.objects.filter(
            shop=shop,
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
            context={'request': request, 'shop': shop},
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
@permission_classes([IsAuthenticated, IsShopStaff])
def deactivate_invitation_code(request, code):
    """Deactivate an invitation code"""
    shop, error_response = _session_shop_or_error(request)
    if error_response:
        return error_response

    invitation_code = get_object_or_404(
        models.TailorInvitationCode,
        code=code.upper(),
        shop=shop,
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
@permission_classes([IsAuthenticated, IsShopStaff])
def tailor_my_riders(request):
    """Get list of riders associated with this tailor shop session"""
    shop, error_response = _session_shop_or_error(request)
    if error_response:
        return error_response

    associations = models.TailorRiderAssociation.objects.filter(
        shop=shop,
        is_active=True,
    ).select_related(
        'rider',
        'rider__rider_profile',
        'joined_via_code'
    ).order_by('-priority', '-created_at')

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
            'can_take_measurements': assoc.can_take_measurements,
            'can_do_delivery': assoc.can_do_delivery,
            'rider_types': serializer.data['rider_types'],
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


@api_view(['PATCH', 'DELETE'])
@permission_classes([IsAuthenticated, IsShopStaff])
def remove_rider_from_team(request, rider_id):
    """Update or remove a rider from tailor's team"""
    shop, error_response = _session_shop_or_error(request)
    if error_response:
        return error_response

    association = get_object_or_404(
        models.TailorRiderAssociation,
        shop=shop,
        rider_id=rider_id,
    )

    if request.method == 'PATCH':
        serializer = TailorRiderAssociationUpdateSerializer(
            association,
            data=request.data,
            partial=True,
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                success=True,
                message="Rider settings updated successfully",
                data=TailorRiderAssociationSerializer(association).data,
                status_code=status.HTTP_200_OK,
                request=request
            )

        return api_response(
            success=False,
            message="Invalid data",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST,
            request=request
        )

    association.is_active = False
    association.save(update_fields=['is_active', 'updated_at'])

    return api_response(
        success=True,
        message="Rider removed from your team successfully",
        status_code=status.HTTP_200_OK,
        request=request
    )
