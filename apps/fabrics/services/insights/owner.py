"""Owner-catalog fabric insights. Shop-created fabrics are excluded."""

from __future__ import annotations

from decimal import Decimal

from django.db.models import OuterRef, Subquery
from django.utils import timezone

from apps.fabrics.models import FabricStockMovement, ShopFabric
from apps.fabrics.services.catalog import owner_catalog_products_queryset
from apps.fabrics.services.insights.common import (
    build_rankings,
    country_payload,
    empty_sales,
    isoformat,
    make_alert,
    compact_alerts,
    money,
    named,
    product_image_url,
    sale_is_active,
    sale_is_misconfigured,
    sales_by_product,
    sales_by_product_shop,
    sales_queryset,
    apply_window,
    share_pct,
    standard_breakdowns,
    summarize_sales,
    tag_payloads,
    present_cards,
)
from apps.tailors.models import TailorProfile
from apps.tailors.services.plans.constants import FREE_OWNER_CATALOG_PRODUCTS
from apps.tailors.services.plans.owner_plus import (
    count_owner_catalog_products,
    is_owner_plus_active,
    serialize_owner_plus,
)


def get_owner_fabric_insights(
    *,
    business,
    owner,
    window,
    shop_id: int | None = None,
    low_stock_threshold: int = 5,
    top_n: int = 10,
    request=None,
) -> dict:
    products = list(owner_catalog_products_queryset(business_id=business.id))
    sales_qs = apply_window(
        sales_queryset(business_id=business.id, shop_id=shop_id, owner_catalog_only=True),
        window,
    )
    by_product = sales_by_product(sales_qs)
    by_shop = sales_by_product_shop(sales_qs)
    movement_map = _latest_movements(business_id=business.id)
    now = timezone.now()

    cards = [
        _owner_card(
            product,
            by_product=by_product,
            by_shop=by_shop,
            movement_map=movement_map,
            low_stock_threshold=low_stock_threshold,
            shop_id=shop_id,
            now=now,
            request=request,
        )
        for product in products
    ]
    scoped_cards = cards
    if shop_id is not None:
        scoped_cards = [card for card in cards if card['assigned_to_scope']]

    shops = _business_shops(business)
    presented_scope = present_cards(scoped_cards)
    presented_all = present_cards(cards)
    return {
        'scope': _scope(business, shop_id, shops),
        'period': window.as_dict(),
        'limits': _limits(business, owner, len(products)),
        'catalog_health': _catalog_health(products, now),
        'network_stock': _network_stock(scoped_cards, cards, low_stock_threshold),
        'sales_summary': _sales_summary(sales_qs, presented_scope),
        'assignments': _assignments(presented_all, shops, shop_id, low_stock_threshold),
        'rankings': build_rankings(presented_scope, top_n=top_n),
        'breakdowns': {
            **standard_breakdowns(presented_scope),
            'by_shop': _shop_breakdown(presented_all, shops, shop_id),
        },
        'alerts': _alerts(presented_all, products, low_stock_threshold, shop_id),
        'fabrics': presented_all,
    }


def _latest_movements(*, business_id: int) -> dict[int, dict]:
    latest = FabricStockMovement.objects.filter(shop_fabric_id=OuterRef('pk')).order_by('-created_at')
    rows = ShopFabric.objects.filter(
        product__business_id=business_id,
        product__show_in_owner_catalog=True,
    ).annotate(
        last_movement_at=Subquery(latest.values('created_at')[:1]),
        last_movement_type=Subquery(latest.values('movement_type')[:1]),
    ).values('id', 'last_movement_at', 'last_movement_type')
    return {
        row['id']: {
            'last_movement_at': row['last_movement_at'],
            'last_movement_type': row['last_movement_type'],
        }
        for row in rows
    }


def _business_shops(business):
    return list(
        TailorProfile.objects.filter(business_id=business.id)
        .exclude(shop_name__isnull=True)
        .exclude(shop_name='')
        .order_by('shop_name', 'id')
    )


def _scope(business, shop_id, shops) -> dict:
    shop_name = None
    if shop_id is not None:
        match = next((shop for shop in shops if shop.id == shop_id), None)
        shop_name = match.shop_name if match else None
    return {
        'mode': 'owner',
        'business_id': business.id,
        'shop_id': shop_id,
        'shop_name': shop_name,
        'catalog': 'owner',
    }


