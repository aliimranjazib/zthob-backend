from decimal import Decimal
from django.db import transaction
from django.conf import settings
from apps.tailors.models import Fabric,TailorProfile

class OrderCalculationService:

    """
    Service for calculating order totals and handling order business logic.
    """

    DEFAULT_TAX_RATE=Decimal('0.15')
    DEFAULT_DELIVERY_FEE=Decimal('25.00')
    FREE_DELIVERY_THRESHOLD=Decimal('500.00')

    @staticmethod
    def calculate_subtotal(items_data):

        subtotal=Decimal('0.00')
        for item in items_data:
            fabric=item['fabric']
            quantity=Decimal(str(item.get('quantity',1)))
            unit_price=fabric.price
            subtotal+=unit_price*quantity
        return subtotal.quantize(Decimal('0.01'))
    @staticmethod
    def calculate_tax(subtotal,tax_rate=None):
        if tax_rate is None:
            tax_rate=OrderCalculationService.DEFAULT_TAX_RATE
        if subtotal<=0:
            return Decimal('0.00')
        tax_amount=subtotal * tax_rate
        return tax_amount.quantize(Decimal('0.01'))

    @staticmethod
    def calculate_delivery_fee(subtotal,delivery_address=None,tailor=None):
        if subtotal >= OrderCalculationService.FREE_DELIVERY_THRESHOLD:
            return Decimal('0.00')
        return OrderCalculationService.DEFAULT_DELIVERY_FEE

    @staticmethod
    def calculate_all_totals(items_data,delivery_address=None,tailor=None, tax_rate=None):
        subtotal=OrderCalculationService.calculate_subtotal(items_data)
        tax_amount=OrderCalculationService.calculate_tax(subtotal,tax_rate)
        delivery_fee=OrderCalculationService.calculate_delivery_fee(subtotal,delivery_address,
        tailor
        )
        total_amount=subtotal+tax_amount+delivery_fee
        return {
            'subtotal': subtotal,
            'tax_amount':tax_amount,
            'delivery_fee':delivery_fee,
            'total_amount':total_amount.quantize(Decimal('0.01'))
        }





