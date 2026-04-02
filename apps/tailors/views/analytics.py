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


from apps.tailors.permissions import IsShopStaff

@extend_schema(
    tags=["Tailor Analytics"],
    description="Get comprehensive analytics for the authenticated tailor including revenue, orders, and trends"
)
class TailorAnalyticsView(APIView):
    """
    API endpoint for tailor analytics dashboard.
    """
    permission_classes = [IsAuthenticated, IsShopStaff]
    required_employee_permission = 'can_view_analytics'

    
    @extend_schema(
        description="Get comprehensive tailor analytics",
        parameters=[
            {
                'name': 'days',
                'in': 'query',
                'description': 'Number of days for analytics (1, 7, 15, 30). Default is 30.',
                'required': False,
                'schema': {'type': 'integer', 'enum': [1, 7, 15, 30], 'default': 30}
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
            days_str = request.query_params.get('days', '30')
            days = int(days_str)
            
            allowed_days = [1, 7, 15, 30]
            if days not in allowed_days:
                return api_response(
                    success=False,
                    message="Days parameter must be one of: 1, 7, 15, 30",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Calculate weeks based on days for trends
            # 1 day -> 1 week trend
            # 7 days -> 1 week trend
            # 15 days -> 2 weeks trend
            # 30 days -> 4 weeks trend
            if days == 30:
                weeks = 4
            elif days == 15:
                weeks = 2
            else:
                weeks = 1
                
        except ValueError:
            return api_response(
                success=False,
                message="Invalid query parameters. Days must be an integer (1, 7, 15, or 30).",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # Determine the target shop owner user
        target_owner = None
        if hasattr(request.user, 'tailor_profile'):
            target_owner = request.user
        elif hasattr(request.user, 'tailor_employee'):
            # Use the owner of the shop the employee works for
            target_owner = request.user.tailor_employee.tailor.user
            
        if not target_owner:
            return api_response(
                success=False,
                message="Shop profile matching your account not found",
                status_code=status.HTTP_404_NOT_FOUND
            )

        # Get analytics data
        try:
            analytics_data = TailorAnalyticsService.get_comprehensive_analytics(
                tailor_user=target_owner,
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

