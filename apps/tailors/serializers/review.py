# apps/tailors/serializers/review.py
from rest_framework import serializers
from ..models import TailorProfileReview

class TailorProfileReviewSerializer(serializers.ModelSerializer):
    """Serializer for viewing tailor profile review details."""
    user_email = serializers.EmailField(source='profile.user.email', read_only=True)
    user_name = serializers.CharField(source='profile.user.get_full_name', read_only=True)
    shop_name = serializers.CharField(source='profile.shop_name', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.get_full_name', read_only=True)
    
    class Meta:
        model = TailorProfileReview
        fields = [
            'id', 'profile', 'user_email', 'user_name', 'shop_name',
            'review_status', 'submitted_at', 'reviewed_at', 
            'reviewed_by', 'reviewed_by_name', 'rejection_reason',
            'service_areas', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'profile', 'submitted_at', 'reviewed_at', 
            'reviewed_by', 'created_at', 'updated_at'
        ]

class TailorProfileReviewUpdateSerializer(serializers.ModelSerializer):
    """Serializer for admin to update review status."""
    
    class Meta:
        model = TailorProfileReview
        fields = ['review_status', 'rejection_reason']
    
    def validate_review_status(self, value):
        if value not in ['approved', 'rejected']:
            raise serializers.ValidationError("Review status must be 'approved' or 'rejected'")
        return value

class TailorProfileStatusSerializer(serializers.ModelSerializer):
    """Serializer for tailor to check their profile review status."""
    
    class Meta:
        model = TailorProfileReview
        fields = [
            'review_status', 'submitted_at', 'reviewed_at', 
            'rejection_reason', 'service_areas'
        ]
        read_only_fields = ['review_status', 'submitted_at', 'reviewed_at', 'rejection_reason', 'service_areas']
