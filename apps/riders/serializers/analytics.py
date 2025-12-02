"""
Rider Analytics Serializers
"""
from rest_framework import serializers


class DailyDeliveriesSerializer(serializers.Serializer):
    """Serializer for daily deliveries data"""
    date = serializers.CharField()
    deliveries_count = serializers.IntegerField()
    delivery_fees = serializers.CharField()
    formatted_delivery_fees = serializers.CharField()


class WeeklyTrendSerializer(serializers.Serializer):
    """Serializer for weekly trend data"""
    week_start = serializers.CharField()
    week_end = serializers.CharField()
    week_label = serializers.CharField()
    orders_assigned = serializers.IntegerField()
    deliveries_completed = serializers.IntegerField()
    delivery_fees = serializers.CharField()
    formatted_delivery_fees = serializers.CharField()


class AnalyticsPeriodSerializer(serializers.Serializer):
    """Serializer for analytics period info"""
    daily_deliveries_days = serializers.IntegerField()
    weekly_trends_weeks = serializers.IntegerField()
    generated_at = serializers.CharField()


class RiderAnalyticsSerializer(serializers.Serializer):
    """Comprehensive rider analytics serializer"""
    total_delivery_fees = serializers.CharField()
    formatted_total_delivery_fees = serializers.CharField()
    completed_deliveries_count = serializers.IntegerField()
    total_orders_count = serializers.IntegerField()
    completion_percentage = serializers.FloatField()
    formatted_completion_percentage = serializers.CharField()
    daily_deliveries = DailyDeliveriesSerializer(many=True)
    weekly_trends = WeeklyTrendSerializer(many=True)
    analytics_period = AnalyticsPeriodSerializer()

