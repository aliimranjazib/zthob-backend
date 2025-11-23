"""
Tailor Analytics Service
Provides comprehensive analytics for tailors including revenue, orders, and trends
"""
from decimal import Decimal
from datetime import datetime, timedelta
from django.db.models import Sum, Count, Q, Avg
from django.utils import timezone
from django.contrib.auth import get_user_model
from apps.orders.models import Order

User = get_user_model()


class TailorAnalyticsService:
    """
    Service class for calculating tailor analytics and statistics.
    Provides methods for revenue, order completion, and trend analysis.
    """
    
    @staticmethod
    def get_tailor_orders(tailor_user, status_filter=None):
        """
        Get orders for a specific tailor with optional status filter.
        
        Args:
            tailor_user: User instance with TAILOR role
            status_filter: Optional status filter (e.g., 'delivered', 'pending')
        
        Returns:
            QuerySet of Order objects
        """
        queryset = Order.objects.filter(tailor=tailor_user)
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset.select_related('customer', 'delivery_address')
    
    @staticmethod
    def calculate_total_revenue(tailor_user):
        """
        Calculate total revenue from all delivered orders.
        
        Args:
            tailor_user: User instance with TAILOR role
        
        Returns:
            Decimal: Total revenue from delivered orders
        """
        delivered_orders = TailorAnalyticsService.get_tailor_orders(
            tailor_user, 
            status_filter='delivered'
        )
        
        total_revenue = delivered_orders.aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0.00')
        
        return total_revenue
    
    @staticmethod
    def calculate_daily_earnings(tailor_user, days=30):
        """
        Calculate daily earnings breakdown for the last N days.
        
        Args:
            tailor_user: User instance with TAILOR role
            days: Number of days to look back (default: 30)
        
        Returns:
            List of dicts with date and earnings
        """
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        delivered_orders = TailorAnalyticsService.get_tailor_orders(
            tailor_user,
            status_filter='delivered'
        ).filter(
            actual_delivery_date__gte=start_date,
            actual_delivery_date__lte=end_date
        )
        
        # Group by date and sum earnings
        daily_data = {}
        for order in delivered_orders:
            delivery_date = order.actual_delivery_date or order.created_at.date()
            if delivery_date not in daily_data:
                daily_data[delivery_date] = Decimal('0.00')
            daily_data[delivery_date] += order.total_amount
        
        # Fill in missing dates with zero earnings
        result = []
        current_date = start_date
        while current_date <= end_date:
            earnings = daily_data.get(current_date, Decimal('0.00'))
            result.append({
                'date': current_date.isoformat(),
                'earnings': str(earnings),
                'formatted_earnings': f"{earnings:.2f}"
            })
            current_date += timedelta(days=1)
        
        return result
    
    @staticmethod
    def get_completed_orders_count(tailor_user):
        """
        Get total count of completed (delivered) orders.
        
        Args:
            tailor_user: User instance with TAILOR role
        
        Returns:
            int: Count of delivered orders
        """
        return TailorAnalyticsService.get_tailor_orders(
            tailor_user,
            status_filter='delivered'
        ).count()
    
    @staticmethod
    def get_total_orders_count(tailor_user):
        """
        Get total count of all orders (excluding cancelled).
        
        Args:
            tailor_user: User instance with TAILOR role
        
        Returns:
            int: Count of all non-cancelled orders
        """
        return TailorAnalyticsService.get_tailor_orders(
            tailor_user
        ).exclude(status='cancelled').count()
    
    @staticmethod
    def calculate_completion_percentage(tailor_user):
        """
        Calculate completion percentage (delivered / total orders).
        
        Args:
            tailor_user: User instance with TAILOR role
        
        Returns:
            dict: Completion percentage and counts
        """
        total_orders = TailorAnalyticsService.get_total_orders_count(tailor_user)
        completed_orders = TailorAnalyticsService.get_completed_orders_count(tailor_user)
        
        if total_orders == 0:
            percentage = Decimal('0.00')
        else:
            percentage = (Decimal(completed_orders) / Decimal(total_orders)) * Decimal('100')
        
        return {
            'completed_orders': completed_orders,
            'total_orders': total_orders,
            'completion_percentage': float(percentage.quantize(Decimal('0.01'))),
            'formatted_percentage': f"{percentage:.2f}%"
        }
    
    @staticmethod
    def get_weekly_order_trends(tailor_user, weeks=12):
        """
        Get weekly order trends for the last N weeks.
        
        Args:
            tailor_user: User instance with TAILOR role
            weeks: Number of weeks to look back (default: 12)
        
        Returns:
            List of dicts with week info and order counts
        """
        end_date = timezone.now()
        start_date = end_date - timedelta(weeks=weeks)
        
        orders = TailorAnalyticsService.get_tailor_orders(tailor_user).filter(
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
                    'orders_created': 0,
                    'orders_completed': 0,
                    'revenue': Decimal('0.00')
                }
            
            weekly_data[week_start]['orders_created'] += 1
            
            if order.status == 'delivered':
                weekly_data[week_start]['orders_completed'] += 1
                weekly_data[week_start]['revenue'] += order.total_amount
        
        # Build result list
        result = []
        current_week_start = start_date.date()
        
        # Find the Monday of the week containing start_date
        days_since_monday = current_week_start.weekday()
        current_week_start = current_week_start - timedelta(days=days_since_monday)
        
        while current_week_start <= end_date.date():
            week_end = current_week_start + timedelta(days=6)
            week_data = weekly_data.get(current_week_start, {
                'orders_created': 0,
                'orders_completed': 0,
                'revenue': Decimal('0.00')
            })
            
            result.append({
                'week_start': current_week_start.isoformat(),
                'week_end': week_end.isoformat(),
                'week_label': f"{current_week_start.strftime('%b %d')} - {week_end.strftime('%b %d, %Y')}",
                'orders_created': week_data['orders_created'],
                'orders_completed': week_data['orders_completed'],
                'revenue': str(week_data['revenue']),
                'formatted_revenue': f"{week_data['revenue']:.2f}"
            })
            
            current_week_start += timedelta(days=7)
        
        return result
    
    @staticmethod
    def get_comprehensive_analytics(tailor_user, days=30, weeks=12):
        """
        Get comprehensive analytics for a tailor.
        
        Args:
            tailor_user: User instance with TAILOR role
            days: Number of days for daily earnings (default: 30)
            weeks: Number of weeks for trends (default: 12)
        
        Returns:
            dict: Complete analytics data
        """
        total_revenue = TailorAnalyticsService.calculate_total_revenue(tailor_user)
        daily_earnings = TailorAnalyticsService.calculate_daily_earnings(tailor_user, days)
        completion_stats = TailorAnalyticsService.calculate_completion_percentage(tailor_user)
        weekly_trends = TailorAnalyticsService.get_weekly_order_trends(tailor_user, weeks)
        
        return {
            'total_revenue': str(total_revenue),
            'formatted_total_revenue': f"{total_revenue:.2f}",
            'completed_orders_count': completion_stats['completed_orders'],
            'total_orders_count': completion_stats['total_orders'],
            'completion_percentage': completion_stats['completion_percentage'],
            'formatted_completion_percentage': completion_stats['formatted_percentage'],
            'daily_earnings': daily_earnings,
            'weekly_trends': weekly_trends,
            'analytics_period': {
                'daily_earnings_days': days,
                'weekly_trends_weeks': weeks,
                'generated_at': timezone.now().isoformat()
            }
        }

