"""Unique fabric name validation (per shop and owner catalog)."""

from __future__ import annotations

from rest_framework import serializers

DUPLICATE_SHOP_FABRIC_NAME_MESSAGE = (
    'A fabric with this name already exists for this shop.'
)
DUPLICATE_OWNER_CATALOG_FABRIC_NAME_MESSAGE = (
    'A fabric with this name already exists in your catalog.'
)
DUPLICATE_LEGACY_FABRIC_NAME_MESSAGE = (
    'A fabric with this name already exists for this shop.'
)


def normalize_fabric_name(name: str | None) -> str:
    return (name or '').strip()


def validate_fabric_name_for_shop(
    shop_id: int,
    name: str | None,
    *,
    exclude_product_id: int | None = None,
) -> None:
    normalized = normalize_fabric_name(name)
    if not normalized:
        return

    from apps.fabrics.models import ShopFabric

    qs = ShopFabric.objects.filter(
        shop_id=shop_id,
        is_active=True,
        product__name__iexact=normalized,
    )
    if exclude_product_id is not None:
        qs = qs.exclude(product_id=exclude_product_id)
    if qs.exists():
        raise serializers.ValidationError({'name': DUPLICATE_SHOP_FABRIC_NAME_MESSAGE})


def validate_fabric_name_for_business_owner_catalog(
    business_id: int,
    name: str | None,
    *,
    exclude_product_id: int | None = None,
) -> None:
    normalized = normalize_fabric_name(name)
    if not normalized:
        return

    from apps.fabrics.models import FabricProduct

    qs = FabricProduct.objects.filter(
        business_id=business_id,
        show_in_owner_catalog=True,
        name__iexact=normalized,
    )
    if exclude_product_id is not None:
        qs = qs.exclude(id=exclude_product_id)
    if qs.exists():
        raise serializers.ValidationError(
            {'name': DUPLICATE_OWNER_CATALOG_FABRIC_NAME_MESSAGE}
        )


def validate_fabric_name_for_legacy_tailor(
    tailor_id: int,
    name: str | None,
    *,
    exclude_fabric_id: int | None = None,
) -> None:
    normalized = normalize_fabric_name(name)
    if not normalized:
        return

    from apps.tailors.models import Fabric

    qs = Fabric.objects.filter(tailor_id=tailor_id, name__iexact=normalized)
    if exclude_fabric_id is not None:
        qs = qs.exclude(pk=exclude_fabric_id)
    if qs.exists():
        raise serializers.ValidationError({'name': DUPLICATE_LEGACY_FABRIC_NAME_MESSAGE})
