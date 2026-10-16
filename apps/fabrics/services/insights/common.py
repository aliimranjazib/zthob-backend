"""Shared presentation helpers for owner and shop fabric insights."""

from __future__ import annotations

from decimal import Decimal

from django.db.models import Count, Max, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.core.media_utils import build_public_media_url
from apps.orders.models import OrderItem

MONEY = Decimal('0.01')
ZERO = Decimal('0.00')

RANKING_FIELDS = (
    'product_id',
    'shop_fabric_id',
    'legacy_fabric_id',
    'source',
    'name',
    'sku',
    'image_url',
    'country',
    'fabric_type',
    'category',
    'season',
    'price',
    'effective_price',
    'stitching_price',
    'units_sold',
    'revenue',
    'share_pct',
    'order_count',
    'stock',
    'reserved_stock',
    'available_stock',
    'is_low_stock',
    'is_out_of_stock',
    'sale_active',
    'is_visible',
    'approval_status',
)


def money(value) -> str:
    if value is None:
        return '0.00'
    return format(Decimal(value).quantize(MONEY), 'f')


def share_pct(part, total) -> float:
    if not total:
        return 0.0
    return round(float(part) * 100.0 / float(total), 1)


def price_band(price) -> tuple[str, str]:
    amount = Decimal(price or 0)
    if amount < Decimal('80'):
        return 'economy', 'Economy'
    if amount < Decimal('150'):
        return 'mid', 'Mid'
    if amount < Decimal('250'):
        return 'premium', 'Premium'
    return 'luxury', 'Luxury'


def sale_is_active(product, now=None) -> bool:
    if not product.is_on_sale or product.discount_price is None:
        return False
    if not product.sale_start or not product.sale_end:
        return False
    now = now or timezone.now()
    return product.sale_start <= now <= product.sale_end


def sale_is_misconfigured(product) -> bool:
    if not product.is_on_sale:
        return False
    if product.discount_price is None or not product.sale_start or not product.sale_end:
        return True
    if product.sale_end <= product.sale_start:
        return True
    if product.price is not None and product.discount_price >= product.price:
        return True
    return False


def named(obj) -> dict | None:
    if obj is None:
        return None
    return {'id': obj.id, 'name': obj.name}


def country_payload(country) -> dict | None:
    if country is None:
        return None
    return {
        'id': country.id,
        'code': country.code,
        'name': country.name,
        'name_ar': country.name_ar or '',
    }


def tag_payloads(product) -> list[dict]:
    return [{'id': tag.id, 'name': tag.name} for tag in product.tags.all()]


def product_image_url(product, request) -> str | None:
    gallery = list(product.gallery.all())
    if not gallery:
        return None
    image = next((item for item in gallery if item.is_primary), gallery[0])
    if not image.image:
        return None
    return build_public_media_url(request, image.image.url)


def isoformat(value):
    if value is None:
        return None
    return value.isoformat()


def empty_sales() -> dict:
    return {
        'units_sold': 0,
        'revenue': ZERO,
        'order_count': 0,
        'last_sold_at': None,
    }


def sales_queryset(*, business_id: int | None = None, shop_id: int | None = None, owner_catalog_only: bool = False):
    queryset = OrderItem.objects.filter(fabric__v2_shop_fabric__isnull=False).exclude(
        order__status='cancelled',
    )
    if business_id is not None:
        queryset = queryset.filter(fabric__v2_shop_fabric__product__business_id=business_id)
    if owner_catalog_only:
        queryset = queryset.filter(fabric__v2_shop_fabric__product__show_in_owner_catalog=True)
    if shop_id is not None:
        queryset = queryset.filter(fabric__v2_shop_fabric__shop_id=shop_id)
    return queryset


def apply_window(queryset, window):
    return queryset.filter(
        order__created_at__date__gte=window.date_from,
        order__created_at__date__lte=window.date_to,
    )


def summarize_sales(queryset) -> dict:
    summary = queryset.aggregate(
        units_sold=Coalesce(Sum('quantity'), 0),
        revenue=Coalesce(Sum('total_price'), ZERO),
        order_count=Count('order_id', distinct=True),
    )
    units = int(summary['units_sold'] or 0)
    revenue = summary['revenue'] or ZERO
    return {
        'units_sold': units,
        'revenue': money(revenue),
        'order_count': int(summary['order_count'] or 0),
        'avg_selling_price': money((revenue / units) if units else ZERO),
    }


