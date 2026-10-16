"""Query filters for owner catalog and shop shelf lists."""

from __future__ import annotations

from django.db.models import IntegerField, Q, Sum, Value
from django.db.models.functions import Coalesce

OWNER_SORTS = {
    'newest': '-created_at',
    'name': 'name',
    'price_asc': 'price',
    'price_desc': '-price',
    'best_selling': '-units_sold',
}

SHOP_SORTS = {
    'newest': '-created_at',
    'name': 'product__name',
    'price_asc': 'sort_price',
    'price_desc': '-sort_price',
    'stock_asc': 'stock',
    'stock_desc': '-stock',
    'best_selling': '-units_sold',
}


def filter_owner_catalog(queryset, params: dict):
    queryset = _apply_product_filters(queryset, params, prefix='')
    sort = params.get('sort') or 'newest'
    if sort == 'best_selling':
        queryset = queryset.annotate(units_sold=_units_sold('shop_assignments__legacy_fabric__orderitem_set'))
    return queryset.order_by(OWNER_SORTS.get(sort, '-created_at'), '-id')


def filter_shop_fabrics(queryset, params: dict):
    queryset = _apply_product_filters(queryset, params, prefix='product__')
    source = params.get('source') or 'all'
    if source == 'from_owner':
        queryset = queryset.filter(product__show_in_owner_catalog=True)
    elif source == 'shop_own':
        queryset = queryset.filter(product__show_in_owner_catalog=False)

    stock = params.get('stock')
    threshold = params.get('low_stock_threshold', 5)
    if stock == 'out':
        queryset = queryset.filter(stock=0)
    elif stock == 'low':
        queryset = queryset.filter(stock__gt=0, stock__lte=threshold)
    elif stock == 'in':
        queryset = queryset.filter(stock__gt=threshold)

    sort = params.get('sort') or 'newest'
    if sort in ('price_asc', 'price_desc'):
        queryset = queryset.annotate(sort_price=Coalesce('price_override', 'product__price'))
    if sort == 'best_selling':
        queryset = queryset.annotate(units_sold=_units_sold('legacy_fabric__orderitem_set'))
    return queryset.order_by(SHOP_SORTS.get(sort, '-created_at'), '-id')


def _apply_product_filters(queryset, params: dict, *, prefix: str):
    query = (params.get('q') or '').strip()
    if query:
        queryset = queryset.filter(
            Q(**{f'{prefix}name__icontains': query}) | Q(**{f'{prefix}sku__icontains': query})
        )
    if params.get('country_id'):
        queryset = queryset.filter(**{f'{prefix}country_id': params['country_id']})
    if params.get('category_id'):
        queryset = queryset.filter(**{f'{prefix}category_id': params['category_id']})
    if params.get('fabric_type_id'):
        queryset = queryset.filter(**{f'{prefix}fabric_type_id': params['fabric_type_id']})
    if params.get('season'):
        queryset = queryset.filter(**{f'{prefix}seasons': params['season']})
    if 'on_sale' in params:
        queryset = queryset.filter(**{f'{prefix}is_on_sale': params['on_sale']})
    return queryset


def _units_sold(order_item_prefix: str):
    return Coalesce(
        Sum(
            f'{order_item_prefix}__quantity',
            filter=~Q(**{f'{order_item_prefix}__order__status': 'cancelled'}),
        ),
        Value(0),
        output_field=IntegerField(),
    )
