from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Order, OrderItem, OrderStatusHistory
from apps.tailors.models import TailorProfile,Fabric
from apps.customers.models import Address
from decimal import Decimal
from django.db import transaction
from apps.orders.services import OrderCalculationService


User = get_user_model()

class OrderItemSerializer(serializers.ModelSerializer):

    fabric_name = serializers.CharField(source='fabric.name', read_only=True)
    fabric_sku = serializers.CharField(source='fabric.sku', read_only=True)
    fabric_image = serializers.SerializerMethodField()
    class Meta:
        model = OrderItem
        fields = [
            'id','fabric','fabric_name','fabric_sku', 'fabric_image','quantity',
            'unit_price','total_price','measurements','custom_instructions',
            'is_ready','created_at'
        ]
        read_only_fields = ['id', 'total_price', 'created_at']

    def get_fabric_image(self,obj):
        if obj.fabric.primary_image:
            request=self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.fabric.primary_image.url)
            return obj.fabric.primary_image.url
        return None

class OrderItemCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model=OrderItem
        fields=['fabric','quantity','measurements','custom_instructions']

    def validate_quantity(self,value):
        if value<=0:
            raise serializers.ValidationError('Quantity must be greater than 0')
        return value

    def validate_unit_price(self,value):
        if value<=0:
            raise serializers.ValidationError('Unit price must be greater than 0')
        return value




class OrderSerializer(serializers.ModelSerializer):

    customer_name=serializers.CharField(source='customer.username',read_only=True)
    customer_email=serializers.CharField(source='customer.email',read_only=True)
    tailor_name=serializers.SerializerMethodField()
    tailor_contact=serializers.SerializerMethodField()
    family_member_name=serializers.SerializerMethodField()
    delivery_address_text=serializers.SerializerMethodField()
    items=OrderItemSerializer(source='order_items',many=True,read_only=True)
    items_count=serializers.IntegerField(read_only=True)
    can_be_cancelled=serializers.BooleanField(read_only=True)

    class Meta:
        model=Order
        fields = [
            'id',
            'order_number',
            'customer',
            'customer_name',
            'customer_email',
            'tailor',
            'tailor_name',
            'tailor_contact',
            'order_type',
            'status',
            'subtotal',
            'tax_amount',
            'delivery_fee',
            'total_amount',
            'payment_status',
            'payment_method',
            'family_member',
            'family_member_name',
            'delivery_address',
            'delivery_address_text',
            'estimated_delivery_date',
            'actual_delivery_date',
            'special_instructions',
            'notes',
            'items',
            'items_count',
            'can_be_cancelled',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id', 'order_number', 'total_amount', 'items_count', 
            'can_be_cancelled', 'created_at', 'updated_at'
        ]

    def get_tailor_name(self, obj):
        try:
            return obj.tailor.tailor_profile.shop_name
        except TailorProfile.DoesNotExist:
            return obj.tailor.username

    def get_tailor_contact(self, obj):
        try:
            return obj.tailor.tailor_profile.contact_number
        except TailorProfile.DoesNotExist:
            return None

    def get_family_member_name(self, obj):
        if obj.family_member:
            return f"{obj.family_member.name} ({obj.family_member.relationship})"
        return None

    def get_delivery_address_text(self,obj):
        if obj.delivery_address:
            return f"{obj.delivery_address.street}, {obj.delivery_address.city}, {obj.delivery_address.country}"
        return None
