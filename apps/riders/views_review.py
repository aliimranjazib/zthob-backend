# apps/riders/views_review.py
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from drf_spectacular.utils import extend_schema
from zthob.utils import api_response
from rest_framework import status
from django.utils import timezone

from .models import RiderProfileReview
from .serializers import (
    RiderProfileReviewSerializer,
    RiderProfileReviewUpdateSerializer
)


@extend_schema(
    tags=["Admin - Rider Review"],
    description="Get all rider profiles pending review (Admin only)"
)
class RiderProfileReviewListView(APIView):
    """
    API for admins to get all rider profiles pending review
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        status_filter = request.query_params.get('status', 'pending')
        
        profiles = RiderProfileReview.objects.filter(
            review_status=status_filter
        ).select_related('profile__user', 'reviewed_by').order_by('-submitted_at')
        
        serializer = RiderProfileReviewSerializer(profiles, many=True)
        
        return api_response(
            success=True,
            message=f"Rider profiles with status '{status_filter}' retrieved",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )


@extend_schema(
    tags=["Admin - Rider Review"],
    description="Get individual rider profile review details (Admin only)"
)
class RiderProfileReviewDetailView(APIView):
    """
    API for admins to review individual rider profiles
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request, pk):
        try:
            profile = RiderProfileReview.objects.select_related(
                'profile__user', 'reviewed_by'
            ).get(pk=pk)
        except RiderProfileReview.DoesNotExist:
            return api_response(
                success=False,
                message="Rider profile review not found",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        serializer = RiderProfileReviewSerializer(profile)
        return api_response(
            success=True,
            message="Rider profile review details retrieved",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )
    
    def put(self, request, pk):
        try:
            profile = RiderProfileReview.objects.get(pk=pk)
        except RiderProfileReview.DoesNotExist:
            return api_response(
                success=False,
                message="Rider profile review not found",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        serializer = RiderProfileReviewUpdateSerializer(profile, data=request.data)
        if serializer.is_valid():
            # Update review details
            profile.reviewed_at = timezone.now()
            profile.reviewed_by = request.user
            profile.save()
            
            # Update the review status and rejection reason
            serializer.save()
            
            # TODO: Send notification to rider (implement later)
            # send_review_notification(profile)
            
            return api_response(
                success=True,
                message=f"Rider profile {serializer.validated_data['review_status']} successfully",
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )
        
        return api_response(
            success=False,
            message="Validation failed",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )

