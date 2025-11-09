from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Sum, Count, Q
from django.contrib import messages
from django.http import HttpResponse
import csv
from datetime import datetime
from .models import Order, OrderItem, OrderStatusHistory


# ============================================================================
# INLINE ADMIN CLASSES
# ============================================================================

class OrderItemInline(admin.TabularInline):
    """Inline admin for OrderItems - shows items directly in Order detail view"""
    model = OrderItem
    extra = 0
    readonly_fields = ['total_price', 'created_at', 'updated_at']
    fields = [
        'fabric', 
        'quantity', 
        'unit_price', 
        'total_price', 
        'is_ready',
        'created_at'
    ]
    can_delete = True
    show_change_link = True
    
    def has_add_permission(self, request, obj=None):
        """Allow adding items only if order is not delivered/cancelled"""
        if obj:
            return obj.status not in ['delivered', 'cancelled']
        return True
    
    def has_delete_permission(self, request, obj=None):
        """Allow deleting items only if order is pending"""
        if obj:
            return obj.status == 'pending'
        return True


class OrderStatusHistoryInline(admin.TabularInline):
    """Inline admin for OrderStatusHistory - shows status change history"""
    model = OrderStatusHistory
    extra = 0
    readonly_fields = ['status', 'previous_status', 'changed_by', 'notes', 'created_at']
    fields = ['status', 'previous_status', 'changed_by', 'notes', 'created_at']
    can_delete = False
    max_num = 0  # Read-only, no adding new history records from admin
    
    def has_add_permission(self, request, obj=None):
        return False


# ============================================================================
# CUSTOM FILTERS
# ============================================================================

