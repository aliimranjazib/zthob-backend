from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Order, OrderItem, OrderStatusHistory
from apps.tailors.models import TailorProfile,Fabric
from apps.customers.models import Address
from decimal import Decimal
from django.db import transaction
from apps.orders.services import OrderCalculationService
from zthob.translations import get_language_from_request, translate_message


User = get_user_model()

class OrderItemSerializer(serializers.ModelSerializer):

    fabric_name = serializers.CharField(source='fabric.name', read_only=True)
    fabric_sku = serializers.CharField(source='fabric.sku', read_only=True)
    fabric_stitching_price = serializers.DecimalField(source='fabric.stitching_price', max_digits=10, decimal_places=2, read_only=True)
    fabric_image = serializers.SerializerMethodField()
    family_member_name = serializers.SerializerMethodField()
    class Meta:
        model = OrderItem
        fields = [
            'id','fabric','fabric_name','fabric_sku', 'fabric_stitching_price', 'fabric_image','quantity',
            'unit_price','total_price','measurements','custom_instructions',
            'is_ready','family_member','family_member_name','created_at'
        ]
        read_only_fields = ['id', 'total_price', 'created_at']

    def get_family_member_name(self, obj):
        if obj.family_member:
            return obj.family_member.name
        
        # If no family member, return customer name with (Self) tag
        try:
            # For OrderItem, order is accessible via obj.order
            customer = obj.order.customer
            name = customer.get_full_name() or customer.username
            return f"{name} (Self)"
        except AttributeError:
            # Fallback for unexpected object structures
            return None

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
        fields=['fabric','quantity','measurements','custom_instructions','family_member']

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
    rider_name=serializers.SerializerMethodField()
    rider_phone=serializers.SerializerMethodField()
    family_member_name=serializers.SerializerMethodField()
    order_recipient=serializers.SerializerMethodField()
    all_recipients=serializers.SerializerMethodField()
    delivery_address_text=serializers.SerializerMethodField()
    items=OrderItemSerializer(source='order_items',many=True,read_only=True)
    items_count=serializers.IntegerField(read_only=True)
    can_be_cancelled=serializers.BooleanField(read_only=True)
    custom_styles = serializers.SerializerMethodField()
    rider_status = serializers.CharField(read_only=True)
    tailor_status = serializers.CharField(read_only=True)
    status_info = serializers.SerializerMethodField()

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
            'rider',
            'rider_name',
            'rider_phone',
            'order_type',
            'status',
            'rider_status',
            'tailor_status',
            'subtotal',
            'tax_amount',
            'delivery_fee',
            'total_amount',
            'payment_status',
            'payment_method',
            'family_member',
            'family_member_name',
            'order_recipient',
            'all_recipients',
            'delivery_address',
            'delivery_address_text',
            'estimated_delivery_date',
            'actual_delivery_date',
            'special_instructions',
            'appointment_date',
            'appointment_time',
            'custom_styles',
            'notes',
            'measurement_taken_at',
            'items',
            'items_count',
            'can_be_cancelled',
            'status_info',
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

    def get_rider_name(self, obj):
        if obj.rider:
            try:
                if hasattr(obj.rider, 'rider_profile') and obj.rider.rider_profile:
                    return obj.rider.rider_profile.full_name or obj.rider.username
            except:
                pass
            return obj.rider.username
        return None

    def get_rider_phone(self, obj):
        if obj.rider:
            try:
                if hasattr(obj.rider, 'rider_profile') and obj.rider.rider_profile:
                    return obj.rider.rider_profile.phone_number
            except:
                pass
            return obj.rider.phone
        return None

    def get_family_member_name(self, obj):
        if obj.family_member:
            return obj.family_member.name
        
        # If no family member, return customer name with (Self) tag
        try:
            name = obj.customer.get_full_name() or obj.customer.username
            return f"{name} (Self)"
        except AttributeError:
            return None
    
    def get_all_recipients(self, obj):
        """Get all recipients for this order as an array."""
        recipients = self._collect_recipients(obj)
        return recipients

    def get_order_recipient(self, obj):
        """Get primary order recipient (for backward compatibility)."""
        recipients = self._collect_recipients(obj)
        return recipients[0] if recipients else None

    def _collect_recipients(self, obj):
        """Helper to collect unique recipients from order items."""
        include_measurements = obj.rider_status == 'measurement_taken' and obj.rider_measurements
        recipients = []
        seen_recipients = set()
        
        # Add order-level family member if exists
        if obj.family_member:
            recipients.append({
                'type': 'family_member',
                'id': obj.family_member.id,
                'name': obj.family_member.name,
            })
            seen_recipients.add(f"family_{obj.family_member.id}")
        
        # Add recipients from items
        for item in obj.order_items.all():
            if item.family_member:
                key = f"family_{item.family_member.id}"
                if key not in seen_recipients:
                    recipients.append({
                        'type': 'family_member',
                        'id': item.family_member.id,
                        'name': item.family_member.name,
                    })
                    seen_recipients.add(key)
            else:
                key = "customer"
                if key not in seen_recipients:
                    recipients.append({
                        'type': 'customer',
                        'id': obj.customer.id,
                        'name': obj.customer.get_full_name() or obj.customer.username,
                        'phone': obj.customer.phone,
                        'email': obj.customer.email,
                    })
                    seen_recipients.add(key)

        if include_measurements:
            for recipient in recipients:
                recipient['measurements'] = obj.rider_measurements
        
        return recipients

    def get_delivery_address_text(self,obj):
        if obj.delivery_address:
            return f"{obj.delivery_address.street}, {obj.delivery_address.city}, {obj.delivery_address.country}"
        return None
    
    def get_custom_styles(self, obj):
        """Return custom_styles, or empty array if None"""
        return obj.custom_styles if obj.custom_styles is not None else []
    
    def get_status_info(self, obj):
        """Get status information including next available actions"""
        request = self.context.get('request')
        if not request or not request.user:
            return None
        
        user_role = request.user.role
        
        # Get allowed transitions from service
        from apps.orders.services import OrderStatusTransitionService
        allowed_transitions = OrderStatusTransitionService.get_allowed_transitions(obj, user_role)
        
        # Build next available actions
        next_actions = []
        
        # Track values to avoid duplicates (prefer more specific status types)
        seen_values = set()
        
        # Add status actions
        for status_value in allowed_transitions.get('status', []):
            # Skip if already at this status
            if status_value == obj.status:
                continue
            action = self._build_status_action('status', status_value, user_role)
            if action:
                next_actions.append(action)
                seen_values.add(status_value)
        
        # Add rider_status actions (prefer over status if same value)
        for rider_status_value in allowed_transitions.get('rider_status', []):
            # Skip if already at this status
            if rider_status_value == obj.rider_status:
                continue
            # If this value already exists as a status action, remove the status action and use this one
            if rider_status_value in seen_values:
                # Remove the duplicate status action
                next_actions = [a for a in next_actions if not (a['type'] == 'status' and a['value'] == rider_status_value)]
            action = self._build_status_action('rider_status', rider_status_value, user_role)
            if action:
                next_actions.append(action)
                seen_values.add(rider_status_value)
        
        # Add tailor_status actions (prefer over status if same value)
        for tailor_status_value in allowed_transitions.get('tailor_status', []):
            # Skip if already at this status
            if tailor_status_value == obj.tailor_status:
                continue
            # If this value already exists as a status action, remove the status action and use this one
            if tailor_status_value in seen_values:
                # Remove the duplicate status action
                next_actions = [a for a in next_actions if not (a['type'] == 'status' and a['value'] == tailor_status_value)]
            action = self._build_status_action('tailor_status', tailor_status_value, user_role)
            if action:
                next_actions.append(action)
                seen_values.add(tailor_status_value)
        
        # Check if order can be cancelled
        can_cancel = False
        cancel_reason = None
        language = get_language_from_request(request) if request else 'en'
        
        if user_role == 'USER' and obj.status == 'pending':
            can_cancel = True
        elif obj.status in ['delivered', 'cancelled']:
            cancel_reason = translate_message("Order is {status} and cannot be cancelled", language, status=obj.status)
        elif obj.status != 'pending':
            cancel_reason = translate_message("Orders can only be cancelled when status is pending", language)
        
        # Calculate status progress
        status_progress = self._calculate_status_progress(obj)
        
        # Add measurement tracking for fabric_with_stitching orders
        measurement_status = None
        if obj.order_type == 'fabric_with_stitching' and obj.rider_status in ['on_way_to_measurement', 'measurement_taken']:
            from django.db.models import Q
            total_items = obj.order_items.count()
            items_with_measurements = obj.order_items.exclude(
                Q(measurements__isnull=True) | Q(measurements={})
            ).count()
            items_without_measurements = total_items - items_with_measurements
            
            measurement_status = {
                'all_measured': obj.all_items_have_measurements,
                'total_items': total_items,
                'measured_items': items_with_measurements,
                'remaining_items': items_without_measurements,
            }
        
        return {
            'current_status': obj.status,
            'current_rider_status': obj.rider_status,
            'current_tailor_status': obj.tailor_status,
            'next_available_actions': next_actions,
            'can_cancel': can_cancel,
            'cancel_reason': cancel_reason,
            'status_progress': status_progress,
            'measurement_status': measurement_status,
        }
    
    def _build_status_action(self, action_type, value, user_role):
        """Build action object for status transition with translation support"""
        # Get request from context for language detection
        request = self.context.get('request')
        language = get_language_from_request(request) if request else 'en'
        
        # Map status values to labels and descriptions
        status_labels = {
            'status': {
                'confirmed': {'label': 'Accept Order', 'description': 'Accept this order'},
                'in_progress': {'label': 'Mark In Progress', 'description': 'Start processing this order'},
                'ready_for_delivery': {'label': 'Mark Ready for Delivery', 'description': 'Order is ready for pickup/delivery'},
                'delivered': {'label': 'Mark Delivered', 'description': 'Mark order as delivered'},
                'cancelled': {'label': 'Cancel Order', 'description': 'Cancel this order'},
            },
            'rider_status': {
                'accepted': {'label': 'Accept Order', 'description': 'Accept this order for delivery'},
                'on_way_to_pickup': {'label': 'Start Pickup', 'description': 'On way to pickup order from tailor'},
                'picked_up': {'label': 'Mark Picked Up', 'description': 'Order picked up from tailor'},
                'on_way_to_delivery': {'label': 'Start Delivery', 'description': 'On way to deliver order to customer'},
                'on_way_to_measurement': {'label': 'Start Measurement', 'description': 'On way to take customer measurements'},
                'measurement_taken': {'label': 'Complete Measurement', 'description': 'Measurements taken successfully'},
                'delivered': {'label': 'Mark Delivered', 'description': 'Order delivered to customer'},
            },
            'tailor_status': {
                'accepted': {'label': 'Accept Order', 'description': 'Accept this order'},
                'in_progress': {'label': 'Mark In Progress', 'description': 'Mark order as in progress'},
                'stitching_started': {'label': 'Start Stitching', 'description': 'Start stitching the garment'},
                'stitched': {'label': 'Finish Stitching', 'description': 'Stitching completed'},
            }
        }
        
        action_info = status_labels.get(action_type, {}).get(value)
        if not action_info:
            return None
        
        # Translate label and description
        translated_label = translate_message(action_info['label'], language)
        translated_description = translate_message(action_info['description'], language)
        
        # Determine if confirmation is required
        requires_confirmation = value in ['cancelled', 'delivered', 'accepted']
        
        # Build confirmation message with translation
        confirmation_message = None
        if requires_confirmation:
            if value == 'accepted':
                confirmation_message = translate_message("Are you sure you want to accept this order?", language)
            elif value == 'delivered':
                confirmation_message = translate_message("Are you sure you want to mark delivered?", language)
            elif value == 'cancelled':
                confirmation_message = translate_message("Are you sure you want to cancel order?", language)
        
        return {
            'type': action_type,
            'value': value,
            'label': translated_label,
            'description': translated_description,
            'role': user_role,
            'requires_confirmation': requires_confirmation,
            'confirmation_message': confirmation_message
        }
    
    def _calculate_status_progress(self, obj):
        """Calculate progress percentage based on order type and current status"""
        if obj.order_type == 'fabric_only':
            # Fabric only: pending -> confirmed -> in_progress -> ready_for_delivery -> delivered (5 steps)
            steps = {
                'pending': 1,
                'confirmed': 2,
                'in_progress': 3,
                'ready_for_delivery': 4,
                'delivered': 5,
                'cancelled': 0
            }
            current_step = steps.get(obj.status, 0)
            total_steps = 5
        else:  # fabric_with_stitching
            # Fabric with stitching: pending -> confirmed -> in_progress -> ready_for_delivery -> delivered (5 main steps)
            # But with more granular tracking via rider_status and tailor_status
            steps = {
                'pending': 1,
                'confirmed': 2,
                'in_progress': 3,
                'ready_for_delivery': 4,
                'delivered': 5,
                'cancelled': 0
            }
            current_step = steps.get(obj.status, 0)
            total_steps = 5
        
        percentage = int((current_step / total_steps) * 100) if total_steps > 0 else 0
        
        return {
            'current_step': current_step,
            'total_steps': total_steps,
            'percentage': percentage
        }

