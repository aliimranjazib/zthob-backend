# apps/tailors/views/config.py
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from apps.orders.models import Order
from zthob.utils import api_response
from zthob.translations import translate_message, get_language_from_request
from rest_framework import status
from rest_framework.permissions import AllowAny

class TailorConfigView(APIView):
    """Extensible configuration endpoint for Tailor App"""
    permission_classes = [AllowAny]

    @extend_schema(
        responses={200: dict},
        summary="Get tailor app configuration",
        description="Returns global configuration for the tailor app, including available statuses. Extensible for future settings.",
        tags=["Tailor Config"]
    )
    def get(self, request):
        language = get_language_from_request(request)
        
        # 1. Available Tailor Statuses
        statuses = []
        for key, display_name in Order.TAILOR_STATUS_CHOICES:
            statuses.append({
                "key": key,
                "display_name": translate_message(display_name, language)
            })

        # Add ready_for_delivery convenience mapping
        statuses.append({
            "key": "ready_for_delivery",
            "display_name": translate_message("Ready for Delivery", language)
        })

        # 2. Employee Roles
        employee_roles = [
            {
                "key": "manager",
                "title": translate_message("Manager", language),
                "description": translate_message(
                    "Manages the shop on behalf of the owner. Has access to orders, catalog, and staff.",
                    language
                ),
                "default_permissions": ["can_manage_orders", "can_manage_catalog", "can_view_analytics", "can_manage_pos"]
            },
            {
                "key": "stitcher",
                "title": translate_message("Stitcher", language),
                "description": translate_message(
                    "Responsible for stitching garments. Can view and update assigned orders.",
                    language
                ),
                "default_permissions": ["can_manage_orders"]
            },
            {
                "key": "cutter",
                "title": translate_message("Cutter", language),
                "description": translate_message(
                    "Responsible for cutting fabric. Can view catalog and assigned orders.",
                    language
                ),
                "default_permissions": ["can_manage_orders", "can_manage_catalog"]
            },
            {
                "key": "receptionist",
                "title": translate_message("Receptionist", language),
                "description": translate_message(
                    "Handles customer interactions and POS. Can manage orders and customers.",
                    language
                ),
                "default_permissions": ["can_manage_orders", "can_manage_pos"]
            },
            {
                "key": "finisher",
                "title": translate_message("Finisher", language),
                "description": translate_message(
                    "Handles final touches and quality checks before delivery.",
                    language
                ),
                "default_permissions": ["can_manage_orders"]
            },
        ]

        # 3. Employee Permissions (all available toggles)
        employee_permissions = [
            {
                "key": "can_manage_orders",
                "title": translate_message("Manage Orders", language),
                "description": translate_message(
                    "Can view, accept, and update order statuses.",
                    language
                ),
            },
            {
                "key": "can_manage_catalog",
                "title": translate_message("Manage Catalog", language),
                "description": translate_message(
                    "Can add, edit, and delete fabrics and categories.",
                    language
                ),
            },
            {
                "key": "can_view_analytics",
                "title": translate_message("View Analytics", language),
                "description": translate_message(
                    "Can view shop performance reports and statistics.",
                    language
                ),
            },
            {
                "key": "can_manage_employees",
                "title": translate_message("Manage Employees", language),
                "description": translate_message(
                    "Can add, edit, and remove other employees. Only grant to trusted staff.",
                    language
                ),
            },
            {
                "key": "can_manage_pos",
                "title": translate_message("Manage POS & Customers", language),
                "description": translate_message(
                    "Can use the point-of-sale system and manage customer records.",
                    language
                ),
            },
        ]

        config_data = {
            "statuses": statuses,
            "employee_roles": employee_roles,
            "employee_permissions": employee_permissions,
        }
        
        return api_response(
            success=True,
            message="Tailor configuration retrieved",
            data=config_data,
            status_code=status.HTTP_200_OK
        )