class OrderStatusFilter(admin.SimpleListFilter):
    """Custom filter for order status with grouping"""
    title = 'Order Status'
    parameter_name = 'status_group'
    
    def lookups(self, request, model_admin):
        return (
            ('active', 'Active Orders'),
            ('pending', 'Pending Confirmation'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled'),
        )
    
    def queryset(self, request, queryset):
        if self.value() == 'active':
            return queryset.exclude(status__in=['delivered', 'cancelled'])
        elif self.value() == 'pending':
            return queryset.filter(status='pending')
        elif self.value() == 'in_progress':
            return queryset.filter(status__in=['confirmed', 'measuring', 'cutting', 'stitching', 'ready_for_delivery'])
        elif self.value() == 'completed':
            return queryset.filter(status='delivered')
        elif self.value() == 'cancelled':
            return queryset.filter(status='cancelled')


class PaymentStatusFilter(admin.SimpleListFilter):
    """Custom filter for payment status"""
    title = 'Payment Status'
    parameter_name = 'payment_status'
    
    def lookups(self, request, model_admin):
        return (
            ('pending', 'Pending Payment'),
            ('paid', 'Paid'),
            ('refunded', 'Refunded'),
        )
    
    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(payment_status=self.value())


class HighValueOrderFilter(admin.SimpleListFilter):
    """Filter for high-value orders"""
    title = 'Order Value'
    parameter_name = 'order_value'
    
    def lookups(self, request, model_admin):
        return (
            ('high', 'High Value (>$500)'),
            ('medium', 'Medium Value ($100-$500)'),
            ('low', 'Low Value (<$100)'),
        )
    
    def queryset(self, request, queryset):
        if self.value() == 'high':
            return queryset.filter(total_amount__gte=500)
        elif self.value() == 'medium':
            return queryset.filter(total_amount__gte=100, total_amount__lt=500)
        elif self.value() == 'low':
            return queryset.filter(total_amount__lt=100)


# ============================================================================
# ORDER ADMIN
# ============================================================================

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """
    Professional Order Admin Interface
    
    Features:
    - Inline OrderItems and Status History
    - Custom display methods with formatting
    - Bulk actions for common operations
    - Advanced filtering and search
    - Export functionality
    - Date hierarchy for time-based navigation
    """
    
    # List Display Configuration
    list_display = [
        'order_number_link',
        'customer_info',
        'tailor_info',
        'order_type_display',
        'status_badge',
        'items_count_display',
        'total_amount_formatted',
        'payment_status_badge',
        'delivery_info',
        'created_at_formatted'
    ]
    
    list_display_links = ['order_number_link']
    
    # Filtering & Search
    list_filter = [
        OrderStatusFilter,
        PaymentStatusFilter,
        HighValueOrderFilter,
        'status', 
        'payment_status', 
        'payment_method',
        'order_type',
        'created_at',
    ]
    
    search_fields = [
        'order_number', 
        'customer__username', 
        'customer__email',
        'customer__phone',
        'tailor__username',
        'tailor__email',
        'family_member__name',
        'delivery_address__street',
        'delivery_address__city',
    ]
    
    date_hierarchy = 'created_at'
    
    # Inline Admins
    inlines = [OrderItemInline, OrderStatusHistoryInline]
    
    # Readonly Fields
    readonly_fields = [
        'order_number',
        'created_at',
        'updated_at',
        'created_by',
        'items_count_display',
        'total_amount_formatted',
        'status_history_link',
    ]
    
    # Fieldsets - Organized for better UX
    fieldsets = (
        ('Order Information', {
            'fields': (
                'order_number',
                'customer',
                'family_member',
                'tailor',
                'order_type',
                'status',
            ),
            'classes': ('wide',)
        }),
        ('Financial Summary', {
            'fields': (
                'items_count_display',
                'subtotal',
                'tax_amount',
                'delivery_fee',
                'total_amount_formatted',
            ),
            'classes': ('wide',)
        }),
        ('Payment Information', {
            'fields': (
                'payment_status',
                'payment_method',
            )
        }),
        ('Delivery Information', {
            'fields': (
                'delivery_address',
                'estimated_delivery_date',
                'actual_delivery_date',
            )
        }),
        ('Additional Information', {
            'fields': (
                'special_instructions',
                'notes',
            ),
            'classes': ('collapse',)
        }),
        ('Audit Information', {
            'fields': (
                'status_history_link',
                'created_by',
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',)
        }),
    )
    
    # Pagination
    list_per_page = 50
    list_max_show_all = 500
    
    # Actions
    actions = [
        'mark_as_confirmed',
        'mark_as_ready_for_delivery',
        'mark_as_delivered',
        'mark_payment_as_paid',
        'export_orders_csv',
        'recalculate_totals',
    ]
    
    # Custom Display Methods
    def order_number_link(self, obj):
        """Clickable order number linking to detail view"""
        if obj.pk:
            try:
                url = reverse('admin:orders_order_change', args=[obj.pk])
                return format_html('<a href="{}">{}</a>', url, obj.order_number or 'No number')
            except Exception:
                return obj.order_number or 'No number'
        return obj.order_number or 'No number'
    order_number_link.short_description = 'Order Number'
    order_number_link.admin_order_field = 'order_number'
    
    def customer_info(self, obj):
        """Display customer information with link"""
        if obj.customer and obj.customer.pk:
            try:
                url = reverse('admin:accounts_customuser_change', args=[obj.customer.pk])
                email = obj.customer.email or 'No email'
                username = obj.customer.username or 'No username'
                return format_html(
                    '<a href="{}">{}</a><br><small>{}</small>',
                    url,
                    username,
                    email
                )
            except Exception:
                username = obj.customer.username or 'No username'
                email = obj.customer.email or 'No email'
                return format_html('{}<br><small>{}</small>', username, email)
        return '-'
    customer_info.short_description = 'Customer'
    customer_info.admin_order_field = 'customer__username'
    
    def tailor_info(self, obj):
        """Display tailor information with link"""
        if obj.tailor and obj.tailor.pk:
            try:
                url = reverse('admin:accounts_customuser_change', args=[obj.tailor.pk])
                try:
                    from apps.tailors.models import TailorProfile
                    tailor_profile = TailorProfile.objects.get(user=obj.tailor)
                    shop_name = tailor_profile.shop_name if tailor_profile.shop_name else obj.tailor.username
                except Exception:
                    # Handle DoesNotExist, AttributeError, ImportError, etc.
                    shop_name = obj.tailor.username or 'Unknown'
                return format_html(
                    '<a href="{}">{}</a>',
                    url,
                    shop_name
                )
            except Exception:
                shop_name = obj.tailor.username if obj.tailor.username else 'Unknown'
                return shop_name
        return '-'
    tailor_info.short_description = 'Tailor'
    tailor_info.admin_order_field = 'tailor__username'
    
    def order_type_display(self, obj):
        """Display order type with badge"""
        colors = {
            'fabric_only': 'blue',
            'fabric_with_stitching': 'green',
        }
        color = colors.get(obj.order_type, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.get_order_type_display()
        )
    order_type_display.short_description = 'Order Type'
    order_type_display.admin_order_field = 'order_type'
    
    def status_badge(self, obj):
        """Display status with color-coded badge"""
        colors = {
            'pending': '#ffc107',
            'confirmed': '#17a2b8',
            'measuring': '#6c757d',
            'cutting': '#6c757d',
            'stitching': '#6c757d',
            'ready_for_delivery': '#28a745',
            'delivered': '#28a745',
            'cancelled': '#dc3545',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 10px; border-radius: 4px; font-weight: 500; font-size: 11px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'
    
    def items_count_display(self, obj):
        """Display number of items in order"""
        count = obj.items_count
        return format_html(
            '<strong>{}</strong> <small>item{}</small>',
            count,
            's' if count != 1 else ''
        )
    items_count_display.short_description = 'Items'
    
    def total_amount_formatted(self, obj):
        """Display total amount with currency formatting"""
        try:
            amount = float(obj.total_amount) if obj.total_amount else 0.0
            return format_html(
                '<strong style="color: #28a745; font-size: 14px;">${:,.2f}</strong>',
                amount
            )
        except (ValueError, TypeError):
            return format_html('<em style="color: #999;">N/A</em>')
    total_amount_formatted.short_description = 'Total Amount'
    total_amount_formatted.admin_order_field = 'total_amount'
    
    def payment_status_badge(self, obj):
        """Display payment status with color-coded badge"""
        colors = {
            'pending': '#ffc107',
            'paid': '#28a745',
            'refunded': '#dc3545',
        }
        color = colors.get(obj.payment_status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 10px; border-radius: 4px; font-size: 11px;">{}</span>',
            color,
            obj.get_payment_status_display()
        )
    payment_status_badge.short_description = 'Payment'
    payment_status_badge.admin_order_field = 'payment_status'
    
    def delivery_info(self, obj):
        """Display delivery information"""
        info = []
        try:
            if obj.estimated_delivery_date:
                info.append(f'Est: {obj.estimated_delivery_date.strftime("%m/%d/%Y")}')
        except (AttributeError, ValueError):
            pass
        try:
            if obj.actual_delivery_date:
                info.append(f'Actual: {obj.actual_delivery_date.strftime("%m/%d/%Y")}')
        except (AttributeError, ValueError):
            pass
        if not info:
            return '-'
        return format_html('<br>'.join(info))
    delivery_info.short_description = 'Delivery Dates'
    
    def created_at_formatted(self, obj):
        """Display formatted creation date"""
        try:
            if obj.created_at:
                return obj.created_at.strftime('%Y-%m-%d %H:%M')
        except (AttributeError, ValueError):
            pass
        return '-'
    created_at_formatted.short_description = 'Created'
    created_at_formatted.admin_order_field = 'created_at'
    
    def status_history_link(self, obj):
        """Link to view status history"""
        if obj.pk:
            count = obj.status_history.count()
            if count > 0:
                url = reverse('admin:orders_orderstatushistory_changelist')
                url += f'?order__id__exact={obj.pk}'
                return format_html(
                    '<a href="{}">View {} status change{}</a>',
                    url,
                    count,
                    's' if count != 1 else ''
                )
        return 'No history'
    status_history_link.short_description = 'Status History'
    
    # Custom Actions
    def mark_as_confirmed(self, request, queryset):
        """Bulk action to mark orders as confirmed"""
        count = 0
        for order in queryset.filter(status='pending'):
            order.status = 'confirmed'
            order.save()
            count += 1
        self.message_user(
            request,
            f'Successfully marked {count} order(s) as confirmed.',
            messages.SUCCESS
        )
    mark_as_confirmed.short_description = 'Mark selected orders as confirmed'
    
    def mark_as_ready_for_delivery(self, request, queryset):
        """Bulk action to mark orders as ready for delivery"""
        count = 0
        allowed_statuses = ['confirmed', 'measuring', 'cutting', 'stitching']
        for order in queryset.filter(status__in=allowed_statuses):
            order.status = 'ready_for_delivery'
            order.save()
            count += 1
        self.message_user(
            request,
            f'Successfully marked {count} order(s) as ready for delivery.',
            messages.SUCCESS
        )
    mark_as_ready_for_delivery.short_description = 'Mark selected orders as ready for delivery'
    
    def mark_as_delivered(self, request, queryset):
        """Bulk action to mark orders as delivered"""
        count = 0
        for order in queryset.filter(status='ready_for_delivery'):
            order.status = 'delivered'
            if not order.actual_delivery_date:
                from django.utils import timezone
                order.actual_delivery_date = timezone.now().date()
            order.save()
            count += 1
        self.message_user(
            request,
            f'Successfully marked {count} order(s) as delivered.',
            messages.SUCCESS
        )
    mark_as_delivered.short_description = 'Mark selected orders as delivered'
    
    def mark_payment_as_paid(self, request, queryset):
        """Bulk action to mark payment status as paid"""
        count = 0
        for order in queryset.filter(payment_status='pending'):
            order.payment_status = 'paid'
            order.save()
            count += 1
        self.message_user(
            request,
            f'Successfully marked {count} order(s) payment as paid.',
            messages.SUCCESS
        )
    mark_payment_as_paid.short_description = 'Mark selected orders payment as paid'
    
    def export_orders_csv(self, request, queryset):
        """Export selected orders to CSV"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="orders_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Order Number',
            'Customer',
            'Tailor',
            'Status',
            'Payment Status',
            'Total Amount',
            'Items Count',
            'Created At',
            'Estimated Delivery',
            'Actual Delivery',
        ])
        
        for order in queryset:
            writer.writerow([
                order.order_number,
                order.customer.username if order.customer else '',
                order.tailor.username if order.tailor else '',
                order.get_status_display(),
                order.get_payment_status_display(),
                order.total_amount,
                order.items_count,
                order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                order.estimated_delivery_date.strftime('%Y-%m-%d') if order.estimated_delivery_date else '',
                order.actual_delivery_date.strftime('%Y-%m-%d') if order.actual_delivery_date else '',
            ])
        
        return response
    export_orders_csv.short_description = 'Export selected orders to CSV'
    
    def recalculate_totals(self, request, queryset):
        """Recalculate totals for selected orders"""
        count = 0
        for order in queryset:
            try:
                order.recalculate_totals()
                count += 1
            except Exception as e:
                self.message_user(
                    request,
                    f'Error recalculating totals for order {order.order_number}: {str(e)}',
                    messages.ERROR
                )
        self.message_user(
            request,
            f'Successfully recalculated totals for {count} order(s).',
            messages.SUCCESS
        )
    recalculate_totals.short_description = 'Recalculate totals for selected orders'
    
    # Override save method
    def save_model(self, request, obj, form, change):
        """Set created_by when creating new orders"""
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    # Override get_queryset for optimization
    def get_queryset(self, request):
        """Optimize queryset with select_related and prefetch_related"""
        qs = super().get_queryset(request)
        return qs.select_related(
            'customer',
            'tailor',
            'family_member',
            'delivery_address',
            'created_by'
        ).prefetch_related(
            'order_items',
            'status_history'
        )


# ============================================================================
# ORDER ITEM ADMIN
# ============================================================================

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """
    Professional OrderItem Admin Interface
    """
    
    list_display = [
        'order_link',
        'fabric_info',
        'quantity', 
        'unit_price_formatted',
        'total_price_formatted',
        'is_ready_badge',
        'created_at_formatted'
    ]
    
    list_display_links = ['order_link']
    
    list_filter = [
        'is_ready',
        'order__status',
        'order__payment_status',
        'created_at',
    ]
    
    search_fields = [
        'order__order_number', 
        'fabric__name', 
        'fabric__sku',
        'order__customer__username',
        'order__customer__email',
    ]
    
    readonly_fields = [
        'total_price',
        'created_at',
        'updated_at',
        'created_by',
    ]
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order',)
        }),
        ('Item Details', {
            'fields': (
                'fabric',
                'quantity',
                'unit_price',
                'total_price',
            )
        }),
        ('Customization', {
            'fields': (
                'measurements',
                'custom_instructions',
            ),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_ready',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    list_per_page = 50
    
    def order_link(self, obj):
        """Clickable order number"""
        if obj.order:
            url = reverse('admin:orders_order_change', args=[obj.order.pk])
            return format_html('<a href="{}">{}</a>', url, obj.order.order_number)
        return '-'
    order_link.short_description = 'Order'
    order_link.admin_order_field = 'order__order_number'
    
    def fabric_info(self, obj):
        """Display fabric information"""
        if obj.fabric:
            return format_html(
                '<strong>{}</strong><br><small>SKU: {}</small>',
                obj.fabric.name,
                getattr(obj.fabric, 'sku', 'N/A')
            )
        return '-'
    fabric_info.short_description = 'Fabric'
    
    def unit_price_formatted(self, obj):
        """Format unit price"""
        try:
            price = float(obj.unit_price) if obj.unit_price is not None else 0.0
            return f'${price:,.2f}'
        except (ValueError, TypeError):
            return 'N/A'
    unit_price_formatted.short_description = 'Unit Price'
    unit_price_formatted.admin_order_field = 'unit_price'
    
    def total_price_formatted(self, obj):
        """Format total price"""
        try:
            price = float(obj.total_price) if obj.total_price is not None else 0.0
            return format_html(
                '<strong style="color: #28a745;">${:,.2f}</strong>',
                price
            )
        except (ValueError, TypeError):
            return format_html('<em style="color: #999;">N/A</em>')
    total_price_formatted.short_description = 'Total Price'
    total_price_formatted.admin_order_field = 'total_price'
    
    def is_ready_badge(self, obj):
        """Display ready status with badge"""
        if obj.is_ready:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 4px 10px; border-radius: 4px; font-size: 11px;">Ready</span>'
            )
        return format_html(
            '<span style="background-color: #ffc107; color: white; padding: 4px 10px; border-radius: 4px; font-size: 11px;">Not Ready</span>'
        )
    is_ready_badge.short_description = 'Ready Status'
    is_ready_badge.admin_order_field = 'is_ready'
    
    def created_at_formatted(self, obj):
        """Format creation date"""
        return obj.created_at.strftime('%Y-%m-%d %H:%M')
    created_at_formatted.short_description = 'Created'
    created_at_formatted.admin_order_field = 'created_at'
    
    def save_model(self, request, obj, form, change):
        """Set created_by when creating new items"""
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        """Optimize queryset"""
        qs = super().get_queryset(request)
        return qs.select_related('order', 'fabric', 'created_by')


# ============================================================================
# ORDER STATUS HISTORY ADMIN
# ============================================================================

@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    """
    Professional OrderStatusHistory Admin Interface
    Read-only admin for audit trail
    """
    
    list_display = [
        'order_link',
        'status_transition',
        'changed_by_info',
        'notes_preview',
        'created_at_formatted'
    ]
    
    list_display_links = ['order_link']
    
    list_filter = [
        'status', 
        'previous_status', 
        'created_at',
    ]
    
    search_fields = [
        'order__order_number', 
        'changed_by__username',
        'changed_by__email',
        'notes',
    ]
    
    readonly_fields = [
        'order',
        'status',
        'previous_status',
        'changed_by',
        'notes',
        'created_at',
        'updated_at',
        'created_by',
    ]
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order',)
        }),
        ('Status Change', {
            'fields': (
                'previous_status',
                'status',
            )
        }),
        ('Change Details', {
            'fields': (
                'changed_by',
                'notes',
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    list_per_page = 50
    
    def has_add_permission(self, request):
        """Prevent manual addition of history records"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of history records (audit trail)"""
        return False
    
    def order_link(self, obj):
        """Clickable order number"""
        if obj.order:
            url = reverse('admin:orders_order_change', args=[obj.order.pk])
            return format_html('<a href="{}">{}</a>', url, obj.order.order_number)
        return '-'
    order_link.short_description = 'Order'
    order_link.admin_order_field = 'order__order_number'
    
    def status_transition(self, obj):
        """Display status transition with visual indicator"""
        current_status = obj.get_status_display() if hasattr(obj, 'get_status_display') else obj.status
        if obj.previous_status:
            # Get display name for previous status
            prev_status_display = obj.previous_status
            for choice in Order.ORDER_STATUS_CHOICES:
                if choice[0] == obj.previous_status:
                    prev_status_display = choice[1]
                    break
            return format_html(
                '<span style="color: #6c757d;">{}</span> → <span style="color: #28a745; font-weight: bold;">{}</span>',
                prev_status_display,
                current_status
            )
        return format_html(
            '<span style="color: #28a745; font-weight: bold;">{}</span>',
            current_status
        )
    status_transition.short_description = 'Status Change'
    
    def changed_by_info(self, obj):
        """Display who made the change"""
        if obj.changed_by:
            url = reverse('admin:accounts_customuser_change', args=[obj.changed_by.pk])
            # Get role display name
            role_display = obj.changed_by.role
            if hasattr(obj.changed_by, 'get_role_display'):
                role_display = obj.changed_by.get_role_display()
            else:
                # Fallback: get from choices
                from apps.accounts.models import CustomUser
                for choice in CustomUser.USER_ROLES:
                    if choice[0] == obj.changed_by.role:
                        role_display = choice[1]
                        break
            return format_html(
                '<a href="{}">{}</a><br><small>{}</small>',
                url,
                obj.changed_by.username,
                role_display
            )
        return 'System'
    changed_by_info.short_description = 'Changed By'
    changed_by_info.admin_order_field = 'changed_by__username'
    
    def notes_preview(self, obj):
        """Preview of notes"""
        if obj.notes:
            preview = obj.notes[:50] + '...' if len(obj.notes) > 50 else obj.notes
            return format_html('<small>{}</small>', preview)
        return '-'
    notes_preview.short_description = 'Notes'
    
    def created_at_formatted(self, obj):
        """Format creation date"""
        return obj.created_at.strftime('%Y-%m-%d %H:%M:%S')
    created_at_formatted.short_description = 'Created'
    created_at_formatted.admin_order_field = 'created_at'
    
    def get_queryset(self, request):
        """Optimize queryset"""
        qs = super().get_queryset(request)
        return qs.select_related('order', 'changed_by', 'created_by').order_by('-created_at')
