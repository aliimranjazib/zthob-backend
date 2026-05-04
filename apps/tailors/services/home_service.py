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
    def get_dashboard_data(tailor_user, language='ar'):
        """
        Get action-oriented dashboard data for a tailor.
        """
        from zthob.translations import translate_message
        
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
                'today_label': translate_message("Today's Revenue", language),
                'weekly_revenue': str(stats['rev_week'] or Decimal('0.00')),
                'weekly_label': translate_message("Weekly Revenue", language),
            },
            'urgent_alerts': [
                {
                    'key': 'overdue',
                    'type': 'overdue', 
                    'label': translate_message("{count} Overdue", language, count=stats['overdue']), 
                    'count': stats['overdue'], 
                    'filter_params': {'is_overdue': 'true'}
                },
                {
                    'key': 'due_today',
                    'type': 'due_today', 
                    'label': translate_message("Due Today ({count})", language, count=stats['due_today']), 
                    'count': stats['due_today'], 
                    'filter_params': {'delivery_due': 'today'}
                },
                {
                    'key': 'due_week',
                    'type': 'due_week', 
                    'label': translate_message("Due this Week ({count})", language, count=stats['due_week']), 
                    'count': stats['due_week'], 
                    'filter_params': {'delivery_due': 'week'}
                }
            ],
            'delivery_orders': [
                {
                    'key': 'del_new',
                    'label': translate_message("New Requests", language), 
                    'description': translate_message("Accept new delivery orders", language), 
                    'count': stats['del_new'], 
                    'filter_params': {'service_mode': 'home_delivery', 'tailor_status': 'none'}
                },
                {
                    'key': 'del_prepare',
                    'label': translate_message("Make Progress", language), 
                    'description': translate_message("Ready for processing", language), 
                    'count': stats['del_prepare'], 
                    'filter_params': {'service_mode': 'home_delivery', 'tailor_status': 'accepted'}
                },
                {
                    'key': 'del_stitch',
                    'label': translate_message("Stitching", language), 
                    'description': translate_message("Sewing and finishing", language), 
                    'count': stats['del_stitch'], 
                    'filter_params': {'service_mode': 'home_delivery', 'in_stitching': 'true'}
                },
                {
                    'key': 'del_ready',
                    'label': translate_message("Ready for Rider", language), 
                    'description': translate_message("Waiting for rider handover", language), 
                    'count': stats['del_ready'], 
                    'filter_params': {'service_mode': 'home_delivery', 'status': 'ready_for_delivery'}
                }
            ],
            'shop_orders': [
                {
                    'key': 'shop_new',
                    'label': translate_message("New Shop Orders", language), 
                    'description': translate_message("Accept walk-in customers", language), 
                    'count': stats['shop_new'], 
                    'filter_params': {'service_mode': 'walk_in', 'tailor_status': 'none'}
                },
                {
                    'key': 'shop_measure',
                    'label': translate_message("To Measure", language), 
                    'description': translate_message("Record shop measurements", language), 
                    'count': stats['shop_measure'], 
                    'filter_params': {'service_mode': 'walk_in', 'order_type': 'measurement_service', 'tailor_status': 'accepted'}
                },
                {
                    'key': 'shop_stitch',
                    'label': translate_message("Stitching", language), 
                    'description': translate_message("Shop orders being sewn", language), 
                    'count': stats['shop_stitch'], 
                    'filter_params': {'service_mode': 'walk_in', 'in_stitching': 'true'}
                },
                {
                    'key': 'shop_ready',
                    'label': translate_message("Ready for Customer", language), 
                    'description': translate_message("Waiting for shop collection", language), 
                    'count': stats['shop_ready'], 
                    'filter_params': {'service_mode': 'walk_in', 'status': 'ready_for_pickup'}
                }
            ],
            'express_orders': {
                'total_count': stats['exp_total'],
                'filter_params': {'status': 'express'},
                'items': express_list
            },
            'recent_orders': recent_orders
        }
