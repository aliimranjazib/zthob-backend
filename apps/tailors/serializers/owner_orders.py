"""Owner dashboard order serializers with shop branch metadata."""

from rest_framework import serializers

from apps.core.phone_utils import format_phone_for_display
from apps.orders.serializers import OrderListSerializer, OrderSerializer


def build_shop_info(order):
    shop = getattr(order, 'shop', None)
    if shop is None:
        return None
    return {
        'id': shop.id,
        'shop_name': shop.shop_name or '',
        'contact_number': format_phone_for_display(shop.contact_number) if shop.contact_number else None,
        'address': shop.address or '',
        'shop_status': bool(shop.shop_status),
    }


class OwnerOrderListSerializer(OrderListSerializer):
    shop_id = serializers.IntegerField(read_only=True, allow_null=True)
    shop_info = serializers.SerializerMethodField()

    class Meta(OrderListSerializer.Meta):
        fields = OrderListSerializer.Meta.fields + ['shop_id', 'shop_info']

    def get_shop_info(self, obj):
        return build_shop_info(obj)

    def get_tailor_name(self, obj):
        shop = getattr(obj, 'shop', None)
        if shop and shop.shop_name:
            return shop.shop_name
        return super().get_tailor_name(obj)


class OwnerOrderDetailSerializer(OrderSerializer):
    shop_id = serializers.IntegerField(read_only=True, allow_null=True)
    shop_info = serializers.SerializerMethodField()

    class Meta(OrderSerializer.Meta):
        fields = OrderSerializer.Meta.fields + ['shop_id', 'shop_info']

    def get_shop_info(self, obj):
        return build_shop_info(obj)

    def get_tailor_name(self, obj):
        shop = getattr(obj, 'shop', None)
        if shop and shop.shop_name:
            return shop.shop_name
        return super().get_tailor_name(obj)

    def get_tailor_contact(self, obj):
        shop = getattr(obj, 'shop', None)
        if shop and shop.contact_number:
            return format_phone_for_display(shop.contact_number)
        return super().get_tailor_contact(obj)
