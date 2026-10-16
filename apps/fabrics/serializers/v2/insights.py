from rest_framework import serializers

from apps.tailors.models.base import SEASON_CHOICES


SEASON_VALUES = [choice[0] for choice in SEASON_CHOICES]


class FabricInsightWindowSerializer(serializers.Serializer):
    days = serializers.IntegerField(required=False, min_value=1, max_value=30)
    period = serializers.ChoiceField(choices=['1d', '7d', '15d', '30d'], required=False)
    date_from = serializers.DateField(required=False, allow_null=True)
    date_to = serializers.DateField(required=False, allow_null=True)
    low_stock_threshold = serializers.IntegerField(required=False, min_value=0, default=5)
    top_n = serializers.IntegerField(required=False, min_value=1, max_value=50, default=10)

    def validate(self, data):
        has_from = data.get('date_from') is not None
        has_to = data.get('date_to') is not None
        if has_from != has_to:
            raise serializers.ValidationError('date_from and date_to must be provided together.')
        if data.get('days') and data.get('period'):
            raise serializers.ValidationError('Pass either days or period.')
        return data


class OwnerFabricInsightQuerySerializer(FabricInsightWindowSerializer):
    shop_id = serializers.IntegerField(required=False, allow_null=True)


class OwnerFabricListQuerySerializer(serializers.Serializer):
    q = serializers.CharField(required=False, allow_blank=True)
    country_id = serializers.IntegerField(required=False)
    category_id = serializers.IntegerField(required=False)
    fabric_type_id = serializers.IntegerField(required=False)
    season = serializers.ChoiceField(choices=SEASON_VALUES, required=False)
    on_sale = serializers.BooleanField(required=False)
    sort = serializers.ChoiceField(
        choices=['newest', 'name', 'price_asc', 'price_desc', 'best_selling'],
        required=False,
        default='newest',
    )


class ShopFabricListQuerySerializer(OwnerFabricListQuerySerializer):
    source = serializers.ChoiceField(
        choices=['all', 'from_owner', 'shop_own'],
        required=False,
        default='all',
    )
    stock = serializers.ChoiceField(choices=['in', 'low', 'out'], required=False)
    low_stock_threshold = serializers.IntegerField(required=False, min_value=0, default=5)
    sort = serializers.ChoiceField(
        choices=[
            'newest',
            'name',
            'price_asc',
            'price_desc',
            'stock_asc',
            'stock_desc',
            'best_selling',
        ],
        required=False,
        default='newest',
    )
