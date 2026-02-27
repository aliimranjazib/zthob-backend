# apps/riders/views/config.py
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from apps.orders.models import Order
from zthob.utils import api_response
from zthob.translations import translate_message, get_language_from_request
from rest_framework import status
from rest_framework.permissions import AllowAny

class RiderConfigView(APIView):
    """Extensible configuration endpoint for Rider App"""
    permission_classes = [AllowAny]

    @extend_schema(
        responses={200: dict},
        summary="Get rider app configuration",
        description="Returns global configuration for the rider app, including statuses and types with translations.",
        tags=["Rider Config"]
    )
    def get(self, request):
        language = get_language_from_request(request)
        
        # 1. Rider Statuses
        rider_statuses = []
        for key, display_name in Order.RIDER_STATUS_CHOICES:
            # Override 'none' to 'New' as requested
            label = "New" if key == 'none' else display_name
            rider_statuses.append({
                "key": key,
                "display_name": translate_message(label, language)
            })
            
        # 2. Order Types
        order_types = []
        for key, display_name in Order.ORDER_TYPE_CHOICES:
            order_types.append({
                "key": key,
                "display_name": translate_message(display_name, language)
            })

        # 3. Service Modes
        service_modes = []
        for key, display_name in Order.SERVICE_MODE_CHOICES:
            service_modes.append({
                "key": key,
                "display_name": translate_message(display_name, language)
            })
        
        config_data = {
            "rider_statuses": rider_statuses,
            "order_types": order_types,
            "service_modes": service_modes
        }
        
        return api_response(
            success=True,
            message="Rider configuration retrieved",
            data=config_data,
            status_code=status.HTTP_200_OK
        )
