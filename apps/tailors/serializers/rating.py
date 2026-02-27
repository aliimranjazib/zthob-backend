# apps/tailors/serializers/rating.py
from rest_framework import serializers
from apps.tailors.models.rating import TailorRating


class TailorRatingCreateSerializer(serializers.ModelSerializer):
    """Serializer for submitting a new tailor rating."""

    class Meta:
        model = TailorRating
        fields = [
            'stitching_quality',
            'on_time_delivery',
            'overall_satisfaction',
            'review',
        ]

    def validate_stitching_quality(self, value):
        if not (1 <= value <= 5):
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value

    def validate_on_time_delivery(self, value):
        if not (1 <= value <= 5):
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value

    def validate_overall_satisfaction(self, value):
        if not (1 <= value <= 5):
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value


class TailorRatingSerializer(serializers.ModelSerializer):
    """Serializer for reading a tailor rating."""
    customer_name = serializers.SerializerMethodField()
    order_number = serializers.SerializerMethodField()

    class Meta:
        model = TailorRating
        fields = [
            'id',
            'order_number',
            'customer_name',
            'stitching_quality',
            'on_time_delivery',
            'overall_satisfaction',
            'review',
            'created_at',
        ]

    def get_customer_name(self, obj):
        return obj.customer.get_full_name() or obj.customer.username

    def get_order_number(self, obj):
        return obj.order.order_number