def _limits(business, owner, owner_fabric_count: int) -> dict:
    plus = serialize_owner_plus(business, owner_user=owner)
    limit = None if is_owner_plus_active(business=business, owner=owner) else FREE_OWNER_CATALOG_PRODUCTS
    used_toward_limit = count_owner_catalog_products(business.id)
    return {
        'tier': plus['tier'],
        'owner_plus_active': plus['is_active'],
        'owner_fabrics': owner_fabric_count,
        'owner_catalog_limit': limit,
        'catalog_products_counted_toward_limit': used_toward_limit,
        'near_limit': limit is not None and used_toward_limit >= max(limit - 5, 0),
        'report_analytics_days': plus['limits']['report_analytics_days'],
    }


def _catalog_health(products, now) -> dict:
    def has_photo(product):
        return any(True for _ in product.gallery.all())

    return {
        'total': len(products),
        'active': sum(1 for product in products if product.is_active),
        'inactive': sum(1 for product in products if not product.is_active),
        'approved': sum(1 for product in products if product.approval_status == 'approved'),
        'pending': sum(1 for product in products if product.approval_status == 'pending'),
        'rejected': sum(1 for product in products if product.approval_status == 'rejected'),
        'featured': sum(1 for product in products if product.is_featured),
        'on_sale': sum(1 for product in products if product.is_on_sale),
        'sale_active': sum(1 for product in products if sale_is_active(product, now)),
        'with_photo': sum(1 for product in products if has_photo(product)),
        'missing_photo': sum(1 for product in products if not has_photo(product)),
        'missing_country': sum(1 for product in products if product.country_id is None),
        'missing_type': sum(1 for product in products if product.fabric_type_id is None),
        'missing_category': sum(1 for product in products if product.category_id is None),
        'missing_stitching_price': sum(1 for product in products if product.stitching_price is None),
    }


def _owner_card(product, *, by_product, by_shop, movement_map, low_stock_threshold, shop_id, now, request):
    assignments = list(product.shop_assignments.all())
    if shop_id is not None:
        visible_assignments = [row for row in assignments if row.shop_id == shop_id]
    else:
        visible_assignments = assignments
    active_assignments = [row for row in visible_assignments if row.is_active]
    sales = by_product.get(product.id, empty_sales())
    shops = [
        _shop_assignment_row(product, row, by_shop, movement_map, low_stock_threshold)
        for row in visible_assignments
    ]
    stock = sum(row.stock for row in active_assignments)
    reserved = sum(row.reserved_stock for row in active_assignments)
    available = max(stock - reserved, 0)
    list_price = money(product.price)
    effective = list_price
    if shop_id is not None and active_assignments:
        effective = money(active_assignments[0].effective_price)
    return {
        'product_id': product.id,
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
        'price': list_price,
        'effective_price': effective,
        'stitching_price': money(product.stitching_price) if product.stitching_price is not None else None,
        'discount_price': money(product.discount_price) if product.discount_price is not None else None,
        'is_on_sale': product.is_on_sale,
        'sale_active': sale_is_active(product, now),
        'sale_start': isoformat(product.sale_start),
        'sale_end': isoformat(product.sale_end),
        'is_active': product.is_active,
        'is_featured': product.is_featured,
        'approval_status': product.approval_status,
        'assigned_shop_count': sum(1 for row in assignments if row.is_active),
        'assigned_to_scope': bool(active_assignments) if shop_id is not None else bool(assignments),
        'stock': stock,
        'reserved_stock': reserved,
        'available_stock': available,
        'is_low_stock': 0 < available <= low_stock_threshold,
        'is_out_of_stock': bool(active_assignments) and available == 0,
        'units_sold': sales['units_sold'],
        'revenue': sales['revenue'],
        'order_count': sales['order_count'],
        'share_pct': 0.0,
        'last_sold_at': isoformat(sales['last_sold_at']),
        'created_at': isoformat(product.created_at),
        'updated_at': isoformat(product.updated_at),
        'shops': shops,
    }


