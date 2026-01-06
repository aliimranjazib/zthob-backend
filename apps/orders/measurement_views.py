"""
Measurement Eligibility API View

This view checks if a customer is eligible for the free measurement service.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status


class MeasurementEligibilityView(APIView):
    """
    Check if customer is eligible for free measurement service.
    
    GET /api/orders/measurement-eligibility/
    
    Returns:
        {
            "is_eligible": true/false,
            "message": "Explanation message"
        }
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            profile = request.user.customer_profile
            
            if profile.first_free_measurement_used:
                return Response({
                    'is_eligible': False,
                    'message': 'Your account has already used the free measurement service.',
                    'used_date': profile.free_measurement_date
                })
            
            return Response({
                'is_eligible': True,
                'message': 'You are eligible for free measurement service.'
            })
            
        except Exception as e:
            return Response({
                'is_eligible': False,
                'message': 'Customer profile not found. Please complete your profile first.',
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
