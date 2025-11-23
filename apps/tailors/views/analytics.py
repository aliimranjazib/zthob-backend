"""
Tailor Analytics Views
"""
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from drf_spectacular.utils import extend_schema
from apps.tailors.permissions import IsTailor
from apps.tailors.services import TailorAnalyticsService
from apps.tailors.serializers.analytics import TailorAnalyticsSerializer
from zthob.utils import api_response


@extend_schema(
    tags=["Tailor Analytics"],
    description="Get comprehensive analytics for the authenticated tailor including revenue, orders, and trends"
)
class TailorAnalyticsView(APIView):
    """
    API endpoint for tailor analytics dashboard.
    
    Provides:
    - Total revenue from completed orders
    - Daily earnings breakdown
    - Total completed orders count
    - Completion percentage
    - Weekly order trends
    
    Query Parameters:
    - days: Number of days for daily earnings (default: 30, max: 365)
    - weeks: Number of weeks for trends (default: 12, max: 52)
    """
    permission_classes = [IsAuthenticated, IsTailor]
    
    @extend_schema(
        description="Get comprehensive tailor analytics",
        parameters=[
            {
                'name': 'days',
                'in': 'query',
                'description': 'Number of days for daily earnings breakdown (default: 30, max: 365)',
                'required': False,
                'schema': {'type': 'integer', 'minimum': 1, 'maximum': 365, 'default': 30}
            },
            {
                'name': 'weeks',
                'in': 'query',
                'description': 'Number of weeks for weekly trends (default: 12, max: 52)',
                'required': False,
                'schema': {'type': 'integer', 'minimum': 1, 'maximum': 52, 'default': 12}
            }
        ],
        responses={
            200: TailorAnalyticsSerializer,
            400: {"description": "Invalid query parameters"},
            403: {"description": "User is not a tailor"}
        }
    )
    def get(self, request):
        """
        Get comprehensive analytics for the authenticated tailor.
        """
        # Get query parameters with defaults and validation
        try:
            days = int(request.query_params.get('days', 30))
            weeks = int(request.query_params.get('weeks', 12))
            
            # Validate ranges
            if days < 1 or days > 365:
                return api_response(
                    success=False,
                    message="Days parameter must be between 1 and 365",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            if weeks < 1 or weeks > 52:
                return api_response(
                    success=False,
                    message="Weeks parameter must be between 1 and 52",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
        except ValueError:
            return api_response(
                success=False,
                message="Invalid query parameters. Days and weeks must be integers.",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # Get analytics data
        try:
            analytics_data = TailorAnalyticsService.get_comprehensive_analytics(
                tailor_user=request.user,
                days=days,
                weeks=weeks
            )
            
            # Serialize the data
            serializer = TailorAnalyticsSerializer(analytics_data)
            
            return api_response(
                success=True,
                message="Analytics data retrieved successfully",
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )
        except Exception as e:
            return api_response(
                success=False,
                message=f"Error retrieving analytics: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

