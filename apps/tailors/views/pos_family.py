"""POS family member management for walk-in customers."""

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from apps.customers.models import FamilyMember
from apps.customers.services.audit_log import log_customer_data_change
from apps.orders.models import Order
from apps.tailors.permissions import IsShopStaff
from apps.tailors.serializers.tailor_pos import (
    POSFamilyMemberCreateSerializer,
    POSFamilyMemberSerializer,
    POSFamilyMemberUpdateSerializer,
)
from apps.tailors.services.pos_customer_access import get_customer_for_pos_or_none
from apps.tailors.services.pos_profile_write_policy import tailor_can_edit_family_member
from apps.tailors.views.base import BaseTailorAPIView
from zthob.utils import api_response


class TailorPOSFamilyMemberListCreateView(BaseTailorAPIView):
    """
    GET/POST /api/tailors/pos/customers/{customer_id}/family/
    """
    permission_classes = [IsAuthenticated, IsShopStaff]
    required_employee_permission = 'can_manage_pos'

    def get(self, request, customer_id):
        profile = self.get_tailor_profile(request.user)
        if not profile:
            return api_response(success=False, message='Shop profile not found', status_code=404)

        customer = get_customer_for_pos_or_none(
            tailor_owner_user=profile.user,
            customer_id=customer_id,
        )
        if not customer:
            return api_response(
                success=False,
                message='Customer not found or access denied',
                status_code=status.HTTP_404_NOT_FOUND,
            )

        members = FamilyMember.objects.filter(user=customer).order_by('name', 'id')
        serializer = POSFamilyMemberSerializer(members, many=True)
        return api_response(
            success=True,
            message='Family members retrieved successfully',
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    def post(self, request, customer_id):
        profile = self.get_tailor_profile(request.user)
        if not profile:
            return api_response(success=False, message='Shop profile not found', status_code=404)

        customer = get_customer_for_pos_or_none(
            tailor_owner_user=profile.user,
            customer_id=customer_id,
        )
        if not customer:
            return api_response(
                success=False,
                message='Customer not found or access denied',
                status_code=status.HTTP_404_NOT_FOUND,
            )

        serializer = POSFamilyMemberCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        family_member = FamilyMember.objects.create(
            user=customer,
            name=serializer.validated_data['name'].strip(),
            gender=serializer.validated_data.get('gender') or None,
            relationship=serializer.validated_data.get('relationship') or None,
            created_source='tailor_pos',
            created_by_tailor=profile.user,
            created_by_shop=profile,
        )

        log_customer_data_change(
            customer=customer,
            actor_user=request.user,
            actor_role=getattr(request.user, 'role', ''),
            entity_type='family_member',
            entity_id=family_member.id,
            action='create',
            after=POSFamilyMemberSerializer(family_member).data,
            source='tailor_pos',
        )

        return api_response(
            success=True,
            message='Family member created successfully',
            data=POSFamilyMemberSerializer(family_member).data,
            status_code=status.HTTP_201_CREATED,
        )


class TailorPOSFamilyMemberDetailView(BaseTailorAPIView):
    """
    PATCH/DELETE /api/tailors/pos/customers/{customer_id}/family/{family_member_id}/
    """
    permission_classes = [IsAuthenticated, IsShopStaff]
    required_employee_permission = 'can_manage_pos'

    def _get_family_member(self, request, customer_id, family_member_id):
        profile = self.get_tailor_profile(request.user)
        if not profile:
            return None, None, api_response(success=False, message='Shop profile not found', status_code=404)

        customer = get_customer_for_pos_or_none(
            tailor_owner_user=profile.user,
            customer_id=customer_id,
        )
        if not customer:
            return None, None, api_response(
                success=False,
                message='Customer not found or access denied',
                status_code=status.HTTP_404_NOT_FOUND,
            )

        family_member = get_object_or_404(
            FamilyMember,
            id=family_member_id,
            user=customer,
        )
        return profile, family_member, None

    def patch(self, request, customer_id, family_member_id):
        profile, family_member, error_response = self._get_family_member(
            request, customer_id, family_member_id,
        )
        if error_response:
            return error_response

        if not tailor_can_edit_family_member(
            family_member=family_member,
            actor_shop_id=profile.id,
        ):
            return api_response(
                success=False,
                message='This family member can no longer be edited from POS',
                status_code=status.HTTP_403_FORBIDDEN,
            )

        serializer = POSFamilyMemberUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        before = POSFamilyMemberSerializer(family_member).data
        for field in ('name', 'gender', 'relationship'):
            if field in serializer.validated_data:
                value = serializer.validated_data[field]
                if field == 'name':
                    value = value.strip()
                setattr(family_member, field, value or None)
        family_member.save()

        log_customer_data_change(
            customer=family_member.user,
            actor_user=request.user,
            actor_role=getattr(request.user, 'role', ''),
            entity_type='family_member',
            entity_id=family_member.id,
            action='update',
            before=before,
            after=POSFamilyMemberSerializer(family_member).data,
            source='tailor_pos',
        )

        return api_response(
            success=True,
            message='Family member updated successfully',
            data=POSFamilyMemberSerializer(family_member).data,
            status_code=status.HTTP_200_OK,
        )

    def delete(self, request, customer_id, family_member_id):
        profile, family_member, error_response = self._get_family_member(
            request, customer_id, family_member_id,
        )
        if error_response:
            return error_response

        active_orders = Order.objects.filter(
            customer=family_member.user,
            order_items__family_member=family_member,
        ).exclude(status='cancelled').exists()

        if active_orders:
            return api_response(
                success=False,
                message='Cannot delete family member referenced by active orders',
                status_code=status.HTTP_409_CONFLICT,
            )

        before = POSFamilyMemberSerializer(family_member).data
        family_member.delete()

        log_customer_data_change(
            customer=family_member.user,
            actor_user=request.user,
            actor_role=getattr(request.user, 'role', ''),
            entity_type='family_member',
            entity_id=family_member_id,
            action='delete',
            before=before,
            source='tailor_pos',
        )

        return api_response(
            success=True,
            message='Family member deleted successfully',
            status_code=status.HTTP_200_OK,
        )