def _shop_assignment_row(product, shop_fabric, by_shop, movement_map, low_stock_threshold) -> dict:
    sales = by_shop.get((product.id, shop_fabric.shop_id), empty_sales())
    movement = movement_map.get(shop_fabric.id, {})
    available = shop_fabric.available_stock
    return {
        'shop_fabric_id': shop_fabric.id,
        'shop_id': shop_fabric.shop_id,
        'shop_name': shop_fabric.shop.shop_name,
        'legacy_fabric_id': shop_fabric.legacy_fabric_id,
        'stock': shop_fabric.stock,
        'reserved_stock': shop_fabric.reserved_stock,
        'available_stock': available,
        'is_low_stock': 0 < available <= low_stock_threshold,
        'is_out_of_stock': available == 0,
        'price_override': money(shop_fabric.price_override) if shop_fabric.price_override is not None else None,
        'effective_price': money(shop_fabric.effective_price),
        'is_visible': shop_fabric.is_visible,
        'is_active': shop_fabric.is_active,
        'units_sold': sales['units_sold'],
        'revenue': money(sales['revenue']),
        'order_count': sales['order_count'],
        'last_sold_at': isoformat(sales['last_sold_at']),
        'last_movement_at': isoformat(movement.get('last_movement_at')),
        'last_movement_type': movement.get('last_movement_type'),
    }


def _network_stock(scoped_cards, all_cards, low_stock_threshold: int) -> dict:
    assigned = [card for card in scoped_cards if card['assigned_shop_count'] or card['shops']]
    return {
        'on_hand': sum(card['stock'] for card in scoped_cards),
        'reserved': sum(card['reserved_stock'] for card in scoped_cards),
        'available': sum(card['available_stock'] for card in scoped_cards),
        'low_stock_threshold': low_stock_threshold,
        'skus_assigned': len(assigned),
        'skus_unassigned': sum(1 for card in all_cards if card['assigned_shop_count'] == 0),
        'skus_out_of_stock': sum(1 for card in scoped_cards if card['is_out_of_stock']),
        'skus_low_stock': sum(1 for card in scoped_cards if card['is_low_stock']),
        'skus_never_sold': sum(1 for card in scoped_cards if card['units_sold'] == 0),
    }


def _sales_summary(sales_qs, cards) -> dict:
    summary = summarize_sales(sales_qs)
    best = max(cards, key=lambda card: (card['units_sold'], card['name']), default=None)
    summary['sku_count'] = len(cards)
    summary['skus_sold'] = sum(1 for card in cards if card['units_sold'] > 0)
    summary['skus_never_sold'] = sum(1 for card in cards if card['units_sold'] == 0)
    summary['best_seller'] = None
    if best and best['units_sold'] > 0:
        summary['best_seller'] = {
            'product_id': best['product_id'],
            'name': best['name'],
            'units_sold': best['units_sold'],
            'revenue': best['revenue'] if isinstance(best['revenue'], str) else money(best['revenue']),
        }
    return summary


def _assignments(cards, shops, shop_id, low_stock_threshold: int) -> dict:
    shop_rows = shops
    if shop_id is not None:
        shop_rows = [shop for shop in shops if shop.id == shop_id]
    by_shop = []
    owner_fabric_count = len(cards)
    for shop in shop_rows:
        listings = []
        for card in cards:
            match = next((row for row in card['shops'] if row['shop_id'] == shop.id and row['is_active']), None)
            if match:
                listings.append((card, match))
        stock = sum(match['stock'] for _, match in listings)
        units = sum(match['units_sold'] for _, match in listings)
        revenue = sum(Decimal(match['revenue']) for _, match in listings)
        by_shop.append({
            'shop_id': shop.id,
            'shop_name': shop.shop_name,
            'owner_fabric_count': len(listings),
            'missing_count': owner_fabric_count - len(listings),
            'stock': stock,
            'units_sold': units,
            'revenue': money(revenue),
            'low_stock_count': sum(1 for _, match in listings if match['is_low_stock'] or match['is_out_of_stock']),
        })
    by_fabric = []
    for card in cards:
        shop_rows_for_card = [row for row in card['shops'] if row['is_active']]
        best = max(shop_rows_for_card, key=lambda row: (row['units_sold'], row['stock']), default=None)
        by_fabric.append({
            'product_id': card['product_id'],
            'name': card['name'],
            'sku': card['sku'],
            'image_url': card['image_url'],
            'assigned_shop_count': card['assigned_shop_count'],
            'unassigned': card['assigned_shop_count'] == 0,
            'total_stock': card['stock'],
            'units_sold': card['units_sold'],
            'best_shop': None if best is None or best['units_sold'] == 0 else {
                'shop_id': best['shop_id'],
                'shop_name': best['shop_name'],
                'units_sold': best['units_sold'],
            },
            'out_of_stock_shop_count': sum(1 for row in shop_rows_for_card if row['is_out_of_stock']),
        })
    return {'by_fabric': by_fabric, 'by_shop': by_shop, 'low_stock_threshold': low_stock_threshold}


