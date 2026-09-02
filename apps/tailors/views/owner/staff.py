from django.db import transaction
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from apps.tailors.models import TailorProfile, TailorStaffMember, ShopStaffAssignment
from apps.tailors.permissions import IsShopOwner
from apps.tailors.serializers.owner_staff import (
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
from apps.tailors.services.staff_sync import deactivate_legacy_employee_for_assignment
from apps.tailors.views.base import BaseTailorAPIView
from zthob.utils import api_response


class OwnerStaffListCreateView(BaseTailorAPIView):
    permission_classes = [IsAuthenticated, IsShopOwner]

    @extend_schema(
        responses={200: OwnerStaffMemberSerializer(many=True)},
        tags=['Owner Staff'],
        summary='List staff roster for the authenticated owner',
    )
    def get(self, request):
        roster = (
            TailorStaffMember.objects.filter(owner=request.user)
            .select_related('user')
            .prefetch_related('shop_assignments__shop')
            .order_by('-joined_at')
        )
        serializer = OwnerStaffMemberSerializer(roster, many=True)
        return api_response(
            success=True,
            message='Staff roster retrieved successfully',
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    @extend_schema(
        request=OwnerStaffCreateSerializer,
        responses={201: OwnerStaffMemberSerializer},
        tags=['Owner Staff'],
        summary='Add a staff member to the owner roster',
    )
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

        staff_member = (
            TailorStaffMember.objects.filter(pk=staff_member.pk)
            .select_related('user')
            .prefetch_related('shop_assignments__shop')
            .first()
        )
        response_serializer = OwnerStaffMemberSerializer(staff_member)
        return api_response(
            success=True,
            message='Staff member added successfully',
            data=response_serializer.data,
            status_code=status.HTTP_201_CREATED,
        )


class OwnerStaffDetailView(BaseTailorAPIView):
    permission_classes = [IsAuthenticated, IsShopOwner]

    def _get_staff_member(self, request, staff_id):
        try:
            return TailorStaffMember.objects.select_related('user').get(
                id=staff_id,
                owner=request.user,
            )
        except TailorStaffMember.DoesNotExist:
            return None

    @extend_schema(
        responses={200: OwnerStaffMemberSerializer},
        tags=['Owner Staff'],
        summary='Get one staff roster member',
    )
    def get(self, request, staff_id):
        staff_member = self._get_staff_member(request, staff_id)
        if staff_member is None:
            return api_response(
                success=False,
                message='Staff member not found',
                status_code=status.HTTP_404_NOT_FOUND,
            )

        staff_member = (
            TailorStaffMember.objects.filter(pk=staff_member.pk)
            .select_related('user')
            .prefetch_related('shop_assignments__shop')
            .first()
        )
        serializer = OwnerStaffMemberSerializer(staff_member)
        return api_response(
            success=True,
            message='Staff member retrieved successfully',
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    @extend_schema(
        request=OwnerStaffUpdateSerializer,
        responses={200: OwnerStaffMemberSerializer},
        tags=['Owner Staff'],
        summary='Update staff roster member',
    )
    def patch(self, request, staff_id):
        staff_member = self._get_staff_member(request, staff_id)
        if staff_member is None:
            return api_response(
                success=False,
                message='Staff member not found',
                status_code=status.HTTP_404_NOT_FOUND,
            )

        serializer = OwnerStaffUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(
                success=False,
                message='Validation failed',
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        if 'name' in data:
            name_parts = data['name'].strip().split(' ', 1)
            staff_member.user.first_name = name_parts[0]
            staff_member.user.last_name = name_parts[1] if len(name_parts) > 1 else ''
            staff_member.user.save(update_fields=['first_name', 'last_name'])
        if 'is_active' in data:
            staff_member.is_active = data['is_active']
            staff_member.save(update_fields=['is_active'])

        staff_member = (
            TailorStaffMember.objects.filter(pk=staff_member.pk)
            .select_related('user')
            .prefetch_related('shop_assignments__shop')
            .first()
        )
        response_serializer = OwnerStaffMemberSerializer(staff_member)
        return api_response(
            success=True,
            message='Staff member updated successfully',
            data=response_serializer.data,
            status_code=status.HTTP_200_OK,
        )

    @extend_schema(
        tags=['Owner Staff'],
        summary='Remove staff member from owner roster',
    )
    def delete(self, request, staff_id):
        staff_member = self._get_staff_member(request, staff_id)
        if staff_member is None:
            return api_response(
                success=False,
                message='Staff member not found',
                status_code=status.HTTP_404_NOT_FOUND,
            )

        with transaction.atomic():
            for assignment in staff_member.shop_assignments.all():
                deactivate_legacy_employee_for_assignment(assignment)
            staff_member.delete()

        return api_response(
            success=True,
            message='Staff member removed successfully',
            status_code=status.HTTP_200_OK,
        )


class OwnerStaffAssignmentListCreateView(BaseTailorAPIView):
    permission_classes = [IsAuthenticated, IsShopOwner]

    def _get_staff_member(self, request, staff_id):
        try:
            return TailorStaffMember.objects.get(id=staff_id, owner=request.user)
        except TailorStaffMember.DoesNotExist:
            return None

    @extend_schema(
        responses={200: OwnerStaffAssignmentSerializer(many=True)},
        tags=['Owner Staff'],
        summary='List shop assignments for a staff member',
    )
    def get(self, request, staff_id):
        staff_member = self._get_staff_member(request, staff_id)
        if staff_member is None:
            return api_response(
                success=False,
                message='Staff member not found',
                status_code=status.HTTP_404_NOT_FOUND,
            )

        assignments = (
            ShopStaffAssignment.objects.filter(staff_member=staff_member)
            .select_related('shop')
            .order_by('-assigned_at')
        )
        serializer = OwnerStaffAssignmentSerializer(assignments, many=True)
        return api_response(
            success=True,
            message='Staff assignments retrieved successfully',
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    @extend_schema(
        request=OwnerStaffAssignmentCreateSerializer,
        responses={201: OwnerStaffAssignmentSerializer},
        tags=['Owner Staff'],
        summary='Assign a staff member to a shop',
    )
    def post(self, request, staff_id):
        staff_member = self._get_staff_member(request, staff_id)
        if staff_member is None:
            return api_response(
                success=False,
                message='Staff member not found',
                status_code=status.HTTP_404_NOT_FOUND,
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
            )

        data = serializer.validated_data
        shop = TailorProfile.objects.get(id=data['shop_id'], owner=request.user)
        assignment, _created = create_or_update_shop_assignment(
            staff_member=staff_member,
            shop=shop,
            roles=data['roles'],
            permissions=data.get('permissions') or [],
            is_active=data.get('is_active', True),
        )
        response_serializer = OwnerStaffAssignmentSerializer(assignment)
        return api_response(
            success=True,
            message='Staff assignment saved successfully',
            data=response_serializer.data,
            status_code=status.HTTP_201_CREATED,
        )


class OwnerStaffAssignmentDetailView(BaseTailorAPIView):
    permission_classes = [IsAuthenticated, IsShopOwner]

    def _get_assignment(self, request, staff_id, assignment_id):
        try:
            return ShopStaffAssignment.objects.select_related(
                'shop',
                'staff_member',
            ).get(
                id=assignment_id,
                staff_member_id=staff_id,
                staff_member__owner=request.user,
            )
        except ShopStaffAssignment.DoesNotExist:
            return None

    @extend_schema(
        request=OwnerStaffAssignmentUpdateSerializer,
        responses={200: OwnerStaffAssignmentSerializer},
        tags=['Owner Staff'],
        summary='Update a shop assignment',
    )
    def patch(self, request, staff_id, assignment_id):
        assignment = self._get_assignment(request, staff_id, assignment_id)
        if assignment is None:
            return api_response(
                success=False,
                message='Assignment not found',
                status_code=status.HTTP_404_NOT_FOUND,
            )

        serializer = OwnerStaffAssignmentUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(
                success=False,
                message='Validation failed',
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        roles = data.get('roles', assignment.roles)
        permissions = data.get('permissions')
        if permissions is None:
            permissions = [
                key for key, enabled in assignment.permissions_dict.items() if enabled
            ]

        assignment.apply_roles_and_permissions(roles, permissions)
        if 'is_active' in data:
            assignment.is_active = data['is_active']
        assignment.save()

        from apps.tailors.services.staff_sync import sync_legacy_employee_from_assignment
        if assignment.is_active and assignment.staff_member.is_active:
            sync_legacy_employee_from_assignment(assignment)
        else:
            deactivate_legacy_employee_for_assignment(assignment)

        response_serializer = OwnerStaffAssignmentSerializer(assignment)
        return api_response(
            success=True,
            message='Staff assignment updated successfully',
            data=response_serializer.data,
            status_code=status.HTTP_200_OK,
        )

    @extend_schema(
        tags=['Owner Staff'],
        summary='Remove a shop assignment',
    )
    def delete(self, request, staff_id, assignment_id):
        assignment = self._get_assignment(request, staff_id, assignment_id)
        if assignment is None:
            return api_response(
                success=False,
                message='Assignment not found',
                status_code=status.HTTP_404_NOT_FOUND,
            )

        deactivate_legacy_employee_for_assignment(assignment)
        assignment.delete()
        return api_response(
            success=True,
            message='Staff assignment removed successfully',
            status_code=status.HTTP_200_OK,
        )