def sales_by_product(queryset) -> dict[int, dict]:
    rows = queryset.values('fabric__v2_shop_fabric__product_id').annotate(
        units_sold=Coalesce(Sum('quantity'), 0),
        revenue=Coalesce(Sum('total_price'), ZERO),
        order_count=Count('order_id', distinct=True),
        last_sold_at=Max('order__created_at'),
    )
    grouped = {}
    for row in rows:
        product_id = row['fabric__v2_shop_fabric__product_id']
        if product_id is None:
            continue
        grouped[product_id] = {
            'units_sold': int(row['units_sold'] or 0),
            'revenue': row['revenue'] or ZERO,
            'order_count': int(row['order_count'] or 0),
            'last_sold_at': row['last_sold_at'],
        }
    return grouped


def sales_by_product_shop(queryset) -> dict[tuple[int, int], dict]:
    rows = queryset.values(
        'fabric__v2_shop_fabric__product_id',
        'fabric__v2_shop_fabric__shop_id',
    ).annotate(
        units_sold=Coalesce(Sum('quantity'), 0),
        revenue=Coalesce(Sum('total_price'), ZERO),
        order_count=Count('order_id', distinct=True),
        last_sold_at=Max('order__created_at'),
    )
    grouped = {}
    for row in rows:
        product_id = row['fabric__v2_shop_fabric__product_id']
        shop_id = row['fabric__v2_shop_fabric__shop_id']
        if product_id is None or shop_id is None:
            continue
        grouped[(product_id, shop_id)] = {
            'units_sold': int(row['units_sold'] or 0),
            'revenue': row['revenue'] or ZERO,
            'order_count': int(row['order_count'] or 0),
            'last_sold_at': row['last_sold_at'],
        }
    return grouped


def sales_by_shop_fabric(queryset) -> dict[int, dict]:
    rows = queryset.values('fabric__v2_shop_fabric__id').annotate(
        units_sold=Coalesce(Sum('quantity'), 0),
        revenue=Coalesce(Sum('total_price'), ZERO),
        order_count=Count('order_id', distinct=True),
        last_sold_at=Max('order__created_at'),
    )
    grouped = {}
    for row in rows:
        shop_fabric_id = row['fabric__v2_shop_fabric__id']
        if shop_fabric_id is None:
            continue
        grouped[shop_fabric_id] = {
            'units_sold': int(row['units_sold'] or 0),
            'revenue': row['revenue'] or ZERO,
            'order_count': int(row['order_count'] or 0),
            'last_sold_at': row['last_sold_at'],
        }
    return grouped


def present_cards(cards: list[dict]) -> list[dict]:
    """Copy cards with period share and string money so nested scopes stay independent."""
    total_units = sum(card['units_sold'] for card in cards)
    presented = []
    for card in cards:
        row = dict(card)
        row['share_pct'] = share_pct(card['units_sold'], total_units)
        row['revenue'] = money(card['revenue'])
        presented.append(row)
    return presented


def ranking_row(card: dict, rank: int) -> dict:
    row = {field: card[field] for field in RANKING_FIELDS if field in card}
    row['rank'] = rank
    return row


def build_rankings(cards: list[dict], *, top_n: int) -> dict:
    def take(ordered):
        return [ranking_row(card, index) for index, card in enumerate(ordered[:top_n], start=1)]

    sellers = [card for card in cards if card['units_sold'] > 0]
    on_sale = [card for card in cards if card.get('sale_active')]
    return {
        'best_sellers': take(sorted(sellers, key=lambda card: (-card['units_sold'], card['name']))),
        'slow_movers': take(sorted(cards, key=lambda card: (card['units_sold'], -card['stock'], card['name']))),
        'never_sold': take(sorted(
            (card for card in cards if card['units_sold'] == 0),
            key=lambda card: (-card['stock'], card['name']),
        )),
        'highest_price': take(sorted(
            cards,
            key=lambda card: (-Decimal(card['effective_price']), card['name']),
        )),
        'lowest_price': take(sorted(
            cards,
            key=lambda card: (Decimal(card['effective_price']), card['name']),
        )),
        'highest_stock': take(sorted(cards, key=lambda card: (-card['stock'], card['name']))),
        'lowest_stock': take(sorted(cards, key=lambda card: (card['stock'], card['name']))),
        'on_sale': take(sorted(on_sale, key=lambda card: (-card['units_sold'], card['name']))),
    }