class OrderCreateSerializer(serializers.ModelSerializer):

    items=OrderItemCreateSerializer(many=True)
    
    # Allow passing either an Address ID (int) or an Address Object (dict)
    delivery_address = serializers.JSONField(
        required=False,
        allow_null=True,
        help_text="Either an address ID (int) or complete address object"
    )

    distance_km = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        allow_null=True,
        write_only=True,
        help_text="Distance in kilometers for delivery fee calculation (optional)"
    )

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
            'appointment_date',
            'appointment_time',
            'custom_styles',
            'items',
            'distance_km'
        ]

    def validate_items(self,value):
        if not value or len(value)==0:
            raise serializers.ValidationError("Order must have at least one item")
        
        tailor =self.context.get('tailor')
        customer = self.context.get('request').user
        validated_items=[]
        for item_data in value:
            fabric = item_data.get('fabric')
            quantity=item_data.get('quantity',1)
            family_member = item_data.get('family_member')
            
            if fabric is None:
                raise serializers.ValidationError("Each item must have a fabric")
            
            # Validate family member belongs to customer
            if family_member and family_member.user != customer:
                raise serializers.ValidationError(f"Family member {family_member.name} must belong to the authenticated customer")
                
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
        if value is None:
            return None
            
        customer = self.context.get('request').user
        
        # Case 1: Integer ID (Saved Address)
        if isinstance(value, int):
            try:
                address = Address.objects.get(id=value, user=customer)
                self.context['using_saved_address'] = True
                self.context['saved_address'] = address
                return address # Return actual Address object for the ForeignKey
            except Address.DoesNotExist:
                raise serializers.ValidationError('Selected address does not exist')
                
        # Case 2: Dict/Object (Current Location)
        elif isinstance(value, dict):
            if 'latitude' not in value or 'longitude' not in value:
                raise serializers.ValidationError('Address must contain latitude and longitude')
            
            try:
                lat = float(value['latitude'])
                lng = float(value['longitude'])
            except (ValueError, TypeError):
                raise serializers.ValidationError('Invalid latitude or longitude')
                
            # Basic validation for Saudi Arabia bounds (approximate)
            if not (16 <= lat <= 32):
                raise serializers.ValidationError('Latitude must be within Saudi Arabia bounds')
            if not (34 <= lng <= 56):
                raise serializers.ValidationError('Longitude must be within Saudi Arabia bounds')
                
            self.context['using_current_location'] = True
            self.context['current_location_data'] = value
            return None # Return None for the ForeignKey field
            
        else:
            raise serializers.ValidationError('Invalid delivery address format. Must be an ID (int) or Address object (dict).')
    
    def validate_custom_styles(self, value):
        """Validate custom_styles array structure"""
        if value is None:
            return None
        
        if not isinstance(value, list):
            raise serializers.ValidationError("custom_styles must be an array")
        
        required_fields = ['style_type', 'index', 'label', 'asset_path']
        
        for idx, style in enumerate(value):
            if not isinstance(style, dict):
                raise serializers.ValidationError(
                    f"custom_styles[{idx}] must be an object"
                )
            
            # Check required fields
            for field in required_fields:
                if field not in style:
                    raise serializers.ValidationError(
                        f"custom_styles[{idx}] is missing required field: {field}"
                    )
            
            # Validate field types
            if not isinstance(style['style_type'], str):
                raise serializers.ValidationError(
                    f"custom_styles[{idx}].style_type must be a string"
                )
            
            if not isinstance(style['index'], int):
                raise serializers.ValidationError(
                    f"custom_styles[{idx}].index must be an integer"
                )
            
            if not isinstance(style['label'], str):
                raise serializers.ValidationError(
                    f"custom_styles[{idx}].label must be a string"
                )
            
            if not isinstance(style['asset_path'], str):
                raise serializers.ValidationError(
                    f"custom_styles[{idx}].asset_path must be a string"
                )
            
            # Validate index is non-negative
            if style['index'] < 0:
                raise serializers.ValidationError(
                    f"custom_styles[{idx}].index must be a non-negative integer"
                )
        
        return value

    @transaction.atomic
    def create(self,validated_data):
        items_data=validated_data.pop('items')
        tailor=validated_data.get('tailor')  # Use .get() method
        validated_data.pop('delivery_address',None)
        using_current_location=self.context.get('using_current_location',False)
        saved_address=self.context.get('saved_address',None)
        current_location_data=self.context.get('current_location_data',None)
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
            'family_member': item_data.get('family_member'),
        })
        # Get distance_km from validated_data if provided
        # Get distance_km from validated_data if provided
        distance_km = validated_data.pop('distance_km', None)
        if distance_km is not None:
            distance_km = float(distance_km)
        
        # Get order_type to pass to calculation service
        order_type = validated_data.get('order_type', 'fabric_only')
        
        # Prepare delivery coordinates based on delivery type
        delivery_lat = None
        delivery_lng = None
        
        if using_current_location and current_location_data:
            
            validated_data['delivery_address'] = None
            validated_data['delivery_latitude'] = current_location_data['latitude']
            validated_data['delivery_longitude'] = current_location_data['longitude']
            validated_data['delivery_formatted_address'] = current_location_data.get('formatted_address', '')
            validated_data['delivery_street'] = current_location_data.get('street', '')
            validated_data['delivery_city'] = current_location_data.get('city', '')
            validated_data['delivery_extra_info'] = current_location_data.get('extra_info', '')
            
            delivery_lat = current_location_data['latitude']
            delivery_lng = current_location_data['longitude']
        else:
            # Using saved address (or None)
            validated_data['delivery_address'] = saved_address
            validated_data['delivery_latitude'] = None
            validated_data['delivery_longitude'] = None
            validated_data['delivery_formatted_address'] = None
            validated_data['delivery_street'] = None
            validated_data['delivery_city'] = None
            validated_data['delivery_extra_info'] = None
            
            if saved_address:
                delivery_lat = saved_address.latitude
                delivery_lng = saved_address.longitude
        
        # Calculate totals with coordinates
        totals = OrderCalculationService.calculate_all_totals(
            items_data=items_with_fabrics,
            distance_km=distance_km,
            delivery_latitude=delivery_lat,
            delivery_longitude=delivery_lng,
            tailor=tailor,
            order_type=order_type
        )
        
        # Remove stitching_price from totals if it exists (Order model doesn't have this field yet)
        # It's already included in total_amount
        totals.pop('stitching_price', None)
        
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
                family_member=item_data['family_member'],
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
    rider_status = serializers.ChoiceField(
        choices=Order.RIDER_STATUS_CHOICES,
        required=False,
        allow_null=True
    )
    tailor_status = serializers.ChoiceField(
        choices=Order.TAILOR_STATUS_CHOICES,
        required=False,
        allow_null=True
    )
    
    class Meta:
        model=Order
        fields=['status', 'rider_status', 'tailor_status', 'notes', 'appointment_date', 'appointment_time', 'custom_styles']
    
    def validate_custom_styles(self, value):
        """Validate custom_styles array structure"""
        if value is None:
            return None
        
        if not isinstance(value, list):
            raise serializers.ValidationError("custom_styles must be an array")
        
        required_fields = ['style_type', 'index', 'label', 'asset_path']
        
        for idx, style in enumerate(value):
            if not isinstance(style, dict):
                raise serializers.ValidationError(
                    f"custom_styles[{idx}] must be an object"
                )
            
            # Check required fields
            for field in required_fields:
                if field not in style:
                    raise serializers.ValidationError(
                        f"custom_styles[{idx}] is missing required field: {field}"
                    )
            
            # Validate field types
            if not isinstance(style['style_type'], str):
                raise serializers.ValidationError(
                    f"custom_styles[{idx}].style_type must be a string"
                )
            
            if not isinstance(style['index'], int):
                raise serializers.ValidationError(
                    f"custom_styles[{idx}].index must be an integer"
                )
            
            if not isinstance(style['label'], str):
                raise serializers.ValidationError(
                    f"custom_styles[{idx}].label must be a string"
                )
            
            if not isinstance(style['asset_path'], str):
                raise serializers.ValidationError(
                    f"custom_styles[{idx}].asset_path must be a string"
                )
            
            # Validate index is non-negative
            if style['index'] < 0:
                raise serializers.ValidationError(
                    f"custom_styles[{idx}].index must be a non-negative integer"
                )
        
        return value
    
    def validate(self, attrs):
        """Validate status transitions using OrderStatusTransitionService"""
        instance = self.instance
        if not instance:
            return attrs
        
        request = self.context.get('request')
        if not request or not request.user:
            return attrs
        
        user_role = request.user.role
        new_status = attrs.get('status', instance.status)
        new_rider_status = attrs.get('rider_status', instance.rider_status)
        new_tailor_status = attrs.get('tailor_status', instance.tailor_status)
        
        # Use transition service for validation
        from apps.orders.services import OrderStatusTransitionService
        
        is_valid, error_msg = OrderStatusTransitionService.validate_transition(
            order=instance,
            new_status=new_status if new_status != instance.status else None,
            new_rider_status=new_rider_status if new_rider_status != instance.rider_status else None,
            new_tailor_status=new_tailor_status if new_tailor_status != instance.tailor_status else None,
            user_role=user_role,
            user=request.user
        )
        
        if not is_valid:
            raise serializers.ValidationError({'status': error_msg})
        
        return attrs
    def update(self, instance, validated_data):
        """Update order using OrderStatusTransitionService"""
        request = self.context.get('request')
        user = request.user if request else None
        user_role = user.role if user else None
        
        # Extract status fields
        new_status = validated_data.pop('status', None)
        new_rider_status = validated_data.pop('rider_status', None)
        new_tailor_status = validated_data.pop('tailor_status', None)
        notes = validated_data.pop('notes', None)
        
        # Update other fields first (appointment_date, appointment_time, custom_styles)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Use transition service for status updates
        from apps.orders.services import OrderStatusTransitionService
        
        if new_status is not None or new_rider_status is not None or new_tailor_status is not None:
            success, error_msg, updated_order = OrderStatusTransitionService.transition(
                order=instance,
                new_status=new_status,
                new_rider_status=new_rider_status,
                new_tailor_status=new_tailor_status,
                user_role=user_role,
                user=user,
                notes=notes
            )
            
            if not success:
                raise serializers.ValidationError({'status': error_msg})
            
            instance = updated_order
        
        # Send push notification for order status change
        try:
            from apps.notifications.services import NotificationService
            NotificationService.send_order_status_notification(
                order=instance,
                old_status=instance.status,  # This will be handled by history
                new_status=instance.status,
                changed_by=user
            )
        except Exception as e:
            # Log error but don't fail the update
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send order status notification: {str(e)}")
        
        return instance

