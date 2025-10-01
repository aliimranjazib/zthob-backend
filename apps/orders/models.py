from django.db import models
from django.conf import settings
from apps.core.models import BaseModel
from decimal import Decimal

# Create your models here.
class Order(BaseModel):
    ORDER_STATUS_CHOICES=(
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("measuring", "Measuring"),
        ("cutting", "Cutting"),
        ("stitching", "Stitching"),
        ("ready_for_delivery", "Ready for Delivery"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
    )
    PAYMENT_STATUS_CHOICES = (
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("refunded", "Refunded"),
    )
    PAYMENT_METHOD_CHOICES = (
        ("cod", "Cash on Delivery"),
        ("credit_card", "Credit Card"),
        ("bank_transfer", "Bank Transfer"),
    )

    customer=models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.CASCADE,
    related_name="customer_orders",
    help_text="The customer who placed the order"
    )
    tailor=models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.CASCADE,
    related_name='tailor_orders',
    help_text='Tailor assigned to this order'
    )
    order_number=models.CharField(
    max_length=20,
    unique=True,
    editable=False,
    help_text="Unique order number generated automatically"

    )
    status=models.CharField(
    max_length=20,
    choices=ORDER_STATUS_CHOICES,
    default="pending",
    help_text="current status of the order"
    )

    subtotal=models.DecimalField(
    max_digits=10,
    decimal_places=2,
    default=Decimal('0.00'),
    help_text="sub total before taxes and fees"
    )

    tax_amount=models.DecimalField(
    max_digits=10,
    decimal_places=2,
    default=Decimal('0.00'),
    help_text="Tax amount"
    )

    delivery_fee=models.DecimalField(
    max_digits=10,
    decimal_places=2,
    default=Decimal('0.00'),
    help_text="delivery fee"
    )

    total_amount=models.DecimalField(
    max_digits=10,
    decimal_places=2,
    default=Decimal('0.00'),
    help_text="Total amount including taxes and fees"
    )
    payment_status=models.CharField(
    max_length=20,
    choices=PAYMENT_STATUS_CHOICES,
    default='pending',
    help_text='Payment_status'
    )
    payment_method=models.CharField(
    max_length=20,
    choices=PAYMENT_METHOD_CHOICES,
    default='credit_card',
    help_text="Payment method chosen by customer"
    )

    delivery_address=models.ForeignKey(
    'customers.Address',
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='delivery_orders',
    help_text="Delivery address for this order"
    )

    estimated_delivery_date=models.DateField(
    null=True,
    blank=True,
    help_text="Estimated delivery time"
    )
    actual_delivery_date = models.DateField(
    null=True,
    blank=True,
    help_text="Actual delivery time"
    )
    special_instructions=models.TextField(
    null=True,
    blank=True,
    help_text="Special instructions from customer"
    )
    notes=models.TextField(
    null=True,
    blank=True,
    help_text="Interal notes for tailor/admin"
    )

    class Meta:
        ordering=['-created_at']
        verbose_name='Order'
        verbose_name_plural='Orders'

    def clean(self):
        """Validate that tailor has TAILOR role"""
        if self.tailor and self.tailor.role != 'TAILOR':
            from django.core.exceptions import ValidationError
            raise ValidationError("Tailor must have TAILOR role")
    def save(self,*args,**kwargs):
        if not self.order_number:
           import uuid
           self.order_number = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        if not self.total_amount:
            self.total_amount=self.subtotal+self.tax_amount+self.delivery_fee

        super().save(*args, **kwargs)

    def __str__(self):
        tailor_name = getattr(self.tailor, 'tailor_profile', {}).get('shop_name', self.tailor.username)
        return f"Order {self.order_number} - {self.customer.username} to {tailor_name}"

    @property
    def items_count(self):
        """ Return total number of items in this orders """
        return self.order_items.count()

    @property
    def can_be_cancelled(self):
        """Check if order can still be cancelled"""
        return self.status in ['pending','confirmed']

class OrderItem(BaseModel):

    """
    Individual Item within an order
    """
    order=models.ForeignKey(
    Order,
    on_delete=models.CASCADE,
    related_name='order_items',
    help_text='Order this items belongs to'
    )

    fabric=models.ForeignKey(
    'tailors.Fabric',
    on_delete=models.CASCADE,
    help_text='Fabric beginf ordered'

    )

    quantity=models.PositiveIntegerField(
    default=1,
    help_text="Quantity of this fabric"
    )

    unit_price=models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Price per unit at time of order"
    )
    total_price=models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Total price for this item (quantity × unit_price)"
    )

    # Measurements and customizations
    measurements = models.JSONField(
        default=dict,
        blank=True,
        help_text="Customer measurements for this item"
    )

    custom_instructions=models.TextField(
    null=True,
    blank=True,
    help_text="Custom instructions for this specific item"
    )

    is_ready=models.BooleanField(
    default=False,
    help_text="Whether this item is ready for delivery"
    )

    class Meta:
        ordering = ['created_at']
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"

    def save(self,*args,**kwargs):
        self.total_price=self.quantity * self.unit_price
        super().save(*args,**kwargs)

    def __str__(self):
        return f"{self.fabric.name} x{self.quantity} - {self.order.order_number}"

class OrderStatusHistory(BaseModel):
    """
    Track status changes over time for audit trail
    """
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='status_history',
        help_text="Order this status change belongs to"
    )
    status = models.CharField(
        max_length=20,
        choices=Order.ORDER_STATUS_CHOICES,
        help_text="Status that was set"
    )
    previous_status = models.CharField(
        max_length=20,
        choices=Order.ORDER_STATUS_CHOICES,
        blank=True,
        null=True,
        help_text="Previous status before this change"
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="User who made this status change"
    )
    
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Notes about this status change"
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Order Status History"
        verbose_name_plural = "Order Status Histories"
    
    def __str__(self):
        return f"{self.order.order_number}: {self.previous_status} → {self.status}"

