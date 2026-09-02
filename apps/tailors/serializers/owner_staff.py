from rest_framework import serializers

from apps.core.phone_utils import format_phone_for_display
from apps.core.services import PhoneVerificationService
from apps.tailors.models import TailorEmployee, TailorStaffMember, ShopStaffAssignment
from apps.tailors.models.staff import STAFF_PERMISSION_KEYS


VALID_ROLES = list(TailorEmployee.VALID_ROLES)


class OwnerStaffAssignmentSerializer(serializers.ModelSerializer):
    shop_id = serializers.IntegerField(source='shop.id', read_only=True)
    shop_name = serializers.CharField(source='shop.shop_name', read_only=True)
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = ShopStaffAssignment
        fields = [
            'id',
            'shop_id',
            'shop_name',
            'roles',
            'permissions',
            'is_active',
            'assigned_at',
            'updated_at',
        ]

    def get_permissions(self, obj):
        return obj.permissions_dict


class OwnerStaffMemberSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    phone = serializers.SerializerMethodField()
    assignments = OwnerStaffAssignmentSerializer(
        source='shop_assignments',
        many=True,
        read_only=True,
    )

    class Meta:
        model = TailorStaffMember
        fields = [
            'id',
            'name',
            'phone',
            'is_active',
            'assignments',
            'joined_at',
            'updated_at',
        ]

    def get_name(self, obj):
        return obj.user.get_full_name() or obj.user.phone or ''

    def get_phone(self, obj):
        if not obj.user.phone:
            return ''
        return format_phone_for_display(obj.user.phone)


class OwnerStaffCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    phone = serializers.CharField(max_length=20)
    roles = serializers.ListField(
        child=serializers.ChoiceField(choices=VALID_ROLES),
        required=False,
        default=list,
    )
    permissions = serializers.ListField(
        child=serializers.ChoiceField(choices=STAFF_PERMISSION_KEYS),
        required=False,
        default=list,
    )
    shop_id = serializers.IntegerField(required=False, allow_null=True)
    is_active = serializers.BooleanField(required=False, default=True)

    def validate_roles(self, value):
        unknown = set(value or []) - TailorEmployee.VALID_ROLES
        if unknown:
            raise serializers.ValidationError(
                f"Invalid roles: {', '.join(unknown)}"
            )
        return list(set(value or []))

    def validate_permissions(self, value):
        unknown = set(value or []) - set(STAFF_PERMISSION_KEYS)
        if unknown:
            raise serializers.ValidationError(
                f"Invalid permissions: {', '.join(unknown)}"
            )
        return list(set(value or []))

    def validate_phone(self, value):
        return PhoneVerificationService.normalize_phone_to_local(value)

    def validate_shop_id(self, value):
        if value in (None, ''):
            return None
        owner = self.context['owner']
        from apps.tailors.models import TailorProfile
        try:
            shop = TailorProfile.objects.get(id=value, owner=owner)
        except TailorProfile.DoesNotExist as exc:
            raise serializers.ValidationError('Shop not found for this owner.') from exc
        return shop.id


class OwnerStaffUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150, required=False)
    is_active = serializers.BooleanField(required=False)


class OwnerStaffAssignmentCreateSerializer(serializers.Serializer):
    shop_id = serializers.IntegerField()
    roles = serializers.ListField(
        child=serializers.ChoiceField(choices=VALID_ROLES),
        min_length=1,
    )
    permissions = serializers.ListField(
        child=serializers.ChoiceField(choices=STAFF_PERMISSION_KEYS),
        required=False,
        default=list,
    )
    is_active = serializers.BooleanField(required=False, default=True)

    def validate_roles(self, value):
        unknown = set(value) - TailorEmployee.VALID_ROLES
        if unknown:
            raise serializers.ValidationError(
                f"Invalid roles: {', '.join(unknown)}"
            )
        return list(set(value))

    def validate_permissions(self, value):
        unknown = set(value or []) - set(STAFF_PERMISSION_KEYS)
        if unknown:
            raise serializers.ValidationError(
                f"Invalid permissions: {', '.join(unknown)}"
            )
        return list(set(value or []))

    def validate_shop_id(self, value):
        owner = self.context['owner']
        from apps.tailors.models import TailorProfile
        try:
            TailorProfile.objects.get(id=value, owner=owner)
        except TailorProfile.DoesNotExist as exc:
            raise serializers.ValidationError('Shop not found for this owner.') from exc
        return value


class OwnerStaffAssignmentUpdateSerializer(serializers.Serializer):
    roles = serializers.ListField(
        child=serializers.ChoiceField(choices=VALID_ROLES),
        min_length=1,
        required=False,
    )
    permissions = serializers.ListField(
        child=serializers.ChoiceField(choices=STAFF_PERMISSION_KEYS),
        required=False,
    )
    is_active = serializers.BooleanField(required=False)

    def validate_roles(self, value):
        unknown = set(value) - TailorEmployee.VALID_ROLES
        if unknown:
            raise serializers.ValidationError(
                f"Invalid roles: {', '.join(unknown)}"
            )
        return list(set(value))

    def validate_permissions(self, value):
        unknown = set(value or []) - set(STAFF_PERMISSION_KEYS)
        if unknown:
            raise serializers.ValidationError(
                f"Invalid permissions: {', '.join(unknown)}"
            )
        return list(set(value or []))