def build_breakdown(cards: list[dict], key_fn) -> list[dict]:
    buckets: dict = {}
    for card in cards:
        result = key_fn(card)
        entries = result if isinstance(result, list) else [result]
        for key, payload in entries:
            bucket = buckets.get(key)
            if bucket is None:
                bucket = {
                    **payload,
                    'units_sold': 0,
                    'revenue': ZERO,
                    'sku_count': 0,
                    'stock_on_hand': 0,
                    'top_product': None,
                }
                buckets[key] = bucket
            bucket['units_sold'] += card['units_sold']
            bucket['revenue'] += Decimal(card['revenue'])
            bucket['sku_count'] += 1
            bucket['stock_on_hand'] += int(card.get('stock') or 0)
            top = bucket['top_product']
            if top is None or card['units_sold'] > top['units_sold']:
                bucket['top_product'] = {
                    'product_id': card['product_id'],
                    'name': card['name'],
                    'units_sold': card['units_sold'],
                }
    total_units = sum(bucket['units_sold'] for bucket in buckets.values())
    rows = []
    for bucket in buckets.values():
        revenue = bucket.pop('revenue')
        rows.append({
            **bucket,
            'revenue': money(revenue),
            'share_pct': share_pct(bucket['units_sold'], total_units),
        })
    rows.sort(key=lambda row: (-row['units_sold'], row.get('name') or row.get('key') or ''))
    return rows


def unspecified(kind: str) -> tuple[str, dict]:
    return f'unspecified:{kind}', {
        'key': 'unspecified',
        'name': 'Unspecified',
    }


def country_key(card):
    country = card.get('country')
    if not country:
        return unspecified('country')
    return f"country:{country['id']}", {
        'key': country['code'],
        'country_id': country['id'],
        'code': country['code'],
        'name': country['name'],
        'name_ar': country.get('name_ar') or '',
    }


def named_key(card, field: str):
    value = card.get(field)
    if not value:
        return unspecified(field)
    return f"{field}:{value['id']}", {
        'key': str(value['id']),
        'id': value['id'],
        'name': value['name'],
    }


def tag_keys(card):
    tags = card.get('tags') or []
    if not tags:
        return [unspecified('tag')]
    return [
        (f"tag:{tag['id']}", {'key': str(tag['id']), 'id': tag['id'], 'name': tag['name']})
        for tag in tags
    ]


def season_key(card):
    season = card.get('season') or 'unspecified'
    labels = {
        'summer': 'Summer',
        'winter': 'Winter',
        'all_season': 'All season',
    }
    return f'season:{season}', {
        'key': season,
        'name': labels.get(season, season.replace('_', ' ').title()),
    }


def price_band_key(card):
    key, label = price_band(card.get('effective_price'))
    return f'band:{key}', {'key': key, 'name': label}


def sale_key(card):
    active = bool(card.get('sale_active'))
    key = 'on_sale' if active else 'full_price'
    label = 'On sale' if active else 'Full price'
    return f'sale:{key}', {'key': key, 'name': label}


def featured_key(card):
    featured = bool(card.get('is_featured'))
    key = 'featured' if featured else 'standard'
    label = 'Featured' if featured else 'Standard'
    return f'featured:{key}', {'key': key, 'name': label}


def standard_breakdowns(cards: list[dict]) -> dict:
    return {
        'by_country': build_breakdown(cards, country_key),
        'by_type': build_breakdown(cards, lambda card: named_key(card, 'fabric_type')),
        'by_category': build_breakdown(cards, lambda card: named_key(card, 'category')),
        'by_season': build_breakdown(cards, season_key),
        'by_tag': build_breakdown(cards, tag_keys),
        'by_price_band': build_breakdown(cards, price_band_key),
        'by_sale': build_breakdown(cards, sale_key),
        'by_featured': build_breakdown(cards, featured_key),
    }


def make_alert(key: str, severity: str, title: str, product_ids) -> dict | None:
    ids = [product_id for product_id in product_ids if product_id is not None]
    if not ids:
        return None
    return {
        'key': key,
        'severity': severity,
        'title': title,
        'count': len(ids),
        'product_ids': ids[:20],
    }


def compact_alerts(alerts) -> list[dict]:
    return [alert for alert in alerts if alert]
