"""
Rider Analytics Service
Provides comprehensive analytics for riders including deliveries, completion rates, and trends
"""
from decimal import Decimal
from datetime import datetime, timedelta
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.contrib.auth import get_user_model
from apps.orders.models import Order

User = get_user_model()


class RiderAnalyticsService:
    """
    Service class for calculating rider analytics and statistics.
    Provides methods for delivery completion, order tracking, and trend analysis.
    """
    
    @staticmethod
    def get_rider_orders(rider_user, status_filter=None):
        """
        Get orders assigned to a specific rider with optional status filter.
        
        Args:
            rider_user: User instance with RIDER role
            status_filter: Optional status filter (e.g., 'delivered', 'pending')
        
        Returns:
            QuerySet of Order objects
        """
        queryset = Order.objects.filter(rider=rider_user)
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset.select_related('customer', 'tailor', 'delivery_address')
    
    @staticmethod
    def get_completed_deliveries_count(rider_user):
        """
        Get total count of completed deliveries (delivered orders).
        
        Args:
            rider_user: User instance with RIDER role
        
        Returns:
            int: Count of delivered orders
        """
        return RiderAnalyticsService.get_rider_orders(
            rider_user,
            status_filter='delivered'
        ).count()
    
    @staticmethod
    def get_total_orders_count(rider_user):
        """
        Get total count of all orders assigned to rider (excluding cancelled).
        
        Args:
            rider_user: User instance with RIDER role
        
        Returns:
            int: Count of all non-cancelled assigned orders
        """
        return RiderAnalyticsService.get_rider_orders(
            rider_user
        ).exclude(status='cancelled').count()
    
    @staticmethod
    def calculate_completion_percentage(rider_user):
        """
        Calculate completion percentage (delivered / total orders).
        
        Args:
            rider_user: User instance with RIDER role
        
        Returns:
            dict: Completion percentage and counts
        """
        total_orders = RiderAnalyticsService.get_total_orders_count(rider_user)
        completed_deliveries = RiderAnalyticsService.get_completed_deliveries_count(rider_user)
        
        if total_orders == 0:
            percentage = Decimal('0.00')
        else:
            percentage = (Decimal(completed_deliveries) / Decimal(total_orders)) * Decimal('100')
        
        return {
            'completed_deliveries': completed_deliveries,
            'total_orders': total_orders,
            'completion_percentage': float(percentage.quantize(Decimal('0.01'))),
            'formatted_percentage': f"{percentage:.2f}%"
        }
    
    @staticmethod
    def calculate_total_delivery_fees(rider_user):
        """
        Calculate total delivery fees from all delivered orders.
        This represents potential earnings from deliveries.
        
        Args:
            rider_user: User instance with RIDER role
        
        Returns:
            Decimal: Total delivery fees from delivered orders
        """
        delivered_orders = RiderAnalyticsService.get_rider_orders(
            rider_user,
            status_filter='delivered'
        )
        
        total_fees = delivered_orders.aggregate(
            total=Sum('delivery_fee')
        )['total'] or Decimal('0.00')
        
        return total_fees
    
    @staticmethod
    def calculate_daily_deliveries(rider_user, days=30):
        """
        Calculate daily deliveries breakdown for the last N days.
        
        Args:
            rider_user: User instance with RIDER role
            days: Number of days to look back (default: 30)
        
        Returns:
            List of dicts with date and delivery count
        """
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        delivered_orders = RiderAnalyticsService.get_rider_orders(
            rider_user,
            status_filter='delivered'
        ).filter(
            actual_delivery_date__gte=start_date,
            actual_delivery_date__lte=end_date
        )
        
        # Group by date and count deliveries
        daily_data = {}
        for order in delivered_orders:
            delivery_date = order.actual_delivery_date or order.created_at.date()
            if delivery_date not in daily_data:
                daily_data[delivery_date] = {
                    'count': 0,
                    'delivery_fees': Decimal('0.00')
                }
            daily_data[delivery_date]['count'] += 1
            daily_data[delivery_date]['delivery_fees'] += order.delivery_fee
        
        # Fill in missing dates with zero deliveries
        result = []
        current_date = start_date
        while current_date <= end_date:
            day_data = daily_data.get(current_date, {
                'count': 0,
                'delivery_fees': Decimal('0.00')
            })
            result.append({
                'date': current_date.isoformat(),
                'deliveries_count': day_data['count'],
                'delivery_fees': str(day_data['delivery_fees']),
                'formatted_delivery_fees': f"{day_data['delivery_fees']:.2f}"
            })
            current_date += timedelta(days=1)
        
        return result
    
    @staticmethod
    def get_weekly_delivery_trends(rider_user, weeks=12):
        """
        Get weekly delivery trends for the last N weeks.
        
        Args:
            rider_user: User instance with RIDER role
            weeks: Number of weeks to look back (default: 12)
        
        Returns:
            List of dicts with week info and delivery counts
        """
        end_date = timezone.now()
        start_date = end_date - timedelta(weeks=weeks)
        
        orders = RiderAnalyticsService.get_rider_orders(rider_user).filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        ).exclude(status='cancelled')
        
        # Group orders by week
        weekly_data = {}
        for order in orders:
            # Get the Monday of the week for this order
            order_date = order.created_at.date()
            days_since_monday = order_date.weekday()
            week_start = order_date - timedelta(days=days_since_monday)
            
            if week_start not in weekly_data:
                weekly_data[week_start] = {
                    'orders_assigned': 0,
                    'deliveries_completed': 0,
                    'delivery_fees': Decimal('0.00')
                }
            
            weekly_data[week_start]['orders_assigned'] += 1
            
            if order.status == 'delivered':
                weekly_data[week_start]['deliveries_completed'] += 1
                weekly_data[week_start]['delivery_fees'] += order.delivery_fee
        
        # Build result list
        result = []
        current_week_start = start_date.date()
        
        # Find the Monday of the week containing start_date
        days_since_monday = current_week_start.weekday()
        current_week_start = current_week_start - timedelta(days=days_since_monday)
        
        while current_week_start <= end_date.date():
            week_end = current_week_start + timedelta(days=6)
            week_data = weekly_data.get(current_week_start, {
                'orders_assigned': 0,
                'deliveries_completed': 0,
                'delivery_fees': Decimal('0.00')
            })
            
            result.append({
                'week_start': current_week_start.isoformat(),
                'week_end': week_end.isoformat(),
                'week_label': f"{current_week_start.strftime('%b %d')} - {week_end.strftime('%b %d, %Y')}",
                'orders_assigned': week_data['orders_assigned'],
                'deliveries_completed': week_data['deliveries_completed'],
                'delivery_fees': str(week_data['delivery_fees']),
                'formatted_delivery_fees': f"{week_data['delivery_fees']:.2f}"
            })
            
            current_week_start += timedelta(days=7)
        
        return result
    
    @staticmethod
    def get_comprehensive_analytics(rider_user, days=30, weeks=12):
        """
        Get comprehensive analytics for a rider.
        
        Args:
            rider_user: User instance with RIDER role
            days: Number of days for daily deliveries (default: 30)
            weeks: Number of weeks for trends (default: 12)
        
        Returns:
            dict: Complete analytics data
        """
        total_delivery_fees = RiderAnalyticsService.calculate_total_delivery_fees(rider_user)
        daily_deliveries = RiderAnalyticsService.calculate_daily_deliveries(rider_user, days)
        completion_stats = RiderAnalyticsService.calculate_completion_percentage(rider_user)
        weekly_trends = RiderAnalyticsService.get_weekly_delivery_trends(rider_user, weeks)
        
        return {
            'total_delivery_fees': str(total_delivery_fees),
            'formatted_total_delivery_fees': f"{total_delivery_fees:.2f}",
            'completed_deliveries_count': completion_stats['completed_deliveries'],
            'total_orders_count': completion_stats['total_orders'],
            'completion_percentage': completion_stats['completion_percentage'],
            'formatted_completion_percentage': completion_stats['formatted_percentage'],
            'daily_deliveries': daily_deliveries,
            'weekly_trends': weekly_trends,
            'analytics_period': {
                'daily_deliveries_days': days,
                'weekly_trends_weeks': weeks,
                'generated_at': timezone.now().isoformat()
            }
        }

