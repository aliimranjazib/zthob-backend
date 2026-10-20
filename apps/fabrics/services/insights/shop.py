"""Shop-shelf fabric insights, split into owner-assigned and shop-created fabrics."""

from __future__ import annotations

from django.db.models import OuterRef, Subquery
from django.utils import timezone

from apps.fabrics.models import FabricStockMovement, ShopFabric
from apps.fabrics.services.insights.common import (
    build_breakdown,
    build_rankings,
    compact_alerts,
    country_payload,
    empty_sales,
    isoformat,
    make_alert,
    money,
    named,
    product_image_url,
    sale_is_active,
    sale_is_misconfigured,
    sales_by_shop_fabric,
    sales_queryset,
    apply_window,
    standard_breakdowns,
    summarize_sales,
    tag_payloads,
    present_cards,
)
from apps.tailors.services.shop_plus import (
    count_owner_catalog_fabrics_on_shop,
    count_shop_created_fabrics_on_shop,
    serialize_shop_tailor_plus,
)

SOURCE_FROM_OWNER = 'from_owner'
SOURCE_SHOP_OWN = 'shop_own'


def get_shop_fabric_insights(
    *,
    shop,
    window,
    low_stock_threshold: int = 5,
    top_n: int = 10,
    request=None,
) -> dict:
    listings = list(_shop_listings(shop.id))
    sales_qs = apply_window(sales_queryset(shop_id=shop.id), window)
    by_listing = sales_by_shop_fabric(sales_qs)
    now = timezone.now()
    cards = [
        _shop_card(listing, by_listing, low_stock_threshold, now, request)
        for listing in listings
    ]
    from_owner = present_cards([card for card in cards if card['source'] == SOURCE_FROM_OWNER])
    shop_own = present_cards([card for card in cards if card['source'] == SOURCE_SHOP_OWN])
    all_cards = present_cards(cards)

    return {
        'scope': {
            'mode': 'shop',
            'shop_id': shop.id,
            'shop_name': shop.shop_name,
            'business_id': shop.business_id,
        },
        'period': window.as_dict(),
        'limits': _limits(shop),
        'shelf': {
            'all': _shelf_block(all_cards, sales_qs),
            'from_owner': _shelf_block(
                from_owner,
                sales_qs.filter(fabric__v2_shop_fabric__product__show_in_owner_catalog=True),
            ),
            'shop_own': _shelf_block(
                shop_own,
                sales_qs.filter(fabric__v2_shop_fabric__product__show_in_owner_catalog=False),
            ),
        },
        'rankings': {
            'all': build_rankings(all_cards, top_n=top_n),
            'from_owner': build_rankings(from_owner, top_n=top_n),
            'shop_own': build_rankings(shop_own, top_n=top_n),
        },
        'breakdowns': {
            'all': {
                **standard_breakdowns(all_cards),
                'by_source': _source_breakdown(all_cards),
            },
            'from_owner': standard_breakdowns(from_owner),
            'shop_own': standard_breakdowns(shop_own),
        },
        'alerts': _alerts(all_cards, listings, low_stock_threshold),
        'fabrics': all_cards,
    }


def _shop_listings(shop_id: int):
    latest = FabricStockMovement.objects.filter(shop_fabric_id=OuterRef('pk')).order_by('-created_at')
    return (
        ShopFabric.objects.filter(shop_id=shop_id, is_active=True)
        .select_related(
            'shop',
            'product',
            'product__fabric_type',
            'product__category',
            'product__country',
            'legacy_fabric',
        )
        .prefetch_related('product__tags', 'product__gallery')
        .annotate(
            last_movement_at=Subquery(latest.values('created_at')[:1]),
            last_movement_type=Subquery(latest.values('movement_type')[:1]),
        )
        .order_by('-created_at')
    )


def _limits(shop) -> dict:
    serialized = serialize_shop_tailor_plus(shop)
    limit = None
    from_owner_count = count_owner_catalog_fabrics_on_shop(shop.id)
    shop_own_count = count_shop_created_fabrics_on_shop(shop.id)
    return {
        'tier': serialized['tier'],
        'plus_active': serialized['is_active'],
        'plus_source': serialized.get('plus_source'),
        'from_owner_count': from_owner_count,
        'from_owner_limit': limit,
        'shop_own_count': shop_own_count,
        'shop_own_limit': limit,
        'near_from_owner_limit': limit is not None and from_owner_count >= max(limit - 5, 0),
        'near_shop_own_limit': limit is not None and shop_own_count >= max(limit - 5, 0),
        'analytics_days': serialized['limits']['analytics_days'],
    }


