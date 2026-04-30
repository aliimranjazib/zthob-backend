from decimal import Decimal
from django.db.models import Count, Sum, Q
from django.utils import timezone
from apps.orders.models import Order

class TailorHomeService:
    """
    Service to provide action-oriented aggregated data for the Tailor Dashboard Home.
    Separates Delivery Orders and Shop Orders into distinct action-based sections.
    """
    
    @staticmethod
    def get_dashboard_data(tailor_user):
        """
        Get action-oriented dashboard data for a tailor.
        """
        now = timezone.now()
        today = now.date()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timezone.timedelta(days=now.weekday())
        week_end = today + timezone.timedelta(days=7)
        
        # Define base filters
        active_filter = Q(tailor=tailor_user, payment_status='paid')
        not_final_filter = ~Q(status__in=['delivered', 'collected', 'cancelled'])
        not_ready_filter = ~Q(status__in=['ready_for_delivery', 'ready_for_pickup', 'delivered', 'collected', 'cancelled'])
        
        # Aggregate all stats in a single query
        stats = Order.objects.filter(active_filter).aggregate(
            # Financials
            rev_today=Sum('total_amount', filter=Q(status__in=['delivered', 'collected'], updated_at__gte=today_start)),
            rev_week=Sum('total_amount', filter=Q(status__in=['delivered', 'collected'], updated_at__gte=week_start)),
            
            # Alerts
            overdue=Count('id', filter=Q(estimated_delivery_date__lt=today) & not_final_filter),
            due_today=Count('id', filter=Q(estimated_delivery_date=today) & not_final_filter),
            due_week=Count('id', filter=Q(estimated_delivery_date__gte=today, estimated_delivery_date__lte=week_end) & not_final_filter),
            
            # --- DELIVERY ORDERS ACTION BUCKETS ---
            del_new=Count('id', filter=Q(service_mode='home_delivery', tailor_status='none') & not_ready_filter),
            del_prepare=Count('id', filter=Q(service_mode='home_delivery', tailor_status='accepted', order_type='fabric_with_stitching') & not_ready_filter),
            del_stitch=Count('id', filter=Q(service_mode='home_delivery', tailor_status__in=['in_progress', 'stitching_started', 'stitched']) & not_ready_filter),
            del_ready=Count('id', filter=Q(service_mode='home_delivery', status='ready_for_delivery')),
            
            # --- SHOP ORDERS ACTION BUCKETS ---
            shop_new=Count('id', filter=Q(service_mode='walk_in', tailor_status='none') & not_ready_filter),
            shop_measure=Count('id', filter=Q(service_mode='walk_in', tailor_status='accepted', order_type='measurement_service') & not_ready_filter),
            shop_stitch=Count('id', filter=Q(service_mode='walk_in', tailor_status__in=['accepted', 'in_progress', 'stitching_started', 'stitched'], order_type='fabric_with_stitching') & not_ready_filter),
            shop_ready=Count('id', filter=Q(service_mode='walk_in', status='ready_for_pickup')),
            
            # Express count
            exp_total=Count('id', filter=Q(is_express=True) & not_final_filter)
        )
        
        # Recent & Express lists
        express_list = Order.objects.filter(active_filter & Q(is_express=True) & not_final_filter).select_related('customer').order_by('-created_at')[:5]
        recent_orders = Order.objects.filter(active_filter).select_related('customer').order_by('-updated_at')[:10]
        
        return {
            'financials': {
                'today_revenue': str(stats['rev_today'] or Decimal('0.00')),
                'weekly_revenue': str(stats['rev_week'] or Decimal('0.00'))
            },
            'urgent_alerts': [
                {'type': 'overdue', 'label': f"{stats['overdue']} Overdue", 'count': stats['overdue'], 'filter_params': {'is_overdue': 'true'}},
                {'type': 'due_today', 'label': f"Due Today ({stats['due_today']})", 'count': stats['due_today'], 'filter_params': {'delivery_due': 'today'}},
                {'type': 'due_week', 'label': f"Due this Week ({stats['due_week']})", 'count': stats['due_week'], 'filter_params': {'delivery_due': 'week'}}
            ],
            'delivery_orders': [
                {'label': 'New Requests', 'description': 'Accept new delivery orders', 'count': stats['del_new'], 'filter_params': {'service_mode': 'home_delivery', 'tailor_status': 'none'}},
                {'label': 'To Prepare', 'description': 'Ready for processing', 'count': stats['del_prepare'], 'filter_params': {'service_mode': 'home_delivery', 'tailor_status': 'accepted'}},
                {'label': 'In Stitching', 'description': 'Sewing and finishing', 'count': stats['del_stitch'], 'filter_params': {'service_mode': 'home_delivery', 'in_stitching': 'true'}},
                {'label': 'Ready for Rider', 'description': 'Waiting for rider handover', 'count': stats['del_ready'], 'filter_params': {'service_mode': 'home_delivery', 'status': 'ready_for_delivery'}}
            ],
            'shop_orders': [
                {'label': 'New Shop Orders', 'description': 'Accept walk-in customers', 'count': stats['shop_new'], 'filter_params': {'service_mode': 'walk_in', 'tailor_status': 'none'}},
                {'label': 'To Measure', 'description': 'Record shop measurements', 'count': stats['shop_measure'], 'filter_params': {'service_mode': 'walk_in', 'order_type': 'measurement_service', 'tailor_status': 'accepted'}},
                {'label': 'In Stitching', 'description': 'Shop orders being sewn', 'count': stats['shop_stitch'], 'filter_params': {'service_mode': 'walk_in', 'in_stitching': 'true'}},
                {'label': 'Ready for Customer', 'description': 'Waiting for shop collection', 'count': stats['shop_ready'], 'filter_params': {'service_mode': 'walk_in', 'status': 'ready_for_pickup'}}
            ],
            'express_orders': {
                'total_count': stats['exp_total'],
                'filter_params': {'status': 'express'},
                'items': express_list
            },
            'recent_orders': recent_orders
        }