class OrderCreateSerializer(serializers.ModelSerializer):

    items=OrderItemCreateSerializer(many=True)

    class Meta:
        model=Order
        fields = [
            'customer',
            'tailor',
            'order_type',
            'payment_method',
            'family_member',
            'delivery_address',
            'estimated_delivery_date',
            'special_instructions',
            'items'
        ]

    def validate_items(self,value):
        if not value or len(value)==0:
            raise serializers.ValidationError("Order must have at least one item")
        
        tailor =self.context.get('tailor')
        validated_items=[]
        for item_data in value:
            fabric = item_data.get('fabric')
            quantity=item_data.get('quantity',1)
            if fabric is None:
                raise serializers.ValidationError("Each item must have a fabric")
            try:
                if isinstance(fabric,int):
                    fabric =Fabric.objects.select_for_update().get(id=fabric)
                elif not isinstance(fabric,Fabric):
                    raise serializers.ValidationError(f'Invalid fabric: {fabric}')
            except Fabric.DoesNotExist:
                raise serializers.ValidationError(f'Fabric with ID {fabric} does not exist')
            if quantity<=0:
                raise serializers.ValidationError(
                f"Quantity must be greater than 0 for fabric {fabric.name}"
                )
            if not fabric.is_active:
                raise serializers.ValidationError(
                    f"{fabric.name} is not available for purchase"
                    )

            if tailor and fabric.tailor.user!= tailor:
                raise serializers.ValidationError(
                    f"Fabric {fabric.name} does not belong to selected tailor"
                )
            item_data['fabric']=fabric
            validated_items.append(item_data)
        return validated_items

    def validate_tailor(self,value):
        if value is None:
            raise serializers.ValidationError('Tailor is required')
        if value.role!='TAILOR':
            raise serializers.ValidationError('Selected user is not a tailor')
        try:
            tailor_profile=value.tailor_profile
            if not tailor_profile.shop_status:
                raise serializers.ValidationError('Selected tailor is not accepting orders')
        except TailorProfile.DoesNotExist:
            raise serializers.ValidationError('Tailor profile not found')
        self.context['tailor'] = value
        return value

    def validate_family_member(self, value):
        if value:
            # Get the customer from context (set in the view)
            customer = self.context.get('request').user
            if value.user != customer:
                raise serializers.ValidationError('Family member must belong to the authenticated customer')
        return value
    
    def validate_delivery_address(self, value):
        if value:
            # Get the customer from context (set in the view)
            customer = self.context.get('request').user
            if value.user != customer:
                raise serializers.ValidationError('Delivery address must belong to the authenticated customer')
        return value

    def validate(self, data):
        """Validate order type based on fabric categories"""
        order_type = data.get('order_type')
        items_data = data.get('items', [])
        
        if items_data:
            # Check categories of all items
            fabric_categories = set()
            for item_data in items_data:
                fabric_value = item_data.get('fabric')
                if fabric_value:
                    try:
                        from apps.tailors.models import Fabric
                        
                        # Handle both ID and Fabric object cases
                        if isinstance(fabric_value, Fabric):
                            fabric = fabric_value
                        else:
                            # Try to get fabric by ID
                            fabric = Fabric.objects.get(id=fabric_value)
                        
                        if fabric.category:
                            fabric_categories.add(fabric.category.name.lower())
                    except (Fabric.DoesNotExist, ValueError, TypeError):
                        # Skip validation for invalid fabric references
                        pass
            
            # Business rule validation
            if not fabric_categories:
                # No valid categories found - allow any order type
                pass
            elif len(fabric_categories) > 1:
                # Mixed categories - only allow fabric_only
                if order_type != 'fabric_only':
                    raise serializers.ValidationError(
                        f"Orders with mixed categories ({', '.join(fabric_categories)}) can only be 'fabric_only' type"
                    )
            elif 'fabric' in fabric_categories:
                # Only fabric category: Can choose either fabric_only or fabric_with_stitching
                if order_type not in ['fabric_only', 'fabric_with_stitching']:
                    raise serializers.ValidationError(
                        "For fabric category items, you can choose either 'fabric_only' or 'fabric_with_stitching'"
                    )
            else:
                # Other categories (caps, handkerchief, etc.): Only fabric_only allowed
                if order_type != 'fabric_only':
                    raise serializers.ValidationError(
                        f"For {', '.join(fabric_categories)} category items, only 'fabric_only' option is available"
                    )
        
        return data
    @transaction.atomic
    def create(self,validated_data):
        items_data=validated_data.pop('items')
        tailor=validated_data.get('tailor')  # Use .get() method
        delivery_address=validated_data.get('delivery_address')
        items_with_fabrics=[]
        fabric_ids=[]
        # order=Order.objects.create(**validated_data)
        for item_data in items_data:
            fabric=item_data['fabric']
            fabric_ids.append(fabric.id)

        #lock fabric to prevent race conditions
        locked_fabrics=Fabric.objects.select_for_update().filter(
            id__in=fabric_ids
        )
        fabric_dict={f.id:f for f in locked_fabrics}
        for item_data in items_data:
            fabric=item_data['fabric']
            quantity=item_data.get('quantity',1)

            locked_fabric=fabric_dict.get(fabric.id)
            if not locked_fabric:
               raise serializers.ValidationError(
                f"Fabric {fabric.name} not found or locked"
            )
            if locked_fabric.stock<quantity:
               raise serializers.ValidationError(
                f"Insufficient stock for {locked_fabric.name}. "
                f"Available: {locked_fabric.stock}, Requested: {quantity}"
            )
            if not locked_fabric.is_active:
                raise serializers.ValidationError(
                f"{locked_fabric.name} is no longer available"
            )
            items_with_fabrics.append({
            'fabric': locked_fabric,
            'quantity': quantity,
            'unit_price': locked_fabric.price,  # ALWAYS use current DB price
            'measurements': item_data.get('measurements', {}),
            'custom_instructions': item_data.get('custom_instructions', ''),
        })
        totals = OrderCalculationService.calculate_all_totals(
        items_with_fabrics,
        delivery_address=delivery_address,
        tailor=tailor
        )
        validated_data.update(totals)
        order = Order.objects.create(**validated_data)
        for item_data in items_with_fabrics:
            fabric = item_data['fabric']
            quantity = item_data['quantity']
            
            # Create order item
            OrderItem.objects.create(
                order=order,
                fabric=fabric,
                quantity=quantity,
                unit_price=item_data['unit_price'],  # Snapshot of price at order time
                measurements=item_data['measurements'],
                custom_instructions=item_data['custom_instructions'],
            )
            fabric.stock -= quantity
            if fabric.stock < 0:
                raise serializers.ValidationError(
                    f"Stock cannot be negative for {fabric.name}"
                )
            fabric.save(update_fields=['stock'])
        try:
            OrderStatusHistory.objects.create(
                order=order,
                status=order.status,
                previous_status=None,
                changed_by=self.context.get('request').user,
                notes="Order created"
            )
        except Exception as e:
            # Edge Case: History creation failure shouldn't break order
            # Log error but don't fail order creation
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to create order history: {str(e)}")
    
        return order
        

class OrderUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model=Order
        fields=['status','notes']
    def validate_status(self,value):
        instance=self.instance
        if instance and value != instance.status:  # Only validate if status is actually changing
            
            # Get allowed transitions based on order type
            allowed_transitions = instance.get_allowed_status_transitions()
            
            current_status=instance.status
            if value not in allowed_transitions.get(current_status,[]):
                raise serializers.ValidationError(
                    f"Cannot change status from {current_status} to {value}. "
                    f"Allowed transitions from {current_status}: {allowed_transitions.get(current_status, [])}"
                )
        return value
    def update(self,instance,validated_data):
        old_status=instance.status
        new_status=validated_data.get('status',instance.status)

    # Update the order first
        instance = super().update(instance, validated_data)
    
        if old_status!=new_status:
            OrderStatusHistory.objects.create(
            order=instance,
            status=new_status,
            previous_status=old_status,
            changed_by=self.context.get('request').user,
            notes=validated_data.get('notes','')
        )
        return instance

class OrderListSerializer(serializers.ModelSerializer):
    customer_name=serializers.CharField(source='customer.username',read_only=True)
    tailor_name = serializers.SerializerMethodField()
    items_count = serializers.IntegerField(read_only=True)

    class Meta:
        model=Order
        fields = [
            'id',
            'order_number',
            'customer_name',
            'tailor_name',
            'status',
            'total_amount',
            'payment_status',
            'items_count',
            'created_at'
        ]

    def get_tailor_name(self, obj):
        try:
            return obj.tailor.tailor_profile.shop_name
        except TailorProfile.DoesNotExist:
            return obj.tailor.username

class OrderStatusHistorySerializer(serializers.ModelSerializer):
    changed_by_name = serializers.CharField(source='changed_by.username', read_only=True)

    class Meta:
        model = OrderStatusHistory
        fields = [
            'id',
            'status',
            'previous_status',
            'changed_by_name',
            'notes',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']

class OrderPaymentStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating payment status only"""
    payment_status = serializers.ChoiceField(
        choices=Order.PAYMENT_STATUS_CHOICES,
        required=True,
        help_text="Payment status: pending, paid, or refunded"
    )
            
