from rest_framework import serializers

from apps.tailors.models import FabricCategory, FabricCountry, FabricTag, FabricType
from apps.tailors.models.v2_fabrics import FabricProduct, FabricStockMovement, ShopFabric


class V2FabricProductImageSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    image_url = serializers.SerializerMethodField()
    is_primary = serializers.BooleanField()
    order = serializers.IntegerField()

    def get_image_url(self, obj):
        if not obj.image:
            return None
        request = self.context.get('request')
        from apps.core.media_utils import build_public_media_url
        return build_public_media_url(request, obj.image.url)


class V2FabricProductSerializer(serializers.ModelSerializer):
    fabric_type_id = serializers.PrimaryKeyRelatedField(
        source='fabric_type',
        queryset=FabricType.objects.all(),
        allow_null=True,
        required=False,
    )
    category_id = serializers.PrimaryKeyRelatedField(
        source='category',
        queryset=FabricCategory.objects.all(),
        allow_null=True,
        required=False,
    )
    country_id = serializers.PrimaryKeyRelatedField(
        source='country',
        queryset=FabricCountry.objects.all(),
        allow_null=True,
        required=False,
    )
    tag_ids = serializers.PrimaryKeyRelatedField(
        source='tags',
        many=True,
        queryset=FabricTag.objects.filter(is_active=True),
        required=False,
    )
    fabric_type_name = serializers.CharField(source='fabric_type.name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    country_name = serializers.CharField(source='country.name', read_only=True)
    gallery = V2FabricProductImageSerializer(many=True, read_only=True)
    assigned_shop_count = serializers.SerializerMethodField()

    class Meta:
        model = FabricProduct
        fields = [
            'id',
            'business_id',
            'name',
            'description',
            'sku',
            'fabric_type_id',
            'fabric_type_name',
            'category_id',
            'category_name',
            'country_id',
            'country_name',
            'tag_ids',
            'price',
            'stitching_price',
            'seasons',
            'approval_status',
            'is_active',
            'assigned_shop_count',
            'gallery',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'business_id', 'sku', 'approval_status', 'created_at', 'updated_at']

    def get_assigned_shop_count(self, obj):
        assignments = getattr(obj, '_prefetched_objects_cache', {}).get('shop_assignments')
        if assignments is not None:
            return len([a for a in assignments if a.is_active])
        return obj.shop_assignments.filter(is_active=True).count()


class V2FabricProductWriteSerializer(serializers.ModelSerializer):
    fabric_type_id = serializers.PrimaryKeyRelatedField(
        source='fabric_type',
        queryset=FabricType.objects.all(),
        allow_null=True,
        required=False,
    )
    category_id = serializers.PrimaryKeyRelatedField(
        source='category',
        queryset=FabricCategory.objects.all(),
        allow_null=True,
        required=False,
    )
    country_id = serializers.PrimaryKeyRelatedField(
        source='country',
        queryset=FabricCountry.objects.all(),
        allow_null=True,
        required=False,
    )
    tag_ids = serializers.PrimaryKeyRelatedField(
        source='tags',
        many=True,
        queryset=FabricTag.objects.filter(is_active=True),
        required=False,
    )

    class Meta:
        model = FabricProduct
        fields = [
            'name',
            'description',
            'fabric_type_id',
            'category_id',
            'country_id',
            'tag_ids',
            'price',
            'stitching_price',
            'seasons',
            'is_active',
        ]


class V2FabricAssignSerializer(serializers.Serializer):
    shop_id = serializers.IntegerField()
    stock = serializers.IntegerField(min_value=0, default=0)
    price_override = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        allow_null=True,
    )
    is_visible = serializers.BooleanField(default=True)


class V2ShopFabricSerializer(serializers.ModelSerializer):
    product = V2FabricProductSerializer(read_only=True)
    legacy_fabric_id = serializers.IntegerField(read_only=True)
    effective_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    available_stock = serializers.IntegerField(read_only=True)

    class Meta:
        model = ShopFabric
        fields = [
            'id',
            'shop_id',
            'product',
            'legacy_fabric_id',
            'stock',
            'reserved_stock',
            'available_stock',
            'price_override',
            'effective_price',
            'is_visible',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'shop_id', 'legacy_fabric_id', 'created_at', 'updated_at']


class V2ShopFabricUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShopFabric
        fields = ['stock', 'price_override', 'is_visible', 'is_active']


class V2FabricStockMovementSerializer(serializers.Serializer):
    movement_type = serializers.ChoiceField(
        choices=[
            FabricStockMovement.TYPE_ADJUSTMENT_ADD,
            FabricStockMovement.TYPE_ADJUSTMENT_REMOVE,
            FabricStockMovement.TYPE_ADJUSTMENT_SET,
        ]
    )
    quantity = serializers.IntegerField(min_value=0)
    reason = serializers.CharField(required=False, allow_blank=True, max_length=64)
    note = serializers.CharField(required=False, allow_blank=True)


class V2FabricAnalyticsQuerySerializer(serializers.Serializer):
    shop_id = serializers.IntegerField(required=False, allow_null=True)
    date_from = serializers.DateField(required=False, allow_null=True)
    date_to = serializers.DateField(required=False, allow_null=True)
    low_stock_threshold = serializers.IntegerField(required=False, min_value=0, default=5)