class OrderListSerializer(serializers.ModelSerializer):
    customer_name=serializers.CharField(source='customer.username',read_only=True)
    tailor_name = serializers.SerializerMethodField()
    items_count = serializers.IntegerField(read_only=True)
    custom_styles = serializers.SerializerMethodField()
    items = OrderItemSerializer(source='order_items', many=True, read_only=True)
    rider_status = serializers.CharField(read_only=True)
    tailor_status = serializers.CharField(read_only=True)
    status_info = serializers.SerializerMethodField()

    class Meta:
        model=Order
        fields = [
            'id',
            'order_number',
            'customer_name',
            'tailor_name',
            'order_type',
            'status',
            'rider_status',
            'tailor_status',
            'total_amount',
            'payment_status',
            'appointment_date',
            'appointment_time',
            'custom_styles',
            'rider_measurements',
            'measurement_taken_at',
            'items_count',
            'items',
            'status_info',
            'created_at'
        ]

    def get_tailor_name(self, obj):
        try:
            return obj.tailor.tailor_profile.shop_name
        except TailorProfile.DoesNotExist:
            return obj.tailor.username
    
    def get_custom_styles(self, obj):
        """Return custom_styles, or empty array if None"""
        return obj.custom_styles if obj.custom_styles is not None else []
    
    def get_status_info(self, obj):
        """Get status information including next available actions - reuse from OrderSerializer"""
        # Reuse the same logic from OrderSerializer
        request = self.context.get('request')
        if not request or not request.user:
            return None
        
        user_role = request.user.role
        
        # Get allowed transitions from service
        from apps.orders.services import OrderStatusTransitionService
        allowed_transitions = OrderStatusTransitionService.get_allowed_transitions(obj, user_role)
        
        # Build next available actions
        next_actions = []
        
        # Track values to avoid duplicates (prefer more specific status types)
        seen_values = set()
        
        # Add status actions
        for status_value in allowed_transitions.get('status', []):
            # Skip if already at this status
            if status_value == obj.status:
                continue
            action = OrderSerializer._build_status_action(self, 'status', status_value, user_role)
            if action:
                next_actions.append(action)
                seen_values.add(status_value)
        
        # Add rider_status actions (prefer over status if same value)
        for rider_status_value in allowed_transitions.get('rider_status', []):
            # Skip if already at this status
            if rider_status_value == obj.rider_status:
                continue
            # If this value already exists as a status action, remove the status action and use this one
            if rider_status_value in seen_values:
                # Remove the duplicate status action
                next_actions = [a for a in next_actions if not (a['type'] == 'status' and a['value'] == rider_status_value)]
            action = OrderSerializer._build_status_action(self, 'rider_status', rider_status_value, user_role)
            if action:
                next_actions.append(action)
                seen_values.add(rider_status_value)
        
        # Add tailor_status actions (prefer over status if same value)
        for tailor_status_value in allowed_transitions.get('tailor_status', []):
            # Skip if already at this status
            if tailor_status_value == obj.tailor_status:
                continue
            # If this value already exists as a status action, remove the status action and use this one
            if tailor_status_value in seen_values:
                # Remove the duplicate status action
                next_actions = [a for a in next_actions if not (a['type'] == 'status' and a['value'] == tailor_status_value)]
            action = OrderSerializer._build_status_action(self, 'tailor_status', tailor_status_value, user_role)
            if action:
                next_actions.append(action)
                seen_values.add(tailor_status_value)
        
        # Check if order can be cancelled
        can_cancel = False
        cancel_reason = None
        language = get_language_from_request(request) if request else 'en'
        
        if user_role == 'USER' and obj.status == 'pending':
            can_cancel = True
        elif obj.status in ['delivered', 'cancelled']:
            cancel_reason = translate_message("Order is {status} and cannot be cancelled", language, status=obj.status)
        elif obj.status != 'pending':
            cancel_reason = translate_message("Orders can only be cancelled when status is pending", language)
        
        # Calculate status progress
        status_progress = OrderSerializer._calculate_status_progress(self, obj)
        
        # Add measurement tracking for fabric_with_stitching orders
        measurement_status = None
        if obj.order_type == 'fabric_with_stitching' and obj.rider_status in ['on_way_to_measurement', 'measurement_taken']:
            from django.db.models import Q
            total_items = obj.order_items.count()
            items_with_measurements = obj.order_items.exclude(
                Q(measurements__isnull=True) | Q(measurements={})
            ).count()
            items_without_measurements = total_items - items_with_measurements
            
            measurement_status = {
                'all_measured': obj.all_items_have_measurements,
                'total_items': total_items,
                'measured_items': items_with_measurements,
                'remaining_items': items_without_measurements,
            }
        
        return {
            'current_status': obj.status,
            'current_rider_status': obj.rider_status,
            'current_tailor_status': obj.tailor_status,
            'next_available_actions': next_actions,
            'can_cancel': can_cancel,
            'cancel_reason': cancel_reason,
            'status_progress': status_progress,
            'measurement_status': measurement_status,
        }

class OrderStatusUpdateResponseSerializer(OrderSerializer):
    """Lightweight serializer for order status update responses - only returns essential fields"""
    
    class Meta:
        model = Order
        fields = [
            'id',
            'order_number',
            'status',
            'rider_status',
            'tailor_status',
            'status_info',
            'updated_at'
        ]
        read_only_fields = ['id', 'order_number', 'status', 'rider_status', 'tailor_status', 'updated_at']

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
            
