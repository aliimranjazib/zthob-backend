from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.core.services import PhoneVerificationService
from .models import RiderProfile, RiderOrderAssignment, RiderProfileReview, RiderDocument
from apps.orders.models import Order
from apps.orders.serializers import OrderItemSerializer

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
    """Serializer for rider registration"""
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    phone_number = serializers.CharField(required=True)
    full_name = serializers.CharField(required=True)
    
    class Meta:
        model = User
        fields = [
            'username',
            'email',
            'password',
            'password_confirm',
            'phone_number',
            'full_name',
            'first_name',
            'last_name',
        ]
        extra_kwargs = {
            'email': {'required': True},
        }
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Passwords do not match"})
        return attrs
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        password_confirm = validated_data.pop('password_confirm')
        phone_number = validated_data.pop('phone_number')
        full_name = validated_data.pop('full_name')
        
        # Create user with RIDER role
        user = User.objects.create_user(
            role='RIDER',
            password=password,
            **validated_data
        )
        
        # Create rider profile
        rider_profile = RiderProfile.objects.create(
            user=user,
            phone_number=phone_number,
            full_name=full_name
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
            'is_approved', 'review_status', 'is_phone_verified', 'documents'
        ]
    
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
            
            # Status & Location
            'is_available',
            'current_latitude',
            'current_longitude',
        ]


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
            'phone_number',
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
    
    class Meta:
        model = Order
        fields = [
            'id',
            'order_number',
            'order_type',
            'status',
            'payment_status',
            'total_amount',
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
            'created_at',
        ]
    
    def get_customer_name(self, obj):
        return obj.customer.get_full_name() if obj.customer else obj.customer.username if obj.customer else 'Unknown'
    
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
        try:
            if hasattr(obj.tailor, 'tailor_profile') and obj.tailor.tailor_profile:
                return obj.tailor.tailor_profile.contact_number
        except:
            pass
        return None
    
    def get_delivery_address(self, obj):
        if obj.delivery_address:
            parts = []
            if obj.delivery_address.street:
                parts.append(obj.delivery_address.street)
            if obj.delivery_address.city:
                parts.append(obj.delivery_address.city)
            if obj.delivery_address.state_province:
                parts.append(obj.delivery_address.state_province)
            if obj.delivery_address.country:
                parts.append(obj.delivery_address.country)
            return ', '.join(parts) if parts else None
        return None
    
    def get_items_count(self, obj):
        return obj.items_count
    
    def get_custom_styles(self, obj):
        """Return custom_styles, or empty array if None"""
        return obj.custom_styles if obj.custom_styles is not None else []


class RiderOrderDetailSerializer(serializers.ModelSerializer):
    """Serializer for order details for riders"""
    customer_info = serializers.SerializerMethodField()
    tailor_info = serializers.SerializerMethodField()
    delivery_address = serializers.SerializerMethodField()
    items = serializers.SerializerMethodField()
    assignment_status = serializers.SerializerMethodField()
    custom_styles = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id',
            'order_number',
            'order_type',
            'status',
            'payment_status',
            'payment_method',
            'total_amount',
            'subtotal',
            'tax_amount',
            'delivery_fee',
            'customer_info',
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
            'rider_measurements',
            'measurement_taken_at',
            'created_at',
        ]
    
    def get_customer_info(self, obj):
        if obj.customer:
            return {
                'id': obj.customer.id,
                'username': obj.customer.username,
                'full_name': obj.customer.get_full_name(),
                'email': obj.customer.email,
                'phone': obj.customer.phone,
            }
        return None
    
    def get_tailor_info(self, obj):
        if obj.tailor:
            try:
                tailor_profile = obj.tailor.tailor_profile
                return {
                    'id': obj.tailor.id,
                    'username': obj.tailor.username,
                    'shop_name': tailor_profile.shop_name if tailor_profile else None,
                    'contact_number': tailor_profile.contact_number if tailor_profile else None,
                    'address': tailor_profile.address if tailor_profile else None,
                }
            except:
                return {
                    'id': obj.tailor.id,
                    'username': obj.tailor.username,
                }
        return None
    
    def get_delivery_address(self, obj):
        if obj.delivery_address:
            return {
                'id': obj.delivery_address.id,
                'street': obj.delivery_address.street,
                'city': obj.delivery_address.city,
                'state_province': obj.delivery_address.state_province,
                'zip_code': obj.delivery_address.zip_code,
                'country': obj.delivery_address.country,
                'formatted_address': obj.delivery_address.formatted_address,
                'latitude': float(obj.delivery_address.latitude) if obj.delivery_address.latitude else None,
                'longitude': float(obj.delivery_address.longitude) if obj.delivery_address.longitude else None,
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
            })
        return items
    
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
    status = serializers.ChoiceField(
        choices=[
            'measuring',  # For fabric_with_stitching: after taking measurements
            'ready_for_delivery',  # For fabric_only: after picking from tailor
            'delivered',  # After delivery
        ],
        required=True
    )
    notes = serializers.CharField(required=False, allow_blank=True)
