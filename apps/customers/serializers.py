from rest_framework.serializers import ModelSerializer
from rest_framework import serializers

from apps.accounts.serializers import UserProfileSerializer
from apps.tailors.models import Fabric
from apps.tailors.serializers import FabricCategorySerializer, FabricImageSerializer, TailorProfileSerializer
from apps.tailors.serializers.catalog import FabricTypeBasicSerializer,FabricTagBasicSerializer
from apps.customers.models import Address, CustomerProfile, FamilyMember


class FabricCatalogSerializer(serializers.ModelSerializer):
    fabric_image = serializers.SerializerMethodField()
    gallery = FabricImageSerializer(many=True, read_only=True)
    category = FabricCategorySerializer(read_only=True)
    fabric_type=FabricTypeBasicSerializer(read_only=True)
    tags=FabricTagBasicSerializer(many=True, read_only=True)
    tailor = TailorProfileSerializer(read_only=True)
    class Meta:
        model=Fabric
        fields = [
            "id",
            "name",
            "description",
            "sku",
            "price",
            "stock",
            "is_active",
            "seasons",
            "fabric_type",  
            "tags", 
            "fabric_image",
            "gallery",
            "category",
            "tailor",
        ]
    

    def get_fabric_image(self, obj) -> str | None:
        request = self.context.get("request", None)
        if request:
            return request.build_absolute_uri(obj.fabric_image.url) if obj.fabric_image else None
        return obj.fabric_image.url if obj.fabric_image else None
    

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
    
    
class FamilyMemberSerializer(serializers.ModelSerializer):
    address=AddressSerializer(required=False)
    class Meta:
        model=FamilyMember
        fields = ['id', 'name', 'gender', 'relationship', 'measurements', 'address']
        read_only_fields = ['user']
        
    def create(self, validated_data):
        user = self.context.get("user")

        address_data = validated_data.pop("address", None)

        family_member = FamilyMember.objects.create(
            user=user,
            **validated_data
        )

        if address_data:
            address = Address.objects.create(user=user, **address_data)
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
            if instance.address:
                for attr, value in validated_data.items():
                    setattr(instance.address, attr, value)
                    instance.address.save()
            else:
                user = self.context.get('user')
                address = Address.objects.create(user=user, **address_data)
                instance.address = address
                instance.save()
        return instance


class CustomerProfileSerializer(serializers.ModelSerializer):
    user=UserProfileSerializer(read_only=True)
    default_address = AddressSerializer(read_only=True)
    addresses = AddressSerializer(source='user.addresses', many=True, read_only=True)
    phone_verified = serializers.SerializerMethodField()
    class Meta:
        model=CustomerProfile
        fields = ['user', 'default_address','addresses','phone_verified',]

    def get_phone_verified(self, obj):
        """Get phone verification status from user"""
        return obj.user.phone_verified