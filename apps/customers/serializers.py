from rest_framework.serializers import ModelSerializer
from rest_framework import serializers

from apps.accounts.serializers import UserProfileSerializer
from apps.tailors.models import Fabric, TailorProfile, FabricCategory
from apps.tailors.serializers import FabricCategorySerializer, FabricImageSerializer
from apps.tailors.serializers.catalog import FabricTypeBasicSerializer, FabricTagBasicSerializer
from apps.customers.models import Address, CustomerProfile, FamilyMember, FabricFavorite

# ============================================================================
# LIGHTWEIGHT HOME SERIALIZERS (OPTIMIZED FOR PERFORMANCE)
# ============================================================================

class SimplifiedAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ['id', 'latitude', 'longitude', 'address', 'city']

class TailorHomeSerializer(serializers.ModelSerializer):
    """Super lightweight serializer for Home Page lists."""
    id = serializers.ReadOnlyField(source='user.id')
    shop_image_url = serializers.SerializerMethodField()
    city = serializers.SerializerMethodField()
    address = serializers.SerializerMethodField()
    is_express = serializers.BooleanField(source='is_express_delivery_enabled', read_only=True)

    class Meta:
        model = TailorProfile
        fields = [
            'id', 'shop_name', 'shop_image_url', 
            'avg_overall_satisfaction', 'rating_count', 'city', 'address',
            'is_express'
        ]

    def get_shop_image_url(self, obj):
        if obj.shop_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.shop_image.url)
            return obj.shop_image.url
        return None

    def get_city(self, obj):
        """Get city from pre-fetched addresses to avoid N+1."""
        # Try pre-fetched addresses first (populated via Prefetch in CustomerHomeAPIView)
        user_addresses = getattr(obj.user, 'addresses', None)
        if user_addresses is not None and hasattr(user_addresses, 'all'):
            # Convert to list to use Python iteration on pre-fetched data
            addresses = list(user_addresses.all())
            addr = next((a for a in addresses if a.is_default), None)
            if not addr and addresses:
                addr = addresses[0]
            if addr: 
                return addr.city
        
        # Fallback only if pre-fetch failed (prevents N+1 in most cases)
        return "Riyadh"

    def get_address(self, obj):
        """Get formatted address from pre-fetched data, resolving 'Instance of Address' issue."""
        user_addresses = getattr(obj.user, 'addresses', None)
        if user_addresses is not None and hasattr(user_addresses, 'all'):
            addresses = list(user_addresses.all())
            addr = next((a for a in addresses if a.is_default), None)
            if not addr and addresses:
                addr = addresses[0]
            
            if addr:
                # Prefer the full address text if available, otherwise format street/city
                return addr.address or f"{addr.street}, {addr.city}"
        
        # Fallback to model field if it's not the corrupted 'Instance of' string
        if obj.address and "Instance of" not in str(obj.address):
            return obj.address
            
        return ""


class FabricCategoryHomeSerializer(serializers.ModelSerializer):
    """Category serializer for Home page that includes sample fabric images."""
    fabric_images = serializers.SerializerMethodField()

    class Meta:
        model = FabricCategory
        fields = ["id", "name", "slug", "image", "fabric_images"]

    def get_fabric_images(self, obj):
        # Use pre-fetched sample_fabrics if available to avoid N+1 queries
        request = self.context.get('request')
        
        sample_fabrics = getattr(obj, 'sample_fabrics', None)
        if sample_fabrics is not None:
            fabrics = sample_fabrics[:4]
        else:
            fabrics = obj.fabrics.filter(is_active=True).prefetch_related('gallery')[:4]
        
        images = []
        for fabric in fabrics:
            # Try to get primary image or first available
            img = fabric.primary_image
            if img:
                image_url = img.url
                if request:
                    image_url = request.build_absolute_uri(image_url)
                images.append(image_url)
        
        return images

class FabricHomeSerializer(serializers.ModelSerializer):
    """Super lightweight serializer for Home Page lists."""
    image_url = serializers.SerializerMethodField()
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = Fabric
        fields = [
            'id', 'name', 'price', 'stitching_price', 
            'image_url', 'category_name', 'is_on_sale', 
            'discount_price', 'is_sale_active'
        ]

    def get_image_url(self, obj):
        first_image = obj.gallery.first()
        if first_image and first_image.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(first_image.image.url)
            return first_image.image.url
        return None


class FabricCatalogSerializer(serializers.ModelSerializer):
    gallery = FabricImageSerializer(many=True, read_only=True)
    category = FabricCategorySerializer(read_only=True)
    fabric_type=FabricTypeBasicSerializer(read_only=True)
    tags=FabricTagBasicSerializer(many=True, read_only=True)
    tailor = TailorHomeSerializer(read_only=True)
    is_favorited = serializers.BooleanField(read_only=True, default=False)
    favorite_count = serializers.IntegerField(read_only=True, default=0)
    
    class Meta:
        model=Fabric
        fields = [
            "id",
            "name",
            "description",
            "sku",
            "price",
            "stitching_price",
            "stock",
            "is_active",
            "seasons",
            "fabric_type",  
            "tags", 
            "gallery",
            "category",
            "tailor",
            "is_on_sale",
            "discount_price",
            "sale_start",
            "sale_end",
            "is_sale_active",
            "is_featured",
            "sales_count",
            "is_favorited",
            "favorite_count",
        ]
    

class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = '__all__'
        read_only_fields = ['user']
    
    def validate_address_tag(self, value):
        """Validate address_tag field"""
        valid_tags = [choice[0] for choice in Address.ADDRESS_TAG_CHOICES]
        if value not in valid_tags:
            raise serializers.ValidationError(f"Invalid address_tag. Must be one of: {', '.join(valid_tags)}")
        return value

class AddressCreateSerializer(serializers.ModelSerializer):
    """Simplified serializer for address creation with only required fields."""
    address = serializers.CharField(max_length=255, help_text="Full address text")
    address_tag = serializers.ChoiceField(choices=Address.ADDRESS_TAG_CHOICES, default='home', help_text="Address type: home, office, work, other")
    is_default = serializers.BooleanField(default=False, help_text="Whether this is the default address")
    
    class Meta:
        model = Address
        fields = ['latitude', 'longitude', 'address', 'extra_info', 'address_tag', 'is_default']
    
    def validate_address_tag(self, value):
        """Validate address_tag field"""
        valid_tags = [choice[0] for choice in Address.ADDRESS_TAG_CHOICES]
        if value not in valid_tags:
            raise serializers.ValidationError(f"Invalid address_tag. Must be one of: {', '.join(valid_tags)}")
        return value
    
    def create(self, validated_data):
        """Create address with simplified data structure."""
        user = self.context.get('request').user
        
        # Get address text and save it to address field
        address_text = validated_data.get('address', '')
        is_default = validated_data.pop('is_default', False)
        
        # Set default values for required fields
        validated_data.update({
            'user': user,
            'address': address_text,  # Save to address field
            'street': address_text,  # Also save to street for backward compatibility
            'city': 'Riyadh',  # Default city, can be updated later
            'country': 'Saudi Arabia',
            'is_default': is_default,
        })
        
        # If this address is being set as default, make other addresses non-default
        if is_default:
            Address.objects.filter(user=user, is_default=True).update(is_default=False)
        
        return super().create(validated_data)

class AddressResponseSerializer(serializers.ModelSerializer):
    """Simplified response serializer for addresses."""
    
    class Meta:
        model = Address
        fields = ['id', 'latitude', 'longitude', 'address', 'extra_info', 'is_default', 'address_tag']
    
    
class FamilyMemberCreateSerializer(serializers.ModelSerializer):
    """Simplified serializer for creating family members - only requires name"""
    class Meta:
        model = FamilyMember
        fields = ['name']
    
    def create(self, validated_data):
        """Create family member with only name"""
        user = self.context.get("user")
        family_member = FamilyMember.objects.create(
            user=user,
            **validated_data
        )
        return family_member


class FamilyMemberSimpleResponseSerializer(serializers.ModelSerializer):
    """Simplified response serializer - only returns id and name"""
    class Meta:
        model = FamilyMember
        fields = ['id', 'name']