def _shop_card(listing, by_listing, low_stock_threshold: int, now, request) -> dict:
    product = listing.product
    sales = by_listing.get(listing.id, empty_sales())
    available = listing.available_stock
    source = SOURCE_FROM_OWNER if product.show_in_owner_catalog else SOURCE_SHOP_OWN
    return {
        'shop_fabric_id': listing.id,
        'product_id': product.id,
        'legacy_fabric_id': listing.legacy_fabric_id,
        'source': source,
        'name': product.name,
        'sku': product.sku,
        'description': product.description or '',
        'image_url': product_image_url(product, request),
        'gallery_count': len(list(product.gallery.all())),
        'country': country_payload(product.country),
        'fabric_type': named(product.fabric_type),
        'category': named(product.category),
        'tags': tag_payloads(product),
        'season': product.seasons,
        'price': money(product.price),
        'price_override': money(listing.price_override) if listing.price_override is not None else None,
        'effective_price': money(listing.effective_price),
        'stitching_price': money(product.stitching_price) if product.stitching_price is not None else None,
        'discount_price': money(product.discount_price) if product.discount_price is not None else None,
        'is_on_sale': product.is_on_sale,
        'sale_active': sale_is_active(product, now),
        'sale_start': isoformat(product.sale_start),
        'sale_end': isoformat(product.sale_end),
        'stock': listing.stock,
        'reserved_stock': listing.reserved_stock,
        'available_stock': available,
        'is_low_stock': 0 < available <= low_stock_threshold,
        'is_out_of_stock': available == 0,
        'is_visible': listing.is_visible,
        'is_active': listing.is_active,
        'approval_status': product.approval_status,
        'is_featured': product.is_featured,
        'customer_can_buy': bool(
            listing.is_visible
            and listing.is_active
            and product.is_active
            and product.approval_status == 'approved'
            and available > 0
        ),
        'units_sold': sales['units_sold'],
        'revenue': sales['revenue'],
        'order_count': sales['order_count'],
        'share_pct': 0.0,
        'last_sold_at': isoformat(sales['last_sold_at']),
        'last_movement_at': isoformat(getattr(listing, 'last_movement_at', None)),
        'last_movement_type': getattr(listing, 'last_movement_type', None),
        'created_at': isoformat(listing.created_at),
        'updated_at': isoformat(listing.updated_at),
    }


def _shelf_block(cards, sales_qs) -> dict:
    summary = summarize_sales(sales_qs)
    best = max(cards, key=lambda card: (card['units_sold'], card['name']), default=None)
    summary.update({
        'sku_count': len(cards),
        'stock': sum(card['stock'] for card in cards),
        'reserved_stock': sum(card['reserved_stock'] for card in cards),
        'available_stock': sum(card['available_stock'] for card in cards),
        'skus_sold': sum(1 for card in cards if card['units_sold'] > 0),
        'skus_never_sold': sum(1 for card in cards if card['units_sold'] == 0),
        'skus_out_of_stock': sum(1 for card in cards if card['is_out_of_stock']),
        'skus_low_stock': sum(1 for card in cards if card['is_low_stock']),
        'skus_on_sale': sum(1 for card in cards if card['sale_active']),
        'skus_hidden': sum(1 for card in cards if not card['is_visible']),
        'best_seller': None,
    })
    if best and best['units_sold'] > 0:
        summary['best_seller'] = {
            'product_id': best['product_id'],
            'shop_fabric_id': best['shop_fabric_id'],
            'name': best['name'],
            'source': best['source'],
            'units_sold': best['units_sold'],
            'revenue': best['revenue'] if isinstance(best['revenue'], str) else money(best['revenue']),
        }
    return summary


def _source_breakdown(cards) -> list[dict]:
    def key_fn(card):
        source = card['source']
        label = 'From owner' if source == SOURCE_FROM_OWNER else 'My fabrics'
        return source, {'key': source, 'name': label}

    return build_breakdown(cards, key_fn)


def _alerts(cards, listings, low_stock_threshold: int) -> list[dict]:
    listing_by_id = {listing.id: listing for listing in listings}
    return compact_alerts([
        make_alert(
            'from_owner_out_of_stock',
            'critical',
            'Owner-assigned fabrics are out of stock in this shop.',
            [
                card['product_id']
                for card in cards
                if card['source'] == SOURCE_FROM_OWNER and card['is_out_of_stock']
            ],
        ),
        make_alert(
            'shop_own_out_of_stock',
            'critical',
            'Shop fabrics are out of stock.',
            [
                card['product_id']
                for card in cards
                if card['source'] == SOURCE_SHOP_OWN and card['is_out_of_stock']
            ],
        ),
        make_alert(
            'best_seller_out',
            'critical',
            'Fabrics that sold in this period are now out of stock.',
            [
                card['product_id']
                for card in cards
                if card['units_sold'] > 0 and card['is_out_of_stock']
            ],
        ),
        make_alert(
            'low_stock',
            'warning',
            f'Available stock is at or below {low_stock_threshold}.',
            [card['product_id'] for card in cards if card['is_low_stock']],
        ),
        make_alert(
            'hidden_with_stock',
            'info',
            'Hidden fabrics still have stock.',
            [
                card['product_id']
                for card in cards
                if not card['is_visible'] and card['available_stock'] > 0
            ],
        ),
        make_alert(
            'not_approved',
            'warning',
            'Customers cannot buy these fabrics until they are approved.',
            [
                card['product_id']
                for card in cards
                if card['approval_status'] != 'approved'
            ],
        ),
        make_alert(
            'missing_photo',
            'info',
            'Fabrics are missing a photo.',
            [card['product_id'] for card in cards if not card['image_url']],
        ),
        make_alert(
            'missing_country',
            'info',
            'Fabrics have no country.',
            [card['product_id'] for card in cards if card['country'] is None],
        ),
        make_alert(
            'sale_misconfigured',
            'warning',
            'Sale is on but the discount or dates are incomplete.',
            [
                card['product_id']
                for card in cards
                if sale_is_misconfigured(listing_by_id[card['shop_fabric_id']].product)
            ],
        ),
    ])
