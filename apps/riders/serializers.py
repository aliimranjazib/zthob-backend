from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.core.services import PhoneVerificationService
from .models import RiderProfile, RiderOrderAssignment, RiderProfileReview, RiderDocument
from apps.orders.models import Order
from apps.orders.serializers import OrderItemSerializer
from zthob.translations import get_language_from_request, translate_message

User = get_user_model()


class RiderDocumentSerializer(serializers.ModelSerializer):
    """Serializer for rider documents"""
    document_url = serializers.SerializerMethodField()
    
    class Meta:
        model = RiderDocument
        fields = [
            'id',
            'document_type',
            'document_url',
            'is_verified',
            'verified_at',
            'notes',
            'created_at',
        ]
        read_only_fields = ['id', 'is_verified', 'verified_at', 'created_at']
    
    def get_document_url(self, obj):
        """Get full URL for document image"""
        if obj.document_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.document_image.url)
            return obj.document_image.url
        return None


class RiderRegisterSerializer(serializers.ModelSerializer):
    """Serializer for rider registration - simplified like customer registration"""
    name = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['name', 'email', 'password', 'confirm_password', 'role']
        extra_kwargs = {
            'email': {'required': True},
        }
    
    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"password": "Passwords do not match"})
        return attrs
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('email must be unique')
        return value
    
    def create(self, validated_data):
        name = validated_data.pop("name")
        password = validated_data.pop("password")
        validated_data.pop('confirm_password')

        # Split name into first_name and last_name
        first_name, *last_name = name.split(" ", 1)
        validated_data["first_name"] = first_name
        validated_data["last_name"] = last_name[0] if last_name else ""

        # Set username = email
        validated_data["username"] = validated_data["email"]
        
        # Ensure role is RIDER
        validated_data["role"] = "RIDER"

        # Create user
        user = User.objects.create_user(password=password, **validated_data)
        
        # Create rider profile with name as full_name
        # phone_number will be set when rider verifies phone via OTP
        rider_profile = RiderProfile.objects.create(
            user=user,
            full_name=name,
            phone_number=""  # Empty string until migration is run, then can be None
        )
        
        # Create review record with 'draft' status
        RiderProfileReview.objects.create(
            profile=rider_profile,
            review_status='draft'
        )
        
        return user


class RiderProfileSerializer(serializers.ModelSerializer):
    """Serializer for rider profile with all information"""
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    is_phone_verified = serializers.BooleanField(source='user.phone_verified', read_only=True)
    phone_number = serializers.SerializerMethodField()  # Get from user.phone (verified phone)
    is_approved = serializers.BooleanField(read_only=True)
    review_status = serializers.CharField(read_only=True)
    documents = RiderDocumentSerializer(many=True, read_only=True)
    
    class Meta:
        model = RiderProfile
        fields = [
            # Basic Info
            'id',
            'username',
            'email',
            'is_phone_verified',
            'is_approved',
            'review_status',
            'full_name',
            'phone_number',
            'emergency_contact',
            
            # National Identity / Iqama
            'iqama_number',
            'iqama_expiry_date',
            
            # Driving License
            'license_number',
            'license_expiry_date',
            'license_type',
            
            # Vehicle Information
            'vehicle_type',
            'vehicle_plate_number_arabic',
            'vehicle_plate_number_english',
            'vehicle_make',
            'vehicle_model',
            'vehicle_year',
            'vehicle_color',
            'vehicle_registration_number',
            'vehicle_registration_expiry_date',
            
            # Insurance
            'insurance_provider',
            'insurance_policy_number',
            'insurance_expiry_date',
            
            # Status & Location
            'is_active',
            'is_available',
            'current_latitude',
            'current_longitude',
            
            # Statistics
            'total_deliveries',
            'rating',
            
            # Documents
            'documents',
            
            # Timestamps
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id', 'total_deliveries', 'rating', 'created_at', 'updated_at',
            'is_approved', 'review_status', 'is_phone_verified', 'documents', 'phone_number'
        ]
    
    def get_phone_number(self, obj):
        """Get verified phone number from user.phone"""
        return obj.user.phone if obj.user else None
    
    def to_representation(self, instance):
        """Add request context to nested serializers"""
        representation = super().to_representation(instance)
        request = self.context.get('request')
        if request and 'documents' in representation:
            # Re-serialize documents with request context
            documents = instance.documents.all()
            representation['documents'] = RiderDocumentSerializer(
                documents, many=True, context={'request': request}
            ).data
        return representation


class RiderProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating rider profile"""
    # phone_number is read-only - it comes from verified user.phone
    phone_number = serializers.SerializerMethodField()
    
    class Meta:
        model = RiderProfile
        fields = [
            # Basic Info
            'full_name',
            'phone_number',  # Read-only - cannot be updated via profile API (only through phone-verify)
            'emergency_contact',
            
            # National Identity / Iqama
            'iqama_number',
            'iqama_expiry_date',
            
            # Driving License
            'license_number',
            'license_expiry_date',
            'license_type',
            
            # Vehicle Information
            'vehicle_type',
            'vehicle_plate_number_arabic',
            'vehicle_plate_number_english',
            'vehicle_make',
            'vehicle_model',
            'vehicle_year',
            'vehicle_color',
            'vehicle_registration_number',
            'vehicle_registration_expiry_date',
            
            # Insurance
            'insurance_provider',
            'insurance_policy_number',
            'insurance_expiry_date',
            
            # Status & Location
            'is_available',
            'current_latitude',
            'current_longitude',
        ]
    
    def get_phone_number(self, obj):
        """Get verified phone number from user.phone"""
        return obj.user.phone if obj.user else None


class RiderProfileSubmissionSerializer(serializers.ModelSerializer):
    """Serializer for rider to submit profile for review"""
    
    class Meta:
        model = RiderProfile
        fields = [
            # Basic Info
            'full_name',
            'phone_number',
            'emergency_contact',
            
            # National Identity / Iqama
            'iqama_number',
            'iqama_expiry_date',
            
            # Driving License
            'license_number',
            'license_expiry_date',
            'license_type',
            
            # Vehicle Information
            'vehicle_type',
            'vehicle_plate_number_arabic',
            'vehicle_plate_number_english',
            'vehicle_make',
            'vehicle_model',
            'vehicle_year',
            'vehicle_color',
            'vehicle_registration_number',
            'vehicle_registration_expiry_date',
            
            # Insurance
            'insurance_provider',
            'insurance_policy_number',
            'insurance_expiry_date',
        ]
    
    def validate(self, attrs):
        # Ensure required fields are present for submission
        required_fields = [
            'full_name',
            'iqama_number',
            'license_number',
            'vehicle_type',
            'vehicle_plate_number_english',
            'vehicle_registration_number',
        ]
        
        missing_fields = []
        for field in required_fields:
            if not attrs.get(field):
                missing_fields.append(field.replace('_', ' ').title())
        
        if missing_fields:
            raise serializers.ValidationError({
                'required_fields': f"The following fields are required for submission: {', '.join(missing_fields)}"
            })
        
        return attrs


class RiderDocumentUploadSerializer(serializers.ModelSerializer):
    """Serializer for uploading rider documents"""
    
    class Meta:
        model = RiderDocument
        fields = [
            'document_type',
            'document_image',
        ]
    
    def validate_document_type(self, value):
        """Validate document type"""
        valid_types = [choice[0] for choice in RiderDocument.DOCUMENT_TYPE_CHOICES]
        if value not in valid_types:
            raise serializers.ValidationError(f"Invalid document type. Must be one of: {', '.join(valid_types)}")
        return value
    
    def create(self, validated_data):
        """Create or update document"""
        rider_profile = self.context['rider_profile']
        document_type = validated_data['document_type']
        
        # Get or create document
        document, created = RiderDocument.objects.update_or_create(
            rider_profile=rider_profile,
            document_type=document_type,
            defaults={
                'document_image': validated_data['document_image'],
                'is_verified': False,  # Reset verification when document is updated
                'verified_at': None,
                'verified_by': None,
            }
        )
        
        return document


class RiderProfileReviewSerializer(serializers.ModelSerializer):
    """Serializer for viewing rider profile review details."""
    user_email = serializers.EmailField(source='profile.user.email', read_only=True)
    user_name = serializers.CharField(source='profile.user.get_full_name', read_only=True)
    rider_name = serializers.CharField(source='profile.full_name', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.get_full_name', read_only=True)
    
    class Meta:
        model = RiderProfileReview
        fields = [
            'id', 'profile', 'user_email', 'user_name', 'rider_name',
            'review_status', 'submitted_at', 'reviewed_at', 
            'reviewed_by', 'reviewed_by_name', 'rejection_reason',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'profile', 'submitted_at', 'reviewed_at', 
            'reviewed_by', 'created_at', 'updated_at'
        ]


class RiderProfileReviewUpdateSerializer(serializers.ModelSerializer):
    """Serializer for admin to update review status."""
    
    class Meta:
        model = RiderProfileReview
        fields = ['review_status', 'rejection_reason']
    
    def validate_review_status(self, value):
        if value not in ['approved', 'rejected']:
            raise serializers.ValidationError("Review status must be 'approved' or 'rejected'")
        return value


class RiderProfileStatusSerializer(serializers.ModelSerializer):
    """Serializer for rider to check their profile review status."""
    
    class Meta:
        model = RiderProfileReview
        fields = [
            'review_status', 'submitted_at', 'reviewed_at', 
            'rejection_reason'
        ]
        read_only_fields = ['review_status', 'submitted_at', 'reviewed_at', 'rejection_reason']


class RiderOrderListSerializer(serializers.ModelSerializer):
    """Serializer for listing orders available for riders"""
    customer_name = serializers.SerializerMethodField()
    customer_phone = serializers.SerializerMethodField()
    tailor_name = serializers.SerializerMethodField()
    tailor_phone = serializers.SerializerMethodField()
    delivery_address = serializers.SerializerMethodField()
    items_count = serializers.SerializerMethodField()
    custom_styles = serializers.SerializerMethodField()
    items = OrderItemSerializer(source='order_items', many=True, read_only=True)
    tailor_status = serializers.CharField(read_only=True)
    status_info = serializers.SerializerMethodField()
    pricing_summary = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id',
            'order_number',
            'order_type',
            'status',
            'rider_status',
            'tailor_status',
            'payment_status',
            'total_amount',
            'pricing_summary',
            'customer_name',
            'customer_phone',
            'tailor_name',
            'tailor_phone',
            'delivery_address',
            'items_count',
            'items',
            'estimated_delivery_date',
            'appointment_date',
            'appointment_time',
            'custom_styles',
            'special_instructions',
            'status_info',
            'created_at',
        ]
    
    def get_pricing_summary(self, obj):
        """Return grouped pricing summary for consistency"""
        return {
            'subtotal': str(obj.subtotal),
            'stitching_price': str(obj.stitching_price),
            'tax_amount': str(obj.tax_amount),
            'delivery_fee': str(obj.delivery_fee),
            'total_amount': str(obj.total_amount),
        }
    
    def get_customer_name(self, obj):
        if not obj.customer:
            return 'Unknown'
        full_name = obj.customer.get_full_name().strip()
        return full_name if full_name else obj.customer.username
    
    def get_customer_phone(self, obj):
        return obj.customer.phone if obj.customer else None
    
    def get_tailor_name(self, obj):
        try:
            if hasattr(obj.tailor, 'tailor_profile') and obj.tailor.tailor_profile:
                return obj.tailor.tailor_profile.shop_name or obj.tailor.username
        except:
            pass
        return obj.tailor.username if obj.tailor else 'Unknown'
    
    def get_tailor_phone(self, obj):
        """Get tailor phone (verified phone from user account)"""
        return obj.tailor.phone if obj.tailor else None
    
    def get_delivery_address(self, obj):
        """Return delivery address matching customer address structure."""
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
    
    def get_items_count(self, obj):
        return obj.items_count
    
    def get_custom_styles(self, obj):
        """Return custom_styles, or empty array if None"""
        return obj.custom_styles if obj.custom_styles is not None else []
    
    def get_status_info(self, obj):
        """Get status information including next available actions for riders"""
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
        """Build action object for status transition - reuse from OrderSerializer"""
        from apps.orders.serializers import OrderSerializer
        # Pass self to preserve context (request) for translation
        serializer_instance = OrderSerializer(context=self.context)
        return OrderSerializer._build_status_action(serializer_instance, action_type, value, user_role)
    
    def _calculate_status_progress(self, obj):
        """Calculate progress percentage - reuse from OrderSerializer"""
        from apps.orders.serializers import OrderSerializer
        return OrderSerializer._calculate_status_progress(OrderSerializer(), obj)


class RiderOrderDetailSerializer(serializers.ModelSerializer):
    """Serializer for order details for riders"""
    customer_info = serializers.SerializerMethodField()
    order_recipient = serializers.SerializerMethodField()
    all_recipients = serializers.SerializerMethodField()
    tailor_info = serializers.SerializerMethodField()
    delivery_address = serializers.SerializerMethodField()
    items = serializers.SerializerMethodField()
    assignment_status = serializers.SerializerMethodField()
    custom_styles = serializers.SerializerMethodField()
    rider_status = serializers.CharField(read_only=True)
    tailor_status = serializers.CharField(read_only=True)
    status_info = serializers.SerializerMethodField()
    pricing_summary = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id',
            'order_number',
            'order_type',
            'status',
            'rider_status',
            'tailor_status',
            'payment_status',
            'payment_method',
            'total_amount',
            'subtotal',
            'tax_amount',
            'delivery_fee',
            'pricing_summary',
            'customer_info',
            'order_recipient',
            'all_recipients',
            'tailor_info',
            'delivery_address',
            'items',
            'assignment_status',
            'estimated_delivery_date',
            'actual_delivery_date',
            'appointment_date',
            'appointment_time',
            'custom_styles',
            'special_instructions',
            'measurement_taken_at',
            'status_info',
            'created_at',
        ]
    
    def get_pricing_summary(self, obj):
        """Return grouped pricing summary for consistency"""
        return {
            'subtotal': str(obj.subtotal),
            'stitching_price': str(obj.stitching_price),
            'tax_amount': str(obj.tax_amount),
            'delivery_fee': str(obj.delivery_fee),
            'total_amount': str(obj.total_amount),
        }
    
    def get_customer_info(self, obj):
        if obj.customer:
            full_name = obj.customer.get_full_name().strip()
            return {
                'id': obj.customer.id,
                'username': obj.customer.username,
                'full_name': full_name if full_name else obj.customer.username,
                'email': obj.customer.email,
                'phone': obj.customer.phone,
            }
        return None
    
    def get_all_recipients(self, obj):
        """Get all recipients for this order as an array."""
        return self._collect_recipients(obj)

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
                    if obj.customer:
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

    def get_tailor_info(self, obj):
        """Return tailor info with structured address from Address model."""
        if obj.tailor:
            try:
                tailor_profile = obj.tailor.tailor_profile
                
                # Get structured address from Address model (same format as delivery_address)
                from apps.customers.models import Address
                tailor_address = None
                # Get address from user's addresses (will use prefetched data if available)
                # First try to get the default address
                address = next((addr for addr in obj.tailor.addresses.all() if addr.is_default), None)
                # If no default address, get the first address
                if not address:
                    address = next(iter(obj.tailor.addresses.all()), None)
                
                if address:
                    tailor_address = {
                        'id': address.id,
                        'latitude': address.latitude,
                        'longitude': address.longitude,
                        'address': address.address or '',
                        'extra_info': address.extra_info or '',
                        'is_default': address.is_default,
                        'address_tag': address.address_tag,
                    }
                
                return {
                    'id': obj.tailor.id,
                    'username': obj.tailor.username,
                    'shop_name': tailor_profile.shop_name if tailor_profile else None,
                    'contact_number': obj.tailor.phone,
                    'address': tailor_address,  # Structured address matching delivery_address format
                }
            except:
                return {
                    'id': obj.tailor.id,
                    'username': obj.tailor.username,
                }
        return None
    
    def get_delivery_address(self, obj):
        """Return delivery address matching customer address structure."""
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
    
    def get_items(self, obj):
        items = []
        request = self.context.get('request')
        for item in obj.order_items.all():
            fabric_image_url = None
            if item.fabric:
                # Get primary image URL
                primary_image = item.fabric.primary_image
                if primary_image:
                    if request:
                        fabric_image_url = request.build_absolute_uri(primary_image.url)
                    else:
                        fabric_image_url = primary_image.url
            
            items.append({
                'id': item.id,
                'fabric_name': item.fabric.name if item.fabric else 'Unknown',
                'fabric_sku': item.fabric.sku if item.fabric else None,
                'fabric_image_url': fabric_image_url,
                'quantity': item.quantity,
                'unit_price': str(item.unit_price),
                'total_price': str(item.total_price),
                'family_member': item.family_member.id if item.family_member else None,
                'family_member_name': self._get_item_recipient_name(item),
                'custom_styles': OrderItemSerializer(item, context=self.context).data.get('custom_styles', []),
            })
        return items

    def _get_item_recipient_name(self, item):
        if item.family_member:
            return item.family_member.name
        
        # If no family member, return customer name with (Self) tag
        try:
            customer = item.order.customer
            name = customer.get_full_name() or customer.username
            return f"{name} (Self)"
        except:
            return "Customer (Self)"
    
    def get_assignment_status(self, obj):
        try:
            assignment = obj.rider_assignment
            return {
                'status': assignment.status,
                'accepted_at': assignment.accepted_at.isoformat() if assignment.accepted_at else None,
                'started_at': assignment.started_at.isoformat() if assignment.started_at else None,
                'completed_at': assignment.completed_at.isoformat() if assignment.completed_at else None,
                'notes': assignment.notes,
            }
        except RiderOrderAssignment.DoesNotExist:
            return None
    
    def get_custom_styles(self, obj):
        """Return custom_styles, or empty array if None"""
        return obj.custom_styles if obj.custom_styles is not None else []
    
    def get_status_info(self, obj):
        """Get status information including next available actions for riders"""
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
        """Build action object for status transition - reuse from OrderSerializer"""
        from apps.orders.serializers import OrderSerializer
        # Pass self to preserve context (request) for translation
        serializer_instance = OrderSerializer(context=self.context)
        return OrderSerializer._build_status_action(serializer_instance, action_type, value, user_role)
    
    def _calculate_status_progress(self, obj):
        """Calculate progress percentage - reuse from OrderSerializer"""
        from apps.orders.serializers import OrderSerializer
        return OrderSerializer._calculate_status_progress(OrderSerializer(), obj)


class RiderAcceptOrderSerializer(serializers.Serializer):
    """Serializer for rider accepting an order"""
    order_id = serializers.IntegerField(required=True)
    
    def validate_order_id(self, value):
        try:
            order = Order.objects.get(id=value)
            if order.payment_status != 'paid':
                raise serializers.ValidationError("Order payment must be paid before rider can accept it")
            if order.rider is not None:
                raise serializers.ValidationError("Order is already assigned to another rider")
            return value
        except Order.DoesNotExist:
            raise serializers.ValidationError("Order does not exist")


class RiderAddMeasurementsSerializer(serializers.Serializer):
    """Serializer for rider adding measurements"""
    family_member = serializers.IntegerField(required=False, allow_null=True, help_text="ID of family member being measured. Null means customer.")
    title = serializers.CharField(required=False, allow_blank=True, help_text="Title for measurements (e.g. 'Wedding Thobe')")
    measurements = serializers.JSONField(required=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_measurements(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Measurements must be a dictionary/JSON object")
        if not value:
            raise serializers.ValidationError("Measurements cannot be empty")
        return value


class RiderUpdateOrderStatusSerializer(serializers.Serializer):
    """Serializer for rider updating order status"""
    rider_status = serializers.ChoiceField(
        choices=[
            'accepted',  # Rider accepts order
            'on_way_to_pickup',  # Rider on way to pickup
            'picked_up',  # Rider picked up
            'on_way_to_delivery',  # Rider on way to delivery
            'on_way_to_measurement',  # Rider on way to take measurements (stitching only)
            'measuring',  # Rider is taking measurements (stitching only)
            'measurement_taken',  # Rider took measurements (stitching only)
            'delivered',  # Rider delivered
        ],
        required=True
    )
    notes = serializers.CharField(required=False, allow_blank=True)
