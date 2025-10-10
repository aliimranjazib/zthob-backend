# apps/tailors/views/review.py
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from drf_spectacular.utils import extend_schema
from zthob.utils import api_response
from rest_framework import status
from django.utils import timezone

from ..models import TailorProfileReview
from ..serializers import (
    TailorProfileReviewSerializer,
    TailorProfileReviewUpdateSerializer
)
from .base import BaseTailorAuthenticatedView

@extend_schema(
    tags=["Admin - Profile Review"],
    description="Get all profiles pending review (Admin only)"
)
class TailorProfileReviewListView(APIView):
    """
    API for admins to get all profiles pending review
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        status_filter = request.query_params.get('status', 'pending')
        
        profiles = TailorProfileReview.objects.filter(
            review_status=status_filter
        ).select_related('profile__user', 'reviewed_by').order_by('-submitted_at')
        
        serializer = TailorProfileReviewSerializer(profiles, many=True)
        
        return api_response(
            success=True,
            message=f"Profiles with status '{status_filter}' retrieved",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )

@extend_schema(
    tags=["Admin - Profile Review"],
    description="Get individual profile review details (Admin only)"
)
class TailorProfileReviewDetailView(APIView):
    """
    API for admins to review individual profiles
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request, pk):
        try:
            profile = TailorProfileReview.objects.select_related(
                'profile__user', 'reviewed_by'
            ).get(pk=pk)
        except TailorProfileReview.DoesNotExist:
            return api_response(
                success=False,
                message="Profile review not found",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        serializer = TailorProfileReviewSerializer(profile)
        return api_response(
            success=True,
            message="Profile review details retrieved",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )
    
    def put(self, request, pk):
        try:
            profile = TailorProfileReview.objects.get(pk=pk)
        except TailorProfileReview.DoesNotExist:
            return api_response(
                success=False,
                message="Profile review not found",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        serializer = TailorProfileReviewUpdateSerializer(profile, data=request.data)
        if serializer.is_valid():
            # Update review details
            profile.reviewed_at = timezone.now()
            profile.reviewed_by = request.user
            profile.save()
            
            # Update the review status and rejection reason
            serializer.save()
            
            # TODO: Send notification to tailor (implement later)
            # send_review_notification(profile)
            
            return api_response(
                success=True,
                message=f"Profile {serializer.validated_data['review_status']} successfully",
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )
        
        return api_response(
            success=False,
            message="Validation failed",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )
