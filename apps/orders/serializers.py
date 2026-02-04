from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Order, OrderItem, OrderStatusHistory
from apps.tailors.models import TailorProfile,Fabric
from apps.customers.models import Address
from apps.customization.models import CustomStyle
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
    custom_styles = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderItem
        fields = [
            'id','fabric','fabric_name','fabric_sku', 'fabric_stitching_price', 'fabric_image','quantity',
            'unit_price','total_price','measurements','custom_instructions',
            'is_ready','family_member','family_member_name','custom_styles','created_at'
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
        # Handle measurement orders where fabric is None
        if not obj.fabric:
            return None
        
        if obj.fabric.primary_image:
            request=self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.fabric.primary_image.url)
            return obj.fabric.primary_image.url
        return None
    
    def get_custom_styles(self, obj):
        """Return custom_styles with absolute URLs for images"""
        styles = obj.custom_styles if obj.custom_styles is not None else []
        if not styles:
            return []
            
        request = self.context.get('request')
        if not request:
            return styles
            
        import copy
        processed_styles = copy.deepcopy(styles)
        
        from django.conf import settings
        media_url = getattr(settings, 'MEDIA_URL', '/media/')
        
        for style in processed_styles:
            asset_path = style.get('asset_path')
            if asset_path and not (asset_path.startswith('http://') or asset_path.startswith('https://')):
                if not asset_path.startswith(media_url) and not asset_path.startswith('/'):
                    full_path = media_url + asset_path
                else:
                    full_path = asset_path
                style['asset_path'] = request.build_absolute_uri(full_path)
                
        return processed_styles

class OrderItemCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model=OrderItem
        fields=['fabric','quantity','measurements','custom_instructions','family_member','custom_styles']
        extra_kwargs = {
            'fabric': {'required': False, 'allow_null': True}
        }

    def validate_quantity(self,value):
        if value<=0:
            raise serializers.ValidationError('Quantity must be greater than 0')
        return value

    def validate_unit_price(self,value):
        if value<=0:
            raise serializers.ValidationError('Unit price must be greater than 0')
        return value




