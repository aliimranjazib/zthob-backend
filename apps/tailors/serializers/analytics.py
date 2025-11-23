"""
Tailor Analytics Serializers
"""
from rest_framework import serializers


class DailyEarningsSerializer(serializers.Serializer):
    """Serializer for daily earnings data"""
    date = serializers.CharField()
    earnings = serializers.CharField()
    formatted_earnings = serializers.CharField()


class WeeklyTrendSerializer(serializers.Serializer):
    """Serializer for weekly trend data"""
    week_start = serializers.CharField()
    week_end = serializers.CharField()
    week_label = serializers.CharField()
    orders_created = serializers.IntegerField()
    orders_completed = serializers.IntegerField()
    revenue = serializers.CharField()
    formatted_revenue = serializers.CharField()


class AnalyticsPeriodSerializer(serializers.Serializer):
    """Serializer for analytics period info"""
    daily_earnings_days = serializers.IntegerField()
    weekly_trends_weeks = serializers.IntegerField()
    generated_at = serializers.CharField()


class TailorAnalyticsSerializer(serializers.Serializer):
    """Comprehensive tailor analytics serializer"""
    total_revenue = serializers.CharField()
    formatted_total_revenue = serializers.CharField()
    completed_orders_count = serializers.IntegerField()
    total_orders_count = serializers.IntegerField()
    completion_percentage = serializers.FloatField()
    formatted_completion_percentage = serializers.CharField()
    daily_earnings = DailyEarningsSerializer(many=True)
    weekly_trends = WeeklyTrendSerializer(many=True)
    analytics_period = AnalyticsPeriodSerializer()

