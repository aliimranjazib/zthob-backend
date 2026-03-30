# apps/tailors/serializers/employee.py
from rest_framework import serializers
from apps.tailors.models.employee import TailorEmployee
from apps.core.services import PhoneVerificationService


VALID_ROLES = list(TailorEmployee.VALID_ROLES)
VALID_PERMISSIONS = [
    'can_manage_orders',
    'can_manage_catalog',
    'can_view_analytics',
    'can_manage_employees',
    'can_manage_pos',
]


class TailorEmployeeCreateSerializer(serializers.Serializer):
    """Serializer for creating a new employee under a tailor shop."""

    name       = serializers.CharField(max_length=150)
    phone      = serializers.CharField(max_length=20)
    roles      = serializers.ListField(
        child=serializers.ChoiceField(choices=VALID_ROLES),
        min_length=1,
        help_text="List of roles e.g. ['stitcher', 'cutter']"
    )
    permissions = serializers.ListField(
        child=serializers.ChoiceField(choices=VALID_PERMISSIONS),
        required=False,
        default=list,
        help_text="List of permission keys to grant e.g. ['can_manage_orders']"
    )

    def validate_roles(self, value):
        unknown = set(value) - TailorEmployee.VALID_ROLES
        if unknown:
            raise serializers.ValidationError(
                f"Invalid roles: {', '.join(unknown)}. Valid: {', '.join(VALID_ROLES)}"
            )
        return list(set(value))  # deduplicate

    def validate_permissions(self, value):
        unknown = set(value) - set(VALID_PERMISSIONS)
        if unknown:
            raise serializers.ValidationError(
                f"Invalid permissions: {', '.join(unknown)}"
            )
        return list(set(value))  # deduplicate

    def validate_phone(self, value):
        # Normalize to local format for consistency
        return PhoneVerificationService.normalize_phone_to_local(value)


class TailorEmployeeUpdateSerializer(serializers.Serializer):
    """Serializer for partially updating an employee (roles / permissions / status)."""

    name = serializers.CharField(max_length=150, required=False)
    roles = serializers.ListField(
        child=serializers.ChoiceField(choices=VALID_ROLES),
        min_length=1,
        required=False
    )
    permissions = serializers.ListField(
        child=serializers.ChoiceField(choices=VALID_PERMISSIONS),
        required=False
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
        unknown = set(value) - set(VALID_PERMISSIONS)
        if unknown:
            raise serializers.ValidationError(
                f"Invalid permissions: {', '.join(unknown)}"
            )
        return list(set(value))


class TailorEmployeeResponseSerializer(serializers.ModelSerializer):
    """Read serializer — returned on create, list, detail."""

    name        = serializers.SerializerMethodField()
    phone       = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = TailorEmployee
        fields = [
            'id', 'name', 'phone',
            'roles', 'permissions',
            'is_active', 'joined_at', 'updated_at',
        ]

    def get_name(self, obj):
        return obj.user.get_full_name() or obj.user.phone or ''

    def get_phone(self, obj):
        return obj.user.phone or ''

    def get_permissions(self, obj):
        return obj.permissions_dict
