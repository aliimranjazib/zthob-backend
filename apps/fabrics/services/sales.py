"""Order sale sync from legacy fabric rows."""

from apps.fabrics.models import FabricStockMovement
from apps.tailors.models import Fabric


def record_sale_from_legacy_fabric(
    *,
    fabric: Fabric,
    quantity: int,
    order_id: int | None = None,
    user=None,
) -> None:
    shop_fabric = getattr(fabric, 'v2_shop_fabric', None)
    if shop_fabric is None:
        return

    previous_stock = shop_fabric.stock
    new_stock = fabric.stock
    if previous_stock == new_stock:
        return

    shop_fabric.stock = new_stock
    shop_fabric.save(update_fields=['stock', 'updated_at'])

    FabricStockMovement.objects.create(
        shop_fabric=shop_fabric,
        movement_type=FabricStockMovement.TYPE_SALE,
        quantity=quantity,
        previous_stock=previous_stock,
        new_stock=new_stock,
        reason='order',
        order_id=order_id,
        created_by=user,
    )
