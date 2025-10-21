# apps/tailors/views/profile.py
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from drf_spectacular.utils import extend_schema
from zthob.utils import api_response
from rest_framework import status
from django.utils import timezone

from ..models import TailorProfile
from ..serializers import (
    TailorProfileSerializer, 
    TailorProfileUpdateSerializer,
    TailorProfileSubmissionSerializer
)
from ..permissions import IsTailor
from .base import BaseTailorAuthenticatedView

@extend_schema(
    tags=["Tailor Profile"],
    description="Tailor profile management operations - supports GET, PUT, and PATCH methods"
)
class TailorProfileView(BaseTailorAuthenticatedView):
    serializer_class = TailorProfileSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        profile, _ = TailorProfile.objects.get_or_create(user=request.user)
        serializer = TailorProfileSerializer(profile, context={'request': request})
        return api_response(
            success=True,
            message='Tailor profile fetched',
            data=serializer.data, 
            status_code=status.HTTP_200_OK
        )
    
    def put(self, request):
        profile, _ = TailorProfile.objects.get_or_create(user=request.user)
        
        # Create a copy of request data
        data = request.data.copy()
        
        # Use TailorProfileUpdateSerializer for basic profile fields
        serializer = TailorProfileUpdateSerializer(profile, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            
            # Service area handling removed - now managed by admin
            
            # Return the full profile data with proper image URLs
            profile_serializer = TailorProfileSerializer(profile, context={'request': request})
            return api_response(
                success=True, 
                message="Tailor profile updated", 
                data=profile_serializer.data, 
                status_code=status.HTTP_200_OK
            )
        return api_response(
            success=False, 
            message="Validation failed", 
            errors=serializer.errors, 
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    def patch(self, request):
        """PATCH method for partial updates - same logic as PUT but explicitly for partial updates."""
        profile, _ = TailorProfile.objects.get_or_create(user=request.user)
        
        # Create a copy of request data
        data = request.data.copy()
        
        # Use TailorProfileUpdateSerializer for basic profile fields with partial=True
        serializer = TailorProfileUpdateSerializer(profile, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            
            # Return the full profile data with proper image URLs
            profile_serializer = TailorProfileSerializer(profile, context={'request': request})
            return api_response(
                success=True, 
                message="Tailor profile updated", 
                data=profile_serializer.data, 
                status_code=status.HTTP_200_OK
            )
        return api_response(
            success=False, 
            message="Validation failed", 
            errors=serializer.errors, 
            status_code=status.HTTP_400_BAD_REQUEST
        )

@extend_schema(
    tags=["Tailor Profile"],
    description="Submit tailor profile for admin review"
)
class TailorProfileSubmissionView(BaseTailorAuthenticatedView):
    serializer_class = TailorProfileSubmissionSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def post(self, request):
        try:
            profile = TailorProfile.objects.get(user=request.user)
        except TailorProfile.DoesNotExist:
            return api_response(
                success=False,
                message="Tailor profile not found",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # Check if already submitted
        if hasattr(profile, 'review') and profile.review.review_status == 'pending':
            return api_response(
                success=False,
                message="Profile already submitted for review",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = TailorProfileSubmissionSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            # Update profile with submitted data
            serializer.save()
            
            # Create or update review record
            from ..models import TailorProfileReview
            review, created = TailorProfileReview.objects.get_or_create(
                profile=profile,
                defaults={
                    'review_status': 'pending',
                    'submitted_at': timezone.now()
                }
            )
            if not created:
                review.review_status = 'pending'
                review.submitted_at = timezone.now()
                review.save()
            
            # Return the full profile data with proper image URLs
            profile_serializer = TailorProfileSerializer(profile, context={'request': request})
            return api_response(
                success=True,
                message="Profile submitted for review successfully",
                data=profile_serializer.data,
                status_code=status.HTTP_200_OK
            )
        
        return api_response(
            success=False,
            message="Validation failed",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )

@extend_schema(
    tags=["Tailor Profile"],
    description="Check tailor profile review status"
)
class TailorProfileStatusView(BaseTailorAuthenticatedView):
    
    def get(self, request):
        try:
            profile = TailorProfile.objects.get(user=request.user)
        except TailorProfile.DoesNotExist:
            return api_response(
                success=False,
                message="Profile not found",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # Get review status
        review = getattr(profile, 'review', None)
        if review:
            data = {
                'review_status': review.review_status,
                'submitted_at': review.submitted_at,
                'reviewed_at': review.reviewed_at,
                'rejection_reason': review.rejection_reason,
                'can_submit': review.review_status in ['draft', 'rejected']
            }
        else:
            data = {
                'review_status': 'draft',
                'submitted_at': None,
                'reviewed_at': None,
                'rejection_reason': None,
                'can_submit': True
            }
        
        return api_response(
            success=True,
            message="Profile status retrieved",
            data=data,
            status_code=status.HTTP_200_OK
        )

@extend_schema(
    tags=["Tailor Profile"],
    description="Update shop status (on/off)"
)
class TailorShopStatusView(BaseTailorAuthenticatedView):
    
    def put(self, request):
        """Update shop status"""
        try:
            profile = TailorProfile.objects.get(user=request.user)
        except TailorProfile.DoesNotExist:
            return api_response(
                success=False,
                message="Profile not found",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # Get shop_status from request data
        shop_status = request.data.get('shop_status')
        if shop_status is None:
            return api_response(
                success=False,
                message="shop_status field is required",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate that shop_status is a boolean
        if not isinstance(shop_status, bool):
            return api_response(
                success=False,
                message="shop_status must be true or false",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        profile.shop_status = shop_status
        profile.save()
        
        status_message = "Shop is now ON" if shop_status else "Shop is now OFF"
        
        return api_response(
            success=True,
            message=status_message,
            data={'shop_status': shop_status},
            status_code=status.HTTP_200_OK
        )
