from rest_framework.serializers import ModelSerializer
from rest_framework import serializers

from apps.accounts.serializers import UserProfileSerializer
from apps.tailors.models import Fabric
from apps.tailors.serializers import FabricCategorySerializer, FabricImageSerializer, TailorProfileSerializer
from apps.tailors.serializers.catalog import FabricTypeBasicSerializer,FabricTagBasicSerializer
from apps.customers.models import Address, CustomerProfile, FamilyMember, FabricFavorite


class FabricCatalogSerializer(serializers.ModelSerializer):
    fabric_image = serializers.SerializerMethodField()
    gallery = FabricImageSerializer(many=True, read_only=True)
    category = FabricCategorySerializer(read_only=True)
    fabric_type=FabricTypeBasicSerializer(read_only=True)
    tags=FabricTagBasicSerializer(many=True, read_only=True)
    tailor = TailorProfileSerializer(read_only=True)
    is_favorited = serializers.SerializerMethodField()
    favorite_count = serializers.SerializerMethodField()
    
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
            "fabric_image",
            "gallery",
            "category",
            "tailor",
            "is_favorited",
            "favorite_count",
        ]
    

    def get_fabric_image(self, obj) -> str | None:
        request = self.context.get("request", None)
        if request:
            return request.build_absolute_uri(obj.fabric_image.url) if obj.fabric_image else None
        return obj.fabric_image.url if obj.fabric_image else None
    
    def get_is_favorited(self, obj) -> bool:
        """Check if the current user has favorited this fabric."""
        request = self.context.get("request", None)
        if request and request.user.is_authenticated:
            return FabricFavorite.objects.filter(user=request.user, fabric=obj).exists()
        return False
    
    def get_favorite_count(self, obj) -> int:
        """Get the total number of users who favorited this fabric."""
        return obj.favorites.count()
    

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
        fields = ['id', 'name', 'gender', 'relationship', 'measurements', 'address', 'address_response']
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
        fields = ['user', 'default_address','addresses','phone_verified', 'dob', 'gender']

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
    recipient_relationship = serializers.CharField(required=False, allow_null=True)
    recipient_gender = serializers.CharField(required=False, allow_null=True)
    measurements = serializers.DictField()
    measurement_taken_at = serializers.DateTimeField()
    order_status = serializers.CharField()
    rider_status = serializers.CharField()
    order_created_at = serializers.DateTimeField()


class FamilyMemberSummarySerializer(serializers.Serializer):
    """Serializer for family member summary in list view"""
    family_member_id = serializers.IntegerField()
    family_member_name = serializers.CharField()
    relationship = serializers.CharField(required=False, allow_null=True)
    total_measurements = serializers.IntegerField()
    latest_measurement_date = serializers.DateTimeField(required=False, allow_null=True)
    has_stored_measurements = serializers.BooleanField()


class StoredProfileMeasurementSerializer(serializers.Serializer):
    """Serializer for stored profile measurements"""
    recipient_type = serializers.CharField()
    recipient_id = serializers.IntegerField()
    recipient_name = serializers.CharField()
    recipient_relationship = serializers.CharField(required=False, allow_null=True)
    recipient_gender = serializers.CharField(required=False, allow_null=True)
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
    summary = serializers.DictField()