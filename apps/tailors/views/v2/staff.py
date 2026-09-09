"""V2 staff endpoints."""

from django.db import transaction
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from apps.tailors.models import TailorProfile, TailorStaffMember
from apps.tailors.permissions import IsShopOwner
from apps.tailors.serializers.v2.staff import (
    OwnerStaffAssignmentCreateSerializer,
    OwnerStaffAssignmentSerializer,
    OwnerStaffAssignmentUpdateSerializer,
    OwnerStaffCreateSerializer,
    OwnerStaffMemberSerializer,
    OwnerStaffUpdateSerializer,
)
from apps.tailors.services.owner_staff import (
    create_or_update_shop_assignment,
    find_or_create_staff_user,
)
from apps.tailors.services.v2.staff import get_staff_member, staff_roster_queryset
from apps.tailors.views.base import BaseTailorAPIView
from zthob.utils import api_response


class V2StaffListCreateView(BaseTailorAPIView):
    permission_classes = [IsAuthenticated, IsShopOwner]

    @extend_schema(responses={200: OwnerStaffMemberSerializer(many=True)}, tags=['V2 Staff'])
    def get(self, request):
        roster = staff_roster_queryset(owner_id=request.user.id)
        serializer = OwnerStaffMemberSerializer(roster, many=True)
        return api_response(
            success=True,
            message='Staff fetched',
            data=serializer.data,
            status_code=status.HTTP_200_OK,
            request=request,
        )

    @extend_schema(request=OwnerStaffCreateSerializer, responses={201: OwnerStaffMemberSerializer}, tags=['V2 Staff'])
    def post(self, request):
        serializer = OwnerStaffCreateSerializer(
            data=request.data,
            context={'owner': request.user},
        )
        if not serializer.is_valid():
            return api_response(
                success=False,
                message='Validation failed',
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
                request=request,
            )

        data = serializer.validated_data
        owner = request.user
        with transaction.atomic():
            user, _created = find_or_create_staff_user(
                phone=data['phone'],
                name=data['name'],
            )
            if user.id == owner.id:
                return api_response(
                    success=False,
                    message='Shop owner cannot be added as staff',
                    status_code=status.HTTP_400_BAD_REQUEST,
                    request=request,
                )

            staff_member, member_created = TailorStaffMember.objects.get_or_create(
                owner=owner,
                user=user,
                defaults={'is_active': data.get('is_active', True)},
            )
            if not member_created and 'is_active' in data:
                staff_member.is_active = data['is_active']
                staff_member.save(update_fields=['is_active'])

            if data.get('name'):
                name_parts = data['name'].strip().split(' ', 1)
                user.first_name = name_parts[0]
                user.last_name = name_parts[1] if len(name_parts) > 1 else ''
                user.save(update_fields=['first_name', 'last_name'])

            shop_id = data.get('shop_id')
            if shop_id:
                shop = TailorProfile.objects.get(id=shop_id, owner=owner)
                create_or_update_shop_assignment(
                    staff_member=staff_member,
                    shop=shop,
                    roles=data.get('roles') or [],
                    permissions=data.get('permissions') or [],
                    is_active=True,
                )

        staff_member = get_staff_member(owner_id=owner.id, staff_id=staff_member.id)
        response = OwnerStaffMemberSerializer(staff_member)
        return api_response(
            success=True,
            message='Staff member added',
            data=response.data,
            status_code=status.HTTP_201_CREATED,
            request=request,
        )


class V2StaffDetailView(BaseTailorAPIView):
    permission_classes = [IsAuthenticated, IsShopOwner]

    @extend_schema(responses={200: OwnerStaffMemberSerializer}, tags=['V2 Staff'])
    def get(self, request, staff_id):
        staff_member = get_staff_member(owner_id=request.user.id, staff_id=staff_id)
        if staff_member is None:
            return api_response(
                success=False,
                message='Staff member not found',
                status_code=status.HTTP_404_NOT_FOUND,
                request=request,
            )
        serializer = OwnerStaffMemberSerializer(staff_member)
        return api_response(
            success=True,
            message='Staff member loaded',
            data=serializer.data,
            status_code=status.HTTP_200_OK,
            request=request,
        )

    @extend_schema(request=OwnerStaffUpdateSerializer, tags=['V2 Staff'])
    def patch(self, request, staff_id):
        staff_member = get_staff_member(owner_id=request.user.id, staff_id=staff_id)
        if staff_member is None:
            return api_response(
                success=False,
                message='Staff member not found',
                status_code=status.HTTP_404_NOT_FOUND,
                request=request,
            )
        serializer = OwnerStaffUpdateSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return api_response(
                success=False,
                message='Validation failed',
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
                request=request,
            )
        data = serializer.validated_data
        if 'name' in data:
            parts = data['name'].strip().split(' ', 1)
            staff_member.user.first_name = parts[0]
            staff_member.user.last_name = parts[1] if len(parts) > 1 else ''
            staff_member.user.save(update_fields=['first_name', 'last_name'])
        if 'is_active' in data:
            staff_member.is_active = data['is_active']
            staff_member.save(update_fields=['is_active'])
        staff_member = get_staff_member(owner_id=request.user.id, staff_id=staff_id)
        return api_response(
            success=True,
            message='Staff member updated',
            data=OwnerStaffMemberSerializer(staff_member).data,
            status_code=status.HTTP_200_OK,
            request=request,
        )


class V2StaffAssignmentListCreateView(BaseTailorAPIView):
    permission_classes = [IsAuthenticated, IsShopOwner]

    @extend_schema(tags=['V2 Staff'])
    def post(self, request, staff_id):
        staff_member = get_staff_member(owner_id=request.user.id, staff_id=staff_id)
        if staff_member is None:
            return api_response(
                success=False,
                message='Staff member not found',
                status_code=status.HTTP_404_NOT_FOUND,
                request=request,
            )
        serializer = OwnerStaffAssignmentCreateSerializer(
            data=request.data,
            context={'owner': request.user},
        )
        if not serializer.is_valid():
            return api_response(
                success=False,
                message='Validation failed',
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
                request=request,
            )
        data = serializer.validated_data
        shop = TailorProfile.objects.get(id=data['shop_id'], owner=request.user)
        assignment, _created = create_or_update_shop_assignment(
            staff_member=staff_member,
            shop=shop,
            roles=data.get('roles') or [],
            permissions=data.get('permissions') or [],
            is_active=True,
        )
        return api_response(
            success=True,
            message='Staff assigned to shop',
            data=OwnerStaffAssignmentSerializer(assignment).data,
            status_code=status.HTTP_201_CREATED,
            request=request,
        )
