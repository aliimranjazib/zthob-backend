from rest_framework import serializers
from apps.orders.models import Order

class TailorOrderSummarySerializer(serializers.ModelSerializer):
    """
    High-performance summary serializer for the tailor dashboard lists.
    Avoids expensive calculations and deep nesting.
    """
    customer_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 
            'order_number', 
            'customer_name', 
            'status', 
            'status_display', 
            'total_amount', 
            'is_express', 
            'created_at', 
            'updated_at'
        ]
        
    def get_customer_name(self, obj):
        if not obj.customer:
            return 'Unknown'
        full_name = obj.customer.get_full_name().strip()
        return full_name if full_name else obj.customer.username

class TailorHomeSerializer(serializers.Serializer):
    """
    Serializer for the unified Tailor Home response.
    """
    counters = serializers.DictField()
    pipeline = serializers.DictField()
    express_orders = TailorOrderSummarySerializer(many=True)
    recent_orders = TailorOrderSummarySerializer(many=True)
    shop_status = serializers.DictField()
