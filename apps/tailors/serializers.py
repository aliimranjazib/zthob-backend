from rest_framework import serializers
from apps.accounts.serializers import UserProfileSerializer
from apps.tailors.models import Fabric, FabricCategory, FabricImage, TailorProfile

class TailorProfileSerializer(serializers.ModelSerializer):
    user=UserProfileSerializer(read_only=True)
    class Meta:
        model=TailorProfile
        fields = ['user','shop_name','establishment_year','tailor_experience','working_hours','contact_number','address']

class FabricImageSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = FabricImage
        fields = ["id", "image", "order"]

    def get_image(self, obj) -> str | None:
        request = self.context.get("request", None)
        if request:
            return request.build_absolute_uri(obj.image.url) if obj.image else None
        return obj.image.url if obj.image else None

class FabricCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = FabricCategory
        fields = ["id", "name", "slug", "is_active", "created_at", "updated_at"]

class FabricSerializer(serializers.ModelSerializer):
    gallery = FabricImageSerializer(many=True, read_only=True)
    category=FabricCategorySerializer(read_only=True)
    tailor=TailorProfileSerializer(read_only=True)
    class Meta:
        model = Fabric
        fields = [
            "id", "tailor", "category",
            "name", "description",
            "sku", "price", "stock",
            "is_active", "created_at", "updated_at",
            "fabric_image", "gallery",
        ]
        read_only_fields = ["id", "sku", "created_at", "updated_at"]
    
    def validate_gallery(self, value):
        if not (1 <= len(value) <= 4):
            raise serializers.ValidationError("You must upload between 1 and 4 images.")
        return value


class FabricCreateSerializer(serializers.ModelSerializer):
    images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True
    )

    class Meta:
        model = Fabric
        fields = [
            "category",
            "name",
            "description",
            "price",
            "stock",
            "is_active",
            "images",
        ]

    def validate_images(self, value):
        if not (1 <= len(value) <= 4):
            raise serializers.ValidationError("You must upload between 1 and 4 images.")
        return value

    def create(self, validated_data):
        images = validated_data.pop("images", [])
        request = self.context.get("request")
        tailor_profile = getattr(request.user, "tailor_profile", None)
        

        fabric = Fabric.objects.create(
            tailor=tailor_profile,
            created_by=request.user,
            fabric_image=images[0] if images else None,
            **validated_data,
        )

        for index, image in enumerate(images):
            FabricImage.objects.create(
                fabric=fabric,
                image=image,
                order=index,
            )

        return fabric
        
        
class TailorProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model=TailorProfile
        fields = ['shop_name','establishment_year','tailor_experience','working_hours','contact_number','address']

    