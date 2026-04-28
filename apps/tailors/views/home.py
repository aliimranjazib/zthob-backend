from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from drf_spectacular.utils import extend_schema

from apps.tailors.permissions import IsShopStaff
from apps.tailors.services.home_service import TailorHomeService
from apps.tailors.serializers.home import TailorHomeSerializer
from zthob.utils import api_response

class TailorHomeAPIView(APIView):
    """
    Unified API for the Tailor Dashboard Home.
    Aggregates counters, express orders, and recent activity.
    """
    permission_classes = [IsAuthenticated, IsShopStaff]
    serializer_class = TailorHomeSerializer

    @extend_schema(
        tags=["Tailor Home"],
        operation_id="tailor_home_data",
        description="Get real-time operational dashboard data for the authenticated tailor/staff.",
        responses={200: TailorHomeSerializer}
    )
    def get(self, request):
        # Determine the target shop owner user (if staff member is logged in)
        target_owner = request.user
        if hasattr(request.user, 'tailor_employee'):
            target_owner = request.user.tailor_employee.tailor.user
            
        try:
            # 1. Fetch data via Service (Optimized Queries)
            data = TailorHomeService.get_dashboard_data(target_owner)
            
            # 2. Serialize response
            serializer = TailorHomeSerializer(data, context={'request': request})
            
            return api_response(
                success=True,
                message="Dashboard data fetched successfully",
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )
        except Exception as e:
            return api_response(
                success=False,
                message=f"Error fetching dashboard data: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
