from decimal import Decimal
from django.db.models import Count, Sum, Q
from django.utils import timezone
from apps.orders.models import Order

class TailorHomeService:
    """
    Service to provide aggregated data for the Tailor Dashboard Home.
    """
    
    @staticmethod
    def get_dashboard_data(tailor_user):
        """
        Get aggregated dashboard data for a tailor.
        Uses single queries and optimized lookups to ensure performance.
        """
        now = timezone.now()
        today = now.date()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timezone.timedelta(days=now.weekday())
        
        # 1. Fetch counts and sums in a single efficient aggregation query
        # Filter by tailor_user to keep it scoped to the authenticated tailor
        stats = Order.objects.filter(tailor=tailor_user, payment_status='paid').aggregate(
            # Financials
            revenue_today=Sum('total_amount', filter=Q(status__in=['delivered', 'collected'], updated_at__gte=today_start)),
            revenue_week=Sum('total_amount', filter=Q(status__in=['delivered', 'collected'], updated_at__gte=week_start)),
            
            # Urgent Alerts
            overdue_count=Count('id', filter=Q(estimated_delivery_date__lt=today) & ~Q(status__in=['delivered', 'collected', 'cancelled'])),
            due_today_count=Count('id', filter=Q(estimated_delivery_date=today) & ~Q(status__in=['delivered', 'collected', 'cancelled'])),
            
            # Task Summary
            needs_acceptance=Count('id', filter=Q(status='pending')),
            ready_to_stitch=Count('id', filter=Q(status='confirmed', tailor_status='accepted')),
            stitching_count=Count('id', filter=Q(tailor_status='stitching_started')),
            
            # Express total for the badge
            express_total=Count('id', filter=Q(is_express=True) & ~Q(status__in=['delivered', 'collected', 'cancelled']))
        )
        
        # 2. Fetch High-Priority Express Orders (Only Paid)
        express_list = Order.objects.filter(
            tailor=tailor_user,
            is_express=True,
            payment_status='paid'
        ).exclude(
            status__in=['delivered', 'collected', 'cancelled']
        ).select_related('customer').order_by('-created_at')[:5]
        
        # 3. Recent Activity (Last 10 Paid Orders)
        recent_orders = Order.objects.filter(
            tailor=tailor_user,
            payment_status='paid'
        ).select_related('customer').order_by('-updated_at')[:10]
        
        return {
            'financials': {
                'today_revenue': str(stats['revenue_today'] or Decimal('0.00')),
                'weekly_revenue': str(stats['revenue_week'] or Decimal('0.00'))
            },
            'urgent_alerts': [
                {
                    'type': 'overdue',
                    'label': f"{stats['overdue_count']} Order Overdue" if stats['overdue_count'] == 1 else f"{stats['overdue_count']} Orders Overdue",
                    'count': stats['overdue_count'] or 0,
                    'filter_params': {'is_overdue': 'true'}
                },
                {
                    'type': 'due_today',
                    'label': f"{stats['due_today_count']} Order Due Today" if stats['due_today_count'] == 1 else f"{stats['due_today_count']} Orders Due Today",
                    'count': stats['due_today_count'] or 0,
                    'filter_params': {'delivery_due': 'today'}
                }
            ],
            'task_summary': [
                {
                    'label': 'Needs Acceptance',
                    'count': stats['needs_acceptance'] or 0,
                    'filter_params': {'status': 'pending'}
                },
                {
                    'label': 'Ready to Stitch',
                    'count': stats['ready_to_stitch'] or 0,
                    'filter_params': {'status': 'confirmed', 'tailor_status': 'accepted'}
                },
                {
                    'label': 'Currently Stitching',
                    'count': stats['stitching_count'] or 0,
                    'filter_params': {'tailor_status': 'stitching_started'}
                }
            ],
            'express_orders': {
                'total_count': stats['express_total'] or 0,
                'filter_params': {'status': 'express'},
                'items': express_list
            },
            'recent_orders': recent_orders
        }
