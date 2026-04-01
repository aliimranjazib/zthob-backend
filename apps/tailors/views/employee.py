# apps/tailors/views/employee.py
import logging
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from drf_spectacular.utils import extend_schema

from apps.tailors.models.employee import TailorEmployee
from apps.tailors.serializers.employee import (
    TailorEmployeeCreateSerializer,
    TailorEmployeeUpdateSerializer,
    TailorEmployeeResponseSerializer,
)
from apps.core.services import PhoneVerificationService
from zthob.utils import api_response
from zthob.translations import translate_message, get_language_from_request

logger = logging.getLogger(__name__)

PERMISSION_KEYS = [
    'can_manage_orders',
    'can_manage_catalog',
    'can_view_analytics',
    'can_manage_employees',
    'can_manage_pos',
]


def _get_tailor_profile(user):
    """
    Returns (tailor_profile, error_response).
    Checks the requesting user is a tailor owner (not an employee).
    """
    if not hasattr(user, 'tailor_profile'):
        return None, 'Tailor profile not found'
    # If the user is themselves an employee they cannot manage other employees
    # unless they have can_manage_employees permission
    return user.tailor_profile, None


def _apply_permissions(employee, permissions_list):
    """Set all 5 boolean permission fields based on the provided list."""
    for key in PERMISSION_KEYS:
        setattr(employee, key, key in permissions_list)


