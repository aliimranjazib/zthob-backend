from django.contrib import admin
from .models import Order, OrderItem, OrderStatusHistory

# Register your models here.

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'order_number',
        'customer', 
        'family_member',
        'tailor', 
        'status', 
        'total_amount', 
        'payment_status',
        'created_at'
    ]
    list_filter = [
        'status', 
        'payment_status', 
        'payment_method',
        'created_at'
    ]
    search_fields = [
        'order_number', 
        'customer__username', 
        'customer__email',
        'tailor__shop_name'
    ]
    readonly_fields = ['order_number', 'created_at', 'updated_at']
    
    def save_model(self, request, obj, form, change):
        if not change:  # Only set created_by when creating new objects
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'customer', 'family_member', 'tailor', 'status')
        }),
        ('Financial Information', {
            'fields': ('subtotal', 'tax_amount', 'delivery_fee', 'total_amount')
        }),
        ('Payment Information', {
            'fields': ('payment_status', 'payment_method')
        }),
        ('Delivery Information', {
            'fields': ('delivery_address', 'estimated_delivery_date', 'actual_delivery_date')
        }),
        ('Additional Information', {
            'fields': ('special_instructions', 'notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = [
        'order', 
        'fabric', 
        'quantity', 
        'unit_price', 
        'total_price',
        'is_ready'
    ]
    list_filter = ['is_ready', 'order__status']
    search_fields = [
        'order__order_number', 
        'fabric__name', 
        'fabric__sku'
    ]
    readonly_fields = ['total_price', 'created_at', 'updated_at']
    
    def save_model(self, request, obj, form, change):
        if not change:  # Only set created_by when creating new objects
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    list_display = [
        'order', 
        'status', 
        'previous_status', 
        'changed_by', 
        'created_at'
    ]
    list_filter = ['status', 'created_at']
    search_fields = [
        'order__order_number', 
        'changed_by__username'
    ]
    readonly_fields = ['created_at', 'updated_at']
    
    def save_model(self, request, obj, form, change):
        if not change:  # Only set created_by when creating new objects
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