def _shop_breakdown(cards, shops, shop_id) -> list[dict]:
    rows = []
    shop_rows = shops if shop_id is None else [shop for shop in shops if shop.id == shop_id]
    total_units = 0
    pending = []
    for shop in shop_rows:
        units = 0
        revenue = Decimal('0')
        stock = 0
        sku_count = 0
        top = None
        for card in cards:
            match = next((row for row in card['shops'] if row['shop_id'] == shop.id and row['is_active']), None)
            if match is None:
                continue
            sku_count += 1
            units += match['units_sold']
            revenue += Decimal(match['revenue'])
            stock += match['stock']
            if top is None or match['units_sold'] > top['units_sold']:
                top = {
                    'product_id': card['product_id'],
                    'name': card['name'],
                    'units_sold': match['units_sold'],
                }
        total_units += units
        pending.append((shop, units, revenue, stock, sku_count, top))
    for shop, units, revenue, stock, sku_count, top in pending:
        rows.append({
            'key': str(shop.id),
            'shop_id': shop.id,
            'name': shop.shop_name,
            'units_sold': units,
            'revenue': money(revenue),
            'sku_count': sku_count,
            'stock_on_hand': stock,
            'share_pct': share_pct(units, total_units),
            'top_product': top,
        })
    rows.sort(key=lambda row: (-row['units_sold'], row['name']))
    return rows


def _alerts(cards, products, low_stock_threshold: int, shop_id: int | None) -> list[dict]:
    product_by_id = {product.id: product for product in products}
    alerts = [
        make_alert(
            'unassigned',
            'warning',
            'Owner fabrics are not assigned to any shop.',
            [card['product_id'] for card in cards if card['assigned_shop_count'] == 0],
        ),
        make_alert(
            'out_of_stock',
            'critical',
            'Assigned owner fabrics are out of stock.',
            [card['product_id'] for card in cards if card['is_out_of_stock']],
        ),
        make_alert(
            'sold_while_out',
            'critical',
            'These owner fabrics sold in this period and are now out of stock.',
            [
                card['product_id']
                for card in cards
                if card['is_out_of_stock'] and card['units_sold'] > 0
            ],
        ),
        make_alert(
            'low_stock',
            'warning',
            f'Available stock is at or below {low_stock_threshold}.',
            [card['product_id'] for card in cards if card['is_low_stock']],
        ),
        make_alert(
            'missing_photo',
            'info',
            'Owner fabrics are missing a photo.',
            [card['product_id'] for card in cards if not card['image_url']],
        ),
        make_alert(
            'missing_country',
            'info',
            'Owner fabrics have no country.',
            [card['product_id'] for card in cards if card['country'] is None],
        ),
        make_alert(
            'pending_approval',
            'warning',
            'Owner fabrics are waiting for approval.',
            [card['product_id'] for card in cards if card['approval_status'] == 'pending'],
        ),
        make_alert(
            'rejected',
            'warning',
            'Owner fabrics were rejected.',
            [card['product_id'] for card in cards if card['approval_status'] == 'rejected'],
        ),
        make_alert(
            'sale_misconfigured',
            'warning',
            'Sale is on but the discount or dates are incomplete.',
            [
                card['product_id']
                for card in cards
                if sale_is_misconfigured(product_by_id[card['product_id']])
            ],
        ),
        make_alert(
            'stock_imbalance',
            'info',
            'Out of stock in one shop while another shop still has this fabric.',
            _imbalanced_product_ids(cards),
        ),
    ]
    if shop_id is not None:
        alerts.append(make_alert(
            'not_on_shop',
            'info',
            'Owner fabrics are not assigned to this shop.',
            [card['product_id'] for card in cards if not card['assigned_to_scope']],
        ))
    return compact_alerts(alerts)


def _imbalanced_product_ids(cards) -> list[int]:
    ids = []
    for card in cards:
        active = [row for row in card['shops'] if row['is_active']]
        if len(active) < 2:
            continue
        if any(row['available_stock'] == 0 for row in active) and any(row['available_stock'] > 0 for row in active):
            ids.append(card['product_id'])
    return ids