class OrderSerializer(serializers.ModelSerializer):

    customer_name=serializers.SerializerMethodField()
    customer_email=serializers.CharField(source='customer.email',read_only=True)
    customer_phone=serializers.CharField(source='customer.phone',read_only=True)
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
    pricing_summary = serializers.SerializerMethodField()
    delivery_address = serializers.SerializerMethodField()

    class Meta:
        model=Order
        fields = [
            'id',
            'order_number',
            'customer',
            'customer_name',
            'customer_email',
            'customer_phone',
            'tailor',
            'tailor_name',
            'tailor_contact',
            'rider',
            'rider_name',
            'rider_phone',
            'order_type',
            'service_mode',
            'status',
            'rider_status',
            'tailor_status',
            'subtotal',
            'stitching_price',
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
            'stitching_completion_date',
            'stitching_completion_time',
            'appointment_date',
            'appointment_time',
            'custom_styles',
            'notes',
            'measurement_taken_at',
            'items',
            'items_count',
            'can_be_cancelled',
            'status_info',
            'pricing_summary',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id', 'order_number', 'stitching_price', 'total_amount', 'items_count', 
            'can_be_cancelled', 'created_at', 'updated_at'
        ]

    def get_customer_name(self, obj):
        if not obj.customer:
            return 'Unknown'
        full_name = obj.customer.get_full_name().strip()
        return full_name if full_name else obj.customer.username

    def get_tailor_name(self, obj):
        if not obj.tailor:
            return None
        try:
            return obj.tailor.tailor_profile.shop_name
        except TailorProfile.DoesNotExist:
            return obj.tailor.username

    def get_tailor_contact(self, obj):
        """Get tailor contact (verified phone from user account)"""
        return obj.tailor.phone if obj.tailor else None

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
        """Get rider phone (verified phone from user account)"""
        return obj.rider.phone if obj.rider else None

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

    def get_delivery_address(self, obj):
        """Return structured delivery address with fallback for current location orders"""
        if obj.delivery_address:
            return {
                'id': obj.delivery_address.id,
                'latitude': obj.delivery_address.latitude,
                'longitude': obj.delivery_address.longitude,
                'address': obj.delivery_address.address or '',
                'extra_info': obj.delivery_address.extra_info or '',
                'is_default': obj.delivery_address.is_default,
                'address_tag': obj.delivery_address.address_tag,
            }
        
        # Fallback to coordinate fields if it was a "current location" order
        elif obj.delivery_latitude and obj.delivery_longitude:
            return {
                'id': None,
                'latitude': obj.delivery_latitude,
                'longitude': obj.delivery_longitude,
                'address': obj.delivery_formatted_address or '',
                'extra_info': obj.delivery_extra_info or '',
                'is_default': False,
                'address_tag': 'Current Location',
            }
        return None

    def get_delivery_address_text(self, obj):
        if obj.delivery_address:
            street = obj.delivery_address.street or ""
            city = obj.delivery_address.city or ""
            country = obj.delivery_address.country or ""
            return f"{street}, {city}, {country}".strip(", ")
            
        # Fallback for current location
        elif obj.delivery_formatted_address:
            return obj.delivery_formatted_address
            
        return None
    
    def get_custom_styles(self, obj):
        """Return custom_styles with absolute URLs for images"""
        styles = obj.custom_styles if obj.custom_styles is not None else []
        if not styles:
            return []
            
        request = self.context.get('request')
        if not request:
            return styles
            
        import copy
        processed_styles = copy.deepcopy(styles)
        
        from django.conf import settings
        media_url = getattr(settings, 'MEDIA_URL', '/media/')
        
        for style in processed_styles:
            asset_path = style.get('asset_path')
            if asset_path and not (asset_path.startswith('http://') or asset_path.startswith('https://')):
                if not asset_path.startswith(media_url) and not asset_path.startswith('/'):
                    full_path = media_url + asset_path
                else:
                    full_path = asset_path
                style['asset_path'] = request.build_absolute_uri(full_path)
                
        return processed_styles
    
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
        
        # Add custom actions
        for custom_action in allowed_transitions.get('custom_actions', []):
            next_actions.append(custom_action)
        
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
        if obj.order_type == 'fabric_with_stitching':
            is_rider_measuring = obj.rider_status in ['on_way_to_measurement', 'measurement_taken']
            is_walk_in_measuring = obj.service_mode == 'walk_in' and obj.status in ['confirmed', 'in_progress']
            
            if is_rider_measuring or is_walk_in_measuring:
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
                'ready_for_pickup': {'label': 'Mark Ready for Pickup', 'description': 'Order is ready for customer pickup'},
                'delivered': {'label': 'Mark Delivered', 'description': 'Mark order as delivered'},
                'collected': {'label': 'Mark Collected', 'description': 'Order collected by customer'},
                'cancelled': {'label': 'Cancel Order', 'description': 'Cancel this order'},
            },
            'rider_status': {
                'accepted': {'label': 'Accept Order', 'description': 'Accept this order for delivery'},
                'on_way_to_pickup': {'label': 'Start Pickup', 'description': 'On way to pickup order from tailor'},
                'picked_up': {'label': 'Mark Picked Up', 'description': 'Order picked up from tailor'},
                'on_way_to_delivery': {'label': 'Start Delivery', 'description': 'On way to deliver order to customer'},
                'on_way_to_measurement': {'label': 'Start Measurement', 'description': 'On way to take customer measurements'},
                'measuring': {'label': 'Taking Measurements', 'description': 'Currently taking customer measurements'},
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
            if obj.service_mode == 'walk_in':
                steps = {
                    'pending': 1,
                    'confirmed': 2,
                    'in_progress': 3,
                    'ready_for_pickup': 4,
                    'collected': 5,
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
            if obj.service_mode == 'walk_in':
                steps = {
                    'pending': 1,
                    'confirmed': 2,
                    'in_progress': 3,
                    'ready_for_pickup': 4,
                    'collected': 5,
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

    def get_pricing_summary(self, obj):
        """Return grouped pricing information"""
        return {
            'subtotal': obj.subtotal,
            'stitching_price': obj.stitching_price,
            'tax_amount': obj.tax_amount,
            'delivery_fee': obj.delivery_fee,
            'total_amount': obj.total_amount
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
            'service_mode',
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
        extra_kwargs = {
            'tailor': {'required': False, 'allow_null': True}
        }

    def validate_items(self,value):
        # Get order_type from initial_data
        order_type = self.initial_data.get('order_type', 'fabric_only')
        
        # For measurement_service orders, allow items without fabric
        if order_type == 'measurement_service':
            if not value or len(value)==0:
                raise serializers.ValidationError(
                    "Measurement orders must specify at least one person to measure"
                )
            
            customer = self.context.get('request').user
            validated_items = []
            
            for item_data in value:
                family_member = item_data.get('family_member')
                
                # Validate family member belongs to customer if specified
                if family_member and family_member.user != customer:
                    raise serializers.ValidationError(
                        f"Family member {family_member.name} must belong to the authenticated customer"
                    )
                
                # For measurement orders, set default values
                item_data['fabric'] = None
                item_data['quantity'] = 1
                item_data['unit_price'] = Decimal('0.00')
                validated_items.append(item_data)
            
            return validated_items
        
        # For regular orders (fabric_only, fabric_with_stitching), existing logic
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
        order_type = self.initial_data.get('order_type', 'fabric_only')
        service_mode = self.initial_data.get('service_mode', 'home_delivery')
        
        # For home_delivery measurement orders, tailor is optional (rider handles it)
        if order_type == 'measurement_service' and service_mode == 'home_delivery':
            if value is None:
                return None  # Allow null tailor for home delivery measurements
            # If tailor is provided, still validate it (fall through to validation below)
        
        # For all other cases, tailor is required
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
        """Validate custom_styles and enrich ID-only format with full details"""
        if value is None:
            return None
        
        if not isinstance(value, list):
            raise serializers.ValidationError("custom_styles must be an array")
        
        enriched_styles = []
        for idx, style in enumerate(value):
            if not isinstance(style, dict):
                raise serializers.ValidationError(f"custom_styles[{idx}] must be an object")
            
            # Scenario 1: ID-only format {"style_id": 8, "category": "collar"}
            if 'style_id' in style:
                style_id = style.get('style_id')
                try:
                    style_obj = CustomStyle.objects.select_related('category').get(id=style_id, is_active=True)
                    enriched_styles.append({
                        "style_type": style_obj.category.name,
                        "index": style_obj.display_order,
                        "label": style_obj.name,
                        "asset_path": style_obj.image.name if style_obj.image else ""
                    })
                except CustomStyle.DoesNotExist:
                    raise serializers.ValidationError(f"Custom style with ID {style_id} not found or inactive")
            
            # Scenario 2: Traditional format (for backward compatibility)
            else:
                required_fields = ['style_type', 'index', 'label', 'asset_path']
                for field in required_fields:
                    if field not in style:
                        raise serializers.ValidationError(
                            f"custom_styles[{idx}] must contain either 'style_id' or '{field}'"
                        )
                enriched_styles.append(style)
        
        return enriched_styles

    def validate(self, data):
        """Cross-field validation for service_mode and delivery_address"""
        service_mode = data.get('service_mode', 'home_delivery')
        delivery_address = data.get('delivery_address')
        
        # Check context for one-time address (current location)
        using_current_location = self.context.get('using_current_location', False)
        
        # Also check for flat location fields (delivery_latitude, delivery_longitude)
        has_flat_location = ('delivery_latitude' in self.initial_data and 
                            'delivery_longitude' in self.initial_data)
        
        if service_mode == 'home_delivery' and not delivery_address and not using_current_location and not has_flat_location:
            raise serializers.ValidationError({
                'delivery_address': 'Delivery address or location coordinates are required for home delivery orders.'
            })
            
        return data

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
            fabric=item_data.get('fabric')
            # Skip fabric processing for measurement orders (fabric is None)
            if fabric is not None:
                fabric_ids.append(fabric.id)

        # Only lock fabrics if there are any (not for measurement orders)
        if fabric_ids:
            #lock fabric to prevent race conditions
            locked_fabrics=Fabric.objects.select_for_update().filter(
                id__in=fabric_ids
            )
            fabric_dict={f.id:f for f in locked_fabrics}
            for item_data in items_data:
                fabric=item_data.get('fabric')
                if fabric is None:
                    # Measurement order item - no fabric
                    continue
                    
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
                'custom_styles': item_data.get('custom_styles'),  # Item-level custom styles
            })
        else:
            # Measurement orders - no fabric validation needed
            for item_data in items_data:
                items_with_fabrics.append({
                    'fabric': None,
                    'quantity': 1,
                    'unit_price': Decimal('0.00'),
                    'measurements': item_data.get('measurements', {}),
                    'custom_instructions': item_data.get('custom_instructions', ''),
                    'family_member': item_data.get('family_member'),
                    'custom_styles': item_data.get('custom_styles'),  # Item-level custom styles
                })
        # Get distance_km from validated_data if provided
        # Get distance_km from validated_data if provided
        distance_km = validated_data.pop('distance_km', None)
        if distance_km is not None:
            distance_km = float(distance_km)
        
        # Get order_type to pass to calculation service
        order_type = validated_data.get('order_type', 'fabric_only')
        service_mode = validated_data.get('service_mode', 'home_delivery')
        
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
            order_type=order_type,
            service_mode=service_mode
        )
        
        # Update validated_data with calculated totals (including stitching_price)
        validated_data.update(totals)
        order = Order.objects.create(**validated_data)
        
        # Handle measurement service orders differently
        if order_type == 'measurement_service':
            # Auto-mark as paid (free)
            order.is_free_measurement = True
            order.payment_status = 'paid'
            order.payment_method = 'cod'
            order.total_amount = Decimal('0.00')
            order.subtotal = Decimal('0.00')
            order.delivery_fee = Decimal('0.00')
            order.save()
            
            # Create order items (each represents a person to measure)
            for item_data in items_with_fabrics:
                OrderItem.objects.create(
                    order=order,
                    fabric=None,  # No fabric for measurement orders
                    quantity=1,
                    unit_price=Decimal('0.00'),
                    measurements=item_data.get('measurements', {}),
                    custom_instructions=item_data.get('custom_instructions', ''),
                    family_member=item_data.get('family_member'),
                    custom_styles=item_data.get('custom_styles'),  # Item-level custom styles
                )
        else:
            # Regular orders - create items with fabric and reduce stock
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
                    custom_styles=item_data.get('custom_styles'),  # Item-level custom styles
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
    stitching_completion_date = serializers.DateField(
        required=False,
        allow_null=True,
        help_text="Date when tailor expects to complete stitching"
    )
    stitching_completion_time = serializers.TimeField(
        required=False,
        allow_null=True,
        help_text="Time when tailor expects to complete stitching (optional)"
    )
    
    class Meta:
        model=Order
        fields=['status', 'rider_status', 'tailor_status', 'notes', 'appointment_date', 'appointment_time', 'custom_styles', 'stitching_completion_date', 'stitching_completion_time']
    
    def validate_custom_styles(self, value):
        """Validate custom_styles and enrich ID-only format with full details"""
        if value is None:
            return None
        
        if not isinstance(value, list):
            raise serializers.ValidationError("custom_styles must be an array")
        
        enriched_styles = []
        for idx, style in enumerate(value):
            if not isinstance(style, dict):
                raise serializers.ValidationError(f"custom_styles[{idx}] must be an object")
            
            # Scenario 1: ID-only format {"style_id": 8, "category": "collar"}
            if 'style_id' in style:
                style_id = style.get('style_id')
                try:
                    style_obj = CustomStyle.objects.select_related('category').get(id=style_id, is_active=True)
                    enriched_styles.append({
                        "style_type": style_obj.category.name,
                        "index": style_obj.display_order,
                        "label": style_obj.name,
                        "asset_path": style_obj.image.name if style_obj.image else ""
                    })
                except CustomStyle.DoesNotExist:
                    raise serializers.ValidationError(f"Custom style with ID {style_id} not found or inactive")
            
            # Scenario 2: Traditional format (for backward compatibility)
            else:
                required_fields = ['style_type', 'index', 'label', 'asset_path']
                for field in required_fields:
                    if field not in style:
                        raise serializers.ValidationError(
                            f"custom_styles[{idx}] must contain either 'style_id' or '{field}'"
                        )
                enriched_styles.append(style)
        
        return enriched_styles
    def validate_stitching_completion_date(self, value):
        """Validate stitching completion date is in the future"""
        if value:
            from django.utils import timezone
            today = timezone.now().date()
            if value < today:
                raise serializers.ValidationError("Stitching completion date must be today or in the future")
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
        else:
            # No status change, but other fields may have been updated
            # Save the instance to persist changes like stitching_completion_date
            instance.save()
        
        
        # Send push notifications for status changes
        # Track which status fields changed and call the appropriate notification methods
        try:
            from apps.notifications.services import NotificationService
            
            # Get old values before transition (from history if available, or use current values)
            # Note: The transition service already saved the order, so we need to get old values from before
            # We'll use the new_* variables we extracted earlier to determine what changed
            
            if new_rider_status is not None:
                # Rider status changed - notify customer, tailor, and rider
                # Get the old rider_status from history or use the current value
                from apps.orders.models import OrderHistory
                try:
                    latest_history = instance.history.filter(
                        rider_status__isnull=False
                    ).exclude(
                        rider_status=instance.rider_status
                    ).order_by('-created_at').first()
                    old_rider_status = latest_history.rider_status if latest_history else 'none'
                except:
                    old_rider_status = 'none'
                
                NotificationService.send_rider_status_notification(
                    order=instance,
                    old_rider_status=old_rider_status,
                    new_rider_status=instance.rider_status,
                    changed_by=user
                )
            
            if new_tailor_status is not None:
                # Tailor status changed - notify customer, tailor, and rider
                from apps.orders.models import OrderHistory
                try:
                    latest_history = instance.history.filter(
                        tailor_status__isnull=False
                    ).exclude(
                        tailor_status=instance.tailor_status
                    ).order_by('-created_at').first()
                    old_tailor_status = latest_history.tailor_status if latest_history else 'none'
                except:
                    old_tailor_status = 'none'
                
                NotificationService.send_tailor_status_notification(
                    order=instance,
                    old_tailor_status=old_tailor_status,
                    new_tailor_status=instance.tailor_status,
                    changed_by=user
                )
            
            if new_status is not None:
                # Main status changed - notify relevant parties
                from apps.orders.models import OrderHistory
                try:
                    latest_history = instance.history.filter(
                        status__isnull=False
                    ).exclude(
                        status=instance.status
                    ).order_by('-created_at').first()
                    old_status = latest_history.status if latest_history else 'pending'
                except:
                    old_status = 'pending'
                
                NotificationService.send_order_status_notification(
                    order=instance,
                    old_status=old_status,
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
    customer_name=serializers.SerializerMethodField()
    tailor_name = serializers.SerializerMethodField()
    items_count = serializers.IntegerField(read_only=True)
    custom_styles = serializers.SerializerMethodField()
    items = OrderItemSerializer(source='order_items', many=True, read_only=True)
    rider_status = serializers.CharField(read_only=True)
    tailor_status = serializers.CharField(read_only=True)
    status_info = serializers.SerializerMethodField()
    pricing_summary = serializers.SerializerMethodField()

    class Meta:
        model=Order
        fields = [
            'id',
            'order_number',
            'customer_name',
            'tailor_name',
            'order_type',
            'service_mode',
            'status',
            'rider_status',
            'tailor_status',
            'stitching_price',
            'total_amount',
            'pricing_summary',
            'payment_status',
            'appointment_date',
            'appointment_time',
            'stitching_completion_date',
            'stitching_completion_time',
            'custom_styles',
            'rider_measurements',
            'measurement_taken_at',
            'items_count',
            'items',
            'status_info',
            'created_at'
        ]

    def get_customer_name(self, obj):
        if not obj.customer:
            return 'Unknown'
        full_name = obj.customer.get_full_name().strip()
        return full_name if full_name else obj.customer.username

    def get_tailor_name(self, obj):
        if not obj.tailor:
            return None
        try:
            return obj.tailor.tailor_profile.shop_name
        except TailorProfile.DoesNotExist:
            return obj.tailor.username
    
    def get_pricing_summary(self, obj):
        """Return grouped pricing summary for consistency with detail view"""
        return {
            'subtotal': str(obj.subtotal),
            'stitching_price': str(obj.stitching_price),
            'tax_amount': str(obj.tax_amount),
            'delivery_fee': str(obj.delivery_fee),
            'total_amount': str(obj.total_amount),
        }
    
    def get_custom_styles(self, obj):
        """Return custom_styles with absolute URLs for images"""
        styles = obj.custom_styles if obj.custom_styles is not None else []
        if not styles:
            return []
            
        request = self.context.get('request')
        if not request:
            return styles
            
        import copy
        processed_styles = copy.deepcopy(styles)
        
        from django.conf import settings
        media_url = getattr(settings, 'MEDIA_URL', '/media/')
        
        for style in processed_styles:
            asset_path = style.get('asset_path')
            if asset_path and not (asset_path.startswith('http://') or asset_path.startswith('https://')):
                if not asset_path.startswith(media_url) and not asset_path.startswith('/'):
                    full_path = media_url + asset_path
                else:
                    full_path = asset_path
                style['asset_path'] = request.build_absolute_uri(full_path)
                
        return processed_styles
    
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
        
        # Add custom actions
        for custom_action in allowed_transitions.get('custom_actions', []):
            next_actions.append(custom_action)
        
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
        if obj.order_type == 'fabric_with_stitching':
            is_rider_measuring = obj.rider_status in ['on_way_to_measurement', 'measurement_taken']
            is_walk_in_measuring = obj.service_mode == 'walk_in' and obj.status in ['confirmed', 'in_progress']
            
            if is_rider_measuring or is_walk_in_measuring:
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
            'stitching_completion_date',
            'stitching_completion_time',
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
            
