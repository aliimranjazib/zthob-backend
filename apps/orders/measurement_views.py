"""
Measurement Eligibility API View

This view checks if a customer is eligible for the free measurement service.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from apps.customers.models import CustomerProfile
from zthob.utils import api_response


class MeasurementEligibilityView(APIView):
    """
    Check if customer is eligible for free measurement service.
    
    GET /api/orders/measurement-eligibility/
    
    Returns:
        {
            "is_eligible": true/false,
            "message": "Explanation message",
            "used_date": "2026-01-07" (if already used)
        }
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Only customers can check eligibility
        if request.user.role != 'USER':
            return api_response(
                success=False,
                message='Only customers can check measurement eligibility',
                data={'is_eligible': False},
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        try:
            # Get or create customer profile
            profile, created = CustomerProfile.objects.get_or_create(
                user=request.user
            )
            
            # Check if already used
            if profile.first_free_measurement_used:
                return api_response(
                    success=True,
                    message='Your account has already used the free measurement service.',
                    data={
                        'is_eligible': False,
                        'used_date': profile.free_measurement_date.isoformat() if profile.free_measurement_date else None,
                        'reason': 'already_used'
                    },
                    status_code=status.HTTP_200_OK
                )
            
            # Eligible for free measurement
            return api_response(
                success=True,
                message='You are eligible for free measurement service.',
                data={
                    'is_eligible': True,
                    'reason': 'eligible'
                },
                status_code=status.HTTP_200_OK
            )
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error checking measurement eligibility: {str(e)}")
            
            return api_response(
                success=False,
                message='An error occurred while checking eligibility. Please try again.',
                data={
                    'is_eligible': False,
                    'reason': 'error'
                },
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
