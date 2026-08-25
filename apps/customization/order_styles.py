"""Build read-only order style entries for customer preset list v2."""

from django.db.models import Q

from apps.core.media_utils import build_public_media_url
from apps.core.phone_utils import display_user_label
from apps.customization.models import CustomStyle
from apps.orders.models import OrderItem
from apps.orders.serializers import format_custom_styles_for_response


def _recipient_name(item):
    if item.recipient_display_name:
        return item.recipient_display_name
    if item.family_member:
        return item.family_member.name
    try:
        return display_user_label(item.order.customer)
    except AttributeError:
        return 'Customer'


def _shop_name(order):
    tailor = order.tailor
    if not tailor:
        return 'Tailor shop'
    try:
        profile = tailor.tailor_profile
        return profile.shop_name or tailor.get_full_name() or tailor.username
    except Exception:
        return tailor.get_full_name() or tailor.username


def _custom_styles_to_preset_styles(formatted_styles):
    preset_styles = []
    for style in formatted_styles:
        preset_styles.append({
            'category': style.get('style_type'),
            'style_id': style.get('style_id'),
            'text': style.get('text'),
            'reference_images': style.get('reference_images', []),
            'reference_image_ids': style.get('reference_image_ids', []),
        })
    return preset_styles


def _build_styles_details(formatted_styles, request):
    details = []
    for style in formatted_styles:
        style_id = style.get('style_id')
        style_type = style.get('style_type')
        label = style.get('label')
        entry = {
            'category': style_type,
            'style_id': style_id,
            'text': style.get('text'),
            'reference_images': style.get('reference_images', []),
            'reference_image_ids': style.get('reference_image_ids', []),
        }

        style_obj = None
        if style_id:
            style_obj = CustomStyle.objects.select_related('category').filter(
                id=style_id,
                is_active=True,
            ).first()

        if style_obj:
            entry.update({
                'category_display': style_obj.category.display_name,
                'style_name': style_obj.name,
                'style_code': style_obj.code,
                'image_url': (
                    build_public_media_url(request, style_obj.image.url)
                    if style_obj.image else style.get('asset_path')
                ),
            })
        else:
            entry.update({
                'category_display': style_type,
                'style_name': label,
                'style_code': None,
                'image_url': style.get('asset_path'),
            })
        details.append(entry)
    return details


def build_order_style_entry(item, request):
    order = item.order
    formatted_styles = format_custom_styles_for_response(item.custom_styles, request)
    order_number = order.order_number or str(order.id).zfill(5)

    return {
        'id': None,
        'name': f'Walk-in order #{order_number}',
        'description': f'From {_shop_name(order)} · {_recipient_name(item)}',
        'styles': _custom_styles_to_preset_styles(formatted_styles),
        'styles_details': _build_styles_details(formatted_styles, request),
        'is_default': False,
        'usage_count': 0,
        'source': 'order',
        'read_only': True,
        'order_id': order.id,
        'order_number': order_number,
        'created_at': order.created_at,
    }


def get_customer_order_style_presets(customer_user, request=None):
    """
    Return walk-in order item styles for the logged-in customer, shaped like presets.
    One entry per order item that has custom_styles.
    """
    items = (
        OrderItem.objects.filter(
            order__customer=customer_user,
            order__service_mode='walk_in',
        )
        .exclude(Q(custom_styles__isnull=True) | Q(custom_styles=[]))
        .select_related(
            'order',
            'family_member',
            'order__customer',
            'order__tailor',
            'order__tailor__tailor_profile',
        )
        .order_by('-order__created_at', '-id')
    )

    return [build_order_style_entry(item, request) for item in items]
