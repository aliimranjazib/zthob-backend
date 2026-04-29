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
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 1. Fetch counts in a single efficient aggregation query
        # Filter by tailor_user to keep it scoped to the authenticated tailor
        stats = Order.objects.filter(tailor=tailor_user).aggregate(
            # Main Summary: Any paid order is a valid order for the tailor
            new_orders=Count('id', filter=Q(payment_status='paid', status__in=['pending', 'confirmed'])),
            in_progress=Count('id', filter=Q(payment_status='paid', status='in_progress')),
            ready_orders=Count('id', filter=Q(payment_status='paid', status__in=['ready_for_delivery', 'ready_for_pickup'])),
            express_orders=Count('id', filter=Q(payment_status='paid', is_express=True).exclude(status__in=['delivered', 'collected', 'cancelled'])),
            revenue_today=Sum('total_amount', filter=Q(payment_status='paid', status__in=['delivered', 'collected'], updated_at__gte=today_start)),
            
            # Pipeline Breakdown (Granular stages)
            new_count=Count('id', filter=Q(payment_status='paid', status='pending')),
            waiting_to_start=Count('id', filter=Q(payment_status='paid', tailor_status='accepted', status='confirmed')),
            stitching=Count('id', filter=Q(payment_status='paid', tailor_status='stitching_started')),
            stitched=Count('id', filter=Q(payment_status='paid', tailor_status='stitched')),
            ready_for_pickup=Count('id', filter=Q(payment_status='paid', status='ready_for_pickup')),
            ready_for_delivery=Count('id', filter=Q(payment_status='paid', status='ready_for_delivery'))
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
        
        # 4. Shop Status Info
        is_open = False
        profile_completeness = 0
        
        if hasattr(tailor_user, 'tailor_profile'):
            profile = tailor_user.tailor_profile
            is_open = profile.shop_status
            
            # Detailed completeness calculation with hints
            checks = [
                (profile.shop_name, "Shop Name"),
                (profile.contact_number or tailor_user.phone, "Contact Number"),
                (profile.address, "Business Address"),
                (profile.shop_image, "Shop Image"),
                (profile.working_hours, "Working Hours"),
            ]
            
            missing_hints = [hint for val, hint in checks if not val]
            total_checks = len(checks)
            filled_count = total_checks - len(missing_hints)
            profile_completeness = int((filled_count / total_checks) * 100)
            
        return {
            'counters': {
                'new_orders': stats['new_orders'] or 0,
                'in_progress': stats['in_progress'] or 0,
                'ready_for_delivery': stats['ready_orders'] or 0,
                'express_orders': stats['express_orders'] or 0,
                'revenue_today': str(stats['revenue_today'] or Decimal('0.00'))
            },
            'pipeline': {
                'new': stats['new_orders'] or 0,
                'waiting_to_start': stats['waiting_to_start'] or 0,
                'stitching': stats['stitching'] or 0,
                'stitched': stats['stitched'] or 0,
                'ready_for_pickup': stats['waiting_for_pickup'] or 0,
                'ready_for_delivery': stats['waiting_for_delivery'] or 0
            },
            'express_orders': express_list,
            'recent_orders': recent_orders,
            'shop_status': {
                'is_open': is_open,
                'profile_completeness': profile_completeness,
            },
            'missing_hints': missing_hints
        }