class FamilyMemberSerializer(serializers.ModelSerializer):
    address = AddressCreateSerializer(required=False, write_only=True)
    address_response = AddressResponseSerializer(source='address', read_only=True)
    
    class Meta:
        model=FamilyMember
        fields = ['id', 'name', 'measurements', 'address', 'address_response']
        read_only_fields = ['user']
        
    def to_representation(self, instance):
        """Custom representation to use address_response as address in output."""
        data = super().to_representation(instance)
        # Replace 'address_response' with 'address' in the output
        if 'address_response' in data:
            data['address'] = data.pop('address_response')
        return data
        
    def create(self, validated_data):
        user = self.context.get("user")

        address_data = validated_data.pop("address", None)

        family_member = FamilyMember.objects.create(
            user=user,
            **validated_data
        )

        if address_data:
            # Create a mock request object for AddressCreateSerializer
            class MockRequest:
                def __init__(self, user):
                    self.user = user
            
            mock_request = MockRequest(user)
            address_serializer = AddressCreateSerializer(data=address_data, context={'request': mock_request})
            if address_serializer.is_valid():
                address = address_serializer.save()
                family_member.address = address
                family_member.save()

        return family_member

    def update(self,instance,validated_data):
        address_data=validated_data.pop('address',None)
        #update family member field
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if address_data:
            # Create a mock request object for AddressCreateSerializer
            class MockRequest:
                def __init__(self, user):
                    self.user = user
            
            user = self.context.get("user")
            mock_request = MockRequest(user)
            
            if instance.address:
                # Use AddressCreateSerializer to properly handle the address update
                address_serializer = AddressCreateSerializer(data=address_data, context={'request': mock_request})
                if address_serializer.is_valid():
                    address_data_validated = address_serializer.validated_data
                    address_text = address_data_validated.get('address', instance.address.address)
                    
                    instance.address.address = address_text
                    instance.address.street = address_text  # Also update street for backward compatibility
                    instance.address.latitude = address_data_validated.get('latitude', instance.address.latitude)
                    instance.address.longitude = address_data_validated.get('longitude', instance.address.longitude)
                    instance.address.extra_info = address_data_validated.get('extra_info', instance.address.extra_info)
                    instance.address.address_tag = address_data_validated.get('address_tag', instance.address.address_tag)
                    instance.address.save()
            else:
                # Create new address if none exists
                address_serializer = AddressCreateSerializer(data=address_data, context={'request': mock_request})
                if address_serializer.is_valid():
                    address = address_serializer.save()
                    instance.address = address
                    instance.save()
        return instance


class CustomerProfileSerializer(serializers.ModelSerializer):
    user=UserProfileSerializer(read_only=True)
    default_address = AddressResponseSerializer(read_only=True)
    addresses = AddressResponseSerializer(source='user.addresses', many=True, read_only=True)
    phone_verified = serializers.SerializerMethodField()
    dob = serializers.DateField(source='date_of_birth', required=False, allow_null=True)
    class Meta:
        model=CustomerProfile
        fields = ['user', 'default_address','addresses','phone_verified', 'dob', 'gender', 'measurements']

    def get_phone_verified(self, obj):
        """Get phone verification status from user"""
        return obj.user.phone_verified


class FabricFavoriteSerializer(serializers.ModelSerializer):
    """Serializer for FabricFavorite model."""
    fabric = FabricCatalogSerializer(read_only=True)
    fabric_id = serializers.IntegerField(write_only=True, required=False)
    
    class Meta:
        model = FabricFavorite
        fields = ['id', 'fabric', 'fabric_id', 'created_at']
        read_only_fields = ['id', 'created_at']


# ============================================================================
# MEASUREMENT SERIALIZERS
# ============================================================================

class OrderMeasurementItemSerializer(serializers.Serializer):
    """Serializer for a single order measurement entry"""
    order_id = serializers.IntegerField()
    order_number = serializers.CharField()
    order_type = serializers.CharField()
    measurements = serializers.DictField()
    measurement_taken_at = serializers.DateTimeField()
    order_status = serializers.CharField()
    rider_status = serializers.CharField()
    order_created_at = serializers.DateTimeField()
    tailor_name = serializers.CharField(required=False, allow_null=True)
    appointment_date = serializers.DateField(required=False, allow_null=True)
    appointment_time = serializers.TimeField(required=False, allow_null=True)