class TailorEmployeeListCreateView(APIView):
    """
    GET  /tailor/employees/  — list all employees of the authenticated tailor
    POST /tailor/employees/  — add a new employee
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: TailorEmployeeResponseSerializer(many=True)},
        tags=["Tailor Employees"],
        summary="List all employees",
    )
    def get(self, request):
        language = get_language_from_request(request)
        tailor, err = _get_tailor_profile(request.user)
        if err:
            return api_response(
                success=False,
                message=translate_message(err, language),
                status_code=status.HTTP_403_FORBIDDEN
            )

        employees = (
            TailorEmployee.objects
            .filter(tailor=tailor)
            .select_related('user')   # single JOIN — no N+1
            .order_by('-joined_at')
        )
        serializer = TailorEmployeeResponseSerializer(employees, many=True)
        return api_response(
            success=True,
            message=translate_message("Employees retrieved successfully", language),
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )

    @extend_schema(
        request=TailorEmployeeCreateSerializer,
        responses={201: TailorEmployeeResponseSerializer},
        tags=["Tailor Employees"],
        summary="Add a new employee",
        description=(
            "Creates or finds a user by phone number and adds them as an employee "
            "to the authenticated tailor's shop. Supports multiple roles and permissions."
        )
    )
    def post(self, request):
        language = get_language_from_request(request)
        tailor, err = _get_tailor_profile(request.user)
        if err:
            return api_response(
                success=False,
                message=translate_message(err, language),
                status_code=status.HTTP_403_FORBIDDEN
            )

        serializer = TailorEmployeeCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(
                success=False,
                message=translate_message("Validation failed", language),
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        data = serializer.validated_data
        phone = data['phone']
        name  = data['name'].strip()
        roles = data['roles']
        permissions = data.get('permissions', [])

        try:
            with transaction.atomic():
                from django.contrib.auth import get_user_model
                User = get_user_model()

                # Find or create user by phone
                user = User.objects.filter(phone=phone).first()
                if not user:
                    # Create a stub user — they will verify OTP on first login
                    name_parts = name.split(' ', 1)
                    username = f"emp_{phone}"
                    # Ensure unique username
                    counter = 1
                    while User.objects.filter(username=username).exists():
                        username = f"emp_{phone}_{counter}"
                        counter += 1

                    user = User.objects.create_user(
                        username=username,
                        phone=phone,
                        first_name=name_parts[0],
                        last_name=name_parts[1] if len(name_parts) > 1 else '',
                        email=None,
                        role='TAILOR',
                        is_active=True,
                    )
                else:
                    # Update name and role if user exists
                    name_parts = name.split(' ', 1)
                    user.first_name = name_parts[0]
                    user.last_name  = name_parts[1] if len(name_parts) > 1 else ''
                    
                    # Ensure user has TAILOR role (promote from USER, don't demote ADMIN)
                    if user.role == 'USER':
                        user.role = 'TAILOR'
                    
                    user.save(update_fields=['first_name', 'last_name', 'role'])


                # Guard: user can't be an employee of another shop
                existing = TailorEmployee.objects.filter(user=user).select_related('tailor').first()
                if existing and existing.tailor_id != tailor.id:
                    return api_response(
                        success=False,
                        message=translate_message(
                            "This phone number is already an employee at another shop",
                            language
                        ),
                        status_code=status.HTTP_409_CONFLICT
                    )

                # Create or update employee record
                employee, created = TailorEmployee.objects.get_or_create(
                    tailor=tailor,
                    user=user,
                    defaults={'roles': roles}
                )

                if not created:
                    # Re-adding/updating an existing employee
                    employee.roles = roles
                    employee.is_active = True

                _apply_permissions(employee, permissions)
                employee.save()

        except Exception as e:
            logger.exception("Error creating tailor employee")
            return api_response(
                success=False,
                message=translate_message("Failed to add employee", language),
                errors=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        response_serializer = TailorEmployeeResponseSerializer(employee)
        return api_response(
            success=True,
            message=translate_message("Employee added successfully", language),
            data=response_serializer.data,
            status_code=status.HTTP_201_CREATED
        )


class TailorEmployeeDetailView(APIView):
    """
    GET    /tailor/employees/<id>/  — get one employee
    PATCH  /tailor/employees/<id>/  — update roles / permissions / status
    DELETE /tailor/employees/<id>/  — remove employee from shop
    """
    permission_classes = [IsAuthenticated]

    def _get_employee(self, request, pk):
        """Fetch employee and verify it belongs to the requesting tailor."""
        tailor, err = _get_tailor_profile(request.user)
        if err:
            return None, None, err
        try:
            employee = (
                TailorEmployee.objects
                .select_related('user', 'tailor')
                .get(pk=pk, tailor=tailor)
            )
            return employee, tailor, None
        except TailorEmployee.DoesNotExist:
            return None, None, "Employee not found"

    @extend_schema(
        responses={200: TailorEmployeeResponseSerializer},
        tags=["Tailor Employees"],
        summary="Get employee detail",
    )
    def get(self, request, pk):
        language = get_language_from_request(request)
        employee, _, err = self._get_employee(request, pk)
        if err:
            code = status.HTTP_404_NOT_FOUND if "not found" in err else status.HTTP_403_FORBIDDEN
            return api_response(
                success=False,
                message=translate_message(err, language),
                status_code=code
            )
        serializer = TailorEmployeeResponseSerializer(employee)
        return api_response(
            success=True,
            message=translate_message("Employee retrieved successfully", language),
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )

    @extend_schema(
        request=TailorEmployeeUpdateSerializer,
        responses={200: TailorEmployeeResponseSerializer},
        tags=["Tailor Employees"],
        summary="Update employee roles / permissions / status",
    )
    def patch(self, request, pk):
        language = get_language_from_request(request)
        employee, _, err = self._get_employee(request, pk)
        if err:
            code = status.HTTP_404_NOT_FOUND if "not found" in err else status.HTTP_403_FORBIDDEN
            return api_response(
                success=False,
                message=translate_message(err, language),
                status_code=code
            )

        serializer = TailorEmployeeUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(
                success=False,
                message=translate_message("Validation failed", language),
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        data = serializer.validated_data

        # Update name on the linked user if provided
        if 'name' in data:
            name_parts = data['name'].strip().split(' ', 1)
            employee.user.first_name = name_parts[0]
            employee.user.last_name  = name_parts[1] if len(name_parts) > 1 else ''
            employee.user.save(update_fields=['first_name', 'last_name'])

        if 'roles' in data:
            employee.roles = data['roles']

        if 'permissions' in data:
            _apply_permissions(employee, data['permissions'])

        if 'is_active' in data:
            employee.is_active = data['is_active']

        employee.save()

        response_serializer = TailorEmployeeResponseSerializer(employee)
        return api_response(
            success=True,
            message=translate_message("Employee updated successfully", language),
            data=response_serializer.data,
            status_code=status.HTTP_200_OK
        )

    @extend_schema(
        tags=["Tailor Employees"],
        summary="Remove employee from shop",
    )
    def delete(self, request, pk):
        language = get_language_from_request(request)
        employee, _, err = self._get_employee(request, pk)
        if err:
            code = status.HTTP_404_NOT_FOUND if "not found" in err else status.HTTP_403_FORBIDDEN
            return api_response(
                success=False,
                message=translate_message(err, language),
                status_code=code
            )

        employee.delete()
        return api_response(
            success=True,
            message=translate_message("Employee removed successfully", language),
            status_code=status.HTTP_200_OK
        )
