from rest_framework.serializers import ModelSerializer
from rest_framework import serializers

from apps.tailors.models import Fabric
from apps.tailors.serializers import FabricCategorySerializer, FabricImageSerializer, TailorProfileSerializer


class FabricCatalogSerializer(serializers.ModelSerializer):
    fabric_image = serializers.SerializerMethodField()
    gallery = FabricImageSerializer(many=True, read_only=True)
    category = FabricCategorySerializer(read_only=True)
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
            "fabric_image",
            "gallery",
            "category",
            "tailor",
        ]
    

    def get_fabric_image(self, obj):
        request = self.context.get("request", None)
        if request:
            return request.build_absolute_uri(obj.fabric_image.url) if obj.fabric_image else None
        return obj.fabric_image.url if obj.fabric_image else None