class CustomerMeasurementSerializer(serializers.Serializer):
    """Serializer for customer's own measurements"""
    order_id = serializers.IntegerField()
    order_number = serializers.CharField()
    order_type = serializers.CharField()
    recipient_type = serializers.CharField()
    recipient_id = serializers.IntegerField()
    recipient_name = serializers.CharField()
    measurements = serializers.DictField()
    measurement_taken_at = serializers.DateTimeField()
    order_status = serializers.CharField()
    rider_status = serializers.CharField()
    order_created_at = serializers.DateTimeField()


class FamilyMemberMeasurementSerializer(serializers.Serializer):
    """Serializer for family member measurements"""
    order_id = serializers.IntegerField()
    order_number = serializers.CharField()
    order_type = serializers.CharField()
    recipient_type = serializers.CharField()
    recipient_id = serializers.IntegerField()
    recipient_name = serializers.CharField()
    measurements = serializers.DictField()
    measurement_taken_at = serializers.DateTimeField()
    order_status = serializers.CharField()
    rider_status = serializers.CharField()
    order_created_at = serializers.DateTimeField()


class FamilyMemberSummarySerializer(serializers.Serializer):
    """Serializer for family member summary in list view"""
    family_member_id = serializers.IntegerField()
    family_member_name = serializers.CharField()
    total_measurements = serializers.IntegerField()
    latest_measurement_date = serializers.DateTimeField(required=False, allow_null=True)
    has_stored_measurements = serializers.BooleanField()


class StoredProfileMeasurementSerializer(serializers.Serializer):
    """Serializer for stored profile measurements"""
    recipient_type = serializers.CharField()
    recipient_id = serializers.IntegerField()
    recipient_name = serializers.CharField()
    measurements = serializers.DictField()
    last_updated = serializers.DateTimeField(required=False, allow_null=True)
    note = serializers.CharField()


class CustomerMeasurementsListSerializer(serializers.Serializer):
    """Serializer for the complete measurements list response"""
    customer_measurements = CustomerMeasurementSerializer(many=True, required=False)
    family_member_measurements = FamilyMemberMeasurementSerializer(many=True, required=False)
    family_members_summary = FamilyMemberSummarySerializer(many=True, required=False)
    stored_profile_measurements = StoredProfileMeasurementSerializer(many=True, required=False)
    summary = serializers.DictField()


class FamilyMemberMeasurementsDetailSerializer(serializers.Serializer):
    """Serializer for family member specific measurements detail"""
    family_member = serializers.DictField()
    order_measurements = OrderMeasurementItemSerializer(many=True)
    stored_profile_measurements = serializers.DictField(required=False, allow_null=True)

class RecipientMeasurementStatsSerializer(serializers.Serializer):
    """Statistics for a recipient's measurements"""
    total_orders = serializers.IntegerField()
    last_measured_at = serializers.DateTimeField(required=False, allow_null=True)


class RecipientMeasurementProfileSerializer(serializers.Serializer):
    """Complete measurement profile for a single recipient"""
    recipient_type = serializers.ChoiceField(choices=['customer', 'family_member'])
    recipient_id = serializers.IntegerField()
    recipient_name = serializers.CharField()
    recipient_relationship = serializers.CharField(required=False, allow_null=True)
    recipient_gender = serializers.CharField(required=False, allow_null=True)
    
    # The current active/stored measurements (from profile)
    current_measurements = serializers.DictField(required=False, allow_null=True)
    current_measurements_note = serializers.CharField(required=False, allow_null=True)
    
    # History of measurements from orders
    order_history = OrderMeasurementItemSerializer(many=True)
    
    # Summary stats
    stats = RecipientMeasurementStatsSerializer()


class RecipientMeasurementsResponseSerializer(serializers.Serializer):
    """New top-level response serializer"""
    recipients = RecipientMeasurementProfileSerializer(many=True)
    global_summary = serializers.DictField()


class CustomerHomeSerializer(serializers.Serializer):
    banners = serializers.ListField(child=serializers.DictField())
    categories = FabricCategoryHomeSerializer(many=True)
    new_tailors = TailorHomeSerializer(many=True)
    top_rated_tailors = TailorHomeSerializer(many=True)
    most_popular_tailors = TailorHomeSerializer(many=True)
    featured_tailors = TailorHomeSerializer(many=True)
    express_delivery_tailors = TailorHomeSerializer(many=True)
    flash_sale_fabrics = FabricHomeSerializer(many=True)
    new_fabrics = FabricHomeSerializer(many=True)