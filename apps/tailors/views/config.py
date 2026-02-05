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

        # 2. Add future config items here
        # constants = {...}
        # features = {...}
        
        config_data = {
            "statuses": statuses,
            # "other_settings": {} 
        }
        
        return api_response(
            success=True,
            message="Tailor configuration retrieved",
            data=config_data,
            status_code=status.HTTP_200_OK
        )
