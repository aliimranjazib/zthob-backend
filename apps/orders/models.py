from django.db import models
from django.conf import settings
from apps.core.models import BaseModel
from decimal import Decimal

# Create your models here.
class Order(BaseModel):
    """
    Order Status Flow Documentation:
    
    Order Types:
    - FABRIC_ONLY: Just purchase fabric/item (no stitching required)
    - FABRIC_WITH_STITCHING: Purchase fabric + get it stitched
    
    Category-Based Order Types:
    - Fabric Category: 2 options (FABRIC_ONLY OR FABRIC_WITH_STITCHING)
    - Other Categories (caps, handkerchief, etc.): 1 option (FABRIC_ONLY only - just buy it)
    
    Status Flows:
    FABRIC_ONLY Flow (for all categories):
    1. pending -> confirmed -> ready_for_delivery -> delivered
    
    FABRIC_WITH_STITCHING Flow (fabric category only):
    1. pending -> confirmed -> measuring -> cutting -> stitching -> ready_for_delivery -> delivered
    
    Role-Based Status Update Permissions:
    - CUSTOMERS (USER): Can only cancel orders (pending -> cancelled)
    - TAILORS (TAILOR): Can update all statuses except cancellation
    - ADMINS (ADMIN): Can do everything (full control)
    
    Cancellation Rules:
    - Can only be cancelled when status is 'pending'
    - Only customers can cancel their own orders
    - Tailors cannot cancel orders (only customers can)
    - Once 'confirmed' or beyond, no cancellation allowed
    - Once 'delivered' or 'cancelled', no further changes allowed
    
    Status Meanings:
    - pending: Order created, waiting for tailor confirmation
    - confirmed: Tailor accepted the order
    - measuring: Taking customer measurements (stitching orders only)
    - cutting: Cutting fabric (stitching orders only)
    - stitching: Sewing the garment (stitching orders only)
    - ready_for_delivery: Order ready for delivery
    - delivered: Order completed and delivered to customer
    - cancelled: Order cancelled (final state)
    """
    ORDER_TYPE_CHOICES = (
        ('fabric_only', 'Fabric Purchase Only'),
        ('fabric_with_stitching', 'Fabric + Stitching'),
    )
    
    # Main order status (simplified)
    ORDER_STATUS_CHOICES=(
        ("pending", "Pending"),                    # Initial state - waiting for tailor
        ("confirmed", "Confirmed"),                # Tailor accepted the order
        ("in_progress", "In Progress"),           # Order being processed
        ("ready_for_delivery", "Ready for Delivery"), # Order ready for delivery
        ("delivered", "Delivered"),                # Order completed (final state)
        ("cancelled", "Cancelled"),                # Order cancelled (final state)
    )
    
    # Rider activity status
    RIDER_STATUS_CHOICES = (
        ("none", "Not Assigned"),                  # No rider assigned yet
        ("accepted", "Accepted Order"),            # Rider accepted the order
        ("on_way_to_pickup", "On Way to Pickup"),  # Rider en route to pickup from tailor
        ("picked_up", "Picked Up"),               # Rider picked up order from tailor
        ("on_way_to_delivery", "On Way to Delivery"), # Rider en route to customer
        ("on_way_to_measurement", "On Way to Measurement"), # Rider en route to take measurements (stitching only)
        ("measurement_taken", "Measurement Taken"), # Rider took measurements (stitching only)
        ("delivered", "Delivered"),                # Rider delivered to customer
    )
    
    # Tailor activity status
    TAILOR_STATUS_CHOICES = (
        ("none", "None"),                          # No tailor activity
        ("accepted", "Accepted Order"),           # Tailor accepted the order
        ("in_progress", "In Progress"),           # Tailor working on order (fabric_only)
        ("ready_for_delivery", "Ready for Delivery"), # Order ready for pickup (fabric_only)
        ("stitching_started", "Started Stitching"), # Tailor started stitching (fabric_with_stitching only)
        ("stitched", "Finished Stitching"),       # Tailor finished stitching (fabric_with_stitching only)
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
    rider=models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rider_orders',
        help_text='Rider assigned to this order for delivery'
    )
    order_type=models.CharField(
        max_length=25,
        choices=ORDER_TYPE_CHOICES,
        default='fabric_with_stitching',
        help_text="Type of order - fabric only or fabric with stitching"
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
    help_text="Main status of the order"
    )
    
    rider_status=models.CharField(
        max_length=30,
        choices=RIDER_STATUS_CHOICES,
        default="none",
        help_text="Current rider activity status"
    )
    
    tailor_status=models.CharField(
        max_length=30,
        choices=TAILOR_STATUS_CHOICES,
        default="none",
        help_text="Current tailor activity status"
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

    family_member=models.ForeignKey(
    'customers.FamilyMember',
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    help_text="Family member this order is for (optional - if not specified, order is for the customer)"
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
    
    # Rider measurements (for fabric_with_stitching orders)
    rider_measurements = models.JSONField(
        default=dict,
        blank=True,
        null=True,
        help_text="Measurements taken by rider at customer location (for fabric_with_stitching orders)"
    )
    
    measurement_taken_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When measurements were taken by the rider"
    )
    
    # Appointment fields
    appointment_date = models.DateField(
        null=True,
        blank=True,
        help_text="Appointment date for customer (optional)"
    )
    appointment_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Appointment time for customer (optional)"
    )
    
    # Custom styles for the order
    custom_styles = models.JSONField(
        default=None,
        blank=True,
        null=True,
        help_text="Array of custom style selections (optional). Format: [{'style_type': 'collar', 'index': 0, 'label': 'Collar Style 1', 'asset_path': 'assets/thobs/collar/collar1.png'}]"
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

    def recalculate_totals(self):
        from apps.orders.services import OrderCalculationService
        items_data=[]
        for item in self.order_items.all():
            items_data.append({
                'fabric':item.fabric,
                'quantity':item.quantity,
            })
        totals = OrderCalculationService.calculate_all_totals(
                items_data,
                delivery_address=self.delivery_address,
                tailor=self.tailor,
                order_type=self.order_type
        )
        self.subtotal = totals['subtotal']
        self.tax_amount = totals['tax_amount']
        self.delivery_fee = totals['delivery_fee']
        # Remove stitching_price from totals if it exists (Order model doesn't have this field yet)
        totals.pop('stitching_price', None)
        self.total_amount = totals['total_amount']
        self.save(update_fields=['subtotal', 'tax_amount', 'delivery_fee', 'total_amount'])

    def __str__(self):
        # Get tailor name from profile if available
        try:
            if hasattr(self.tailor, 'tailor_profile') and self.tailor.tailor_profile:
                tailor_name = self.tailor.tailor_profile.shop_name or self.tailor.username
            else:
                tailor_name = self.tailor.username if self.tailor else 'Unknown'
        except (AttributeError, Exception):
            tailor_name = self.tailor.username if self.tailor else 'Unknown'
        
        # Get recipient name
        if self.family_member and self.family_member.name:
            recipient = self.family_member.name
        else:
            recipient = self.customer.username if self.customer else 'Unknown'
        
        # Get customer username
        customer_name = self.customer.username if self.customer else 'Unknown'
        
        return f"Order {self.order_number or 'N/A'} - {recipient} (by {customer_name}) to {tailor_name}"

    @property
    def items_count(self):
        """ Return total number of items in this orders """
        return self.order_items.count()

    @property
    def can_be_cancelled(self):
        """Check if order can still be cancelled"""
        return self.status in ['pending','confirmed']
    
    def get_allowed_status_transitions(self, user_role=None):
        """
        Get allowed status transitions based on order type.
        Now uses OrderStatusTransitionService for consistency.
        For backward compatibility, returns old format if user_role not provided.
        """
        from apps.orders.services import OrderStatusTransitionService
        
        if user_role:
            # Use the new service-based approach
            transitions = OrderStatusTransitionService.get_allowed_transitions(self, user_role)
            # Convert to old format for backward compatibility
            result = {}
            if transitions['status']:
                result[self.status] = transitions['status']
            return result
        else:
            # Legacy format for backward compatibility
            if self.order_type == 'fabric_only':
                return {
                    'pending': ['confirmed', 'cancelled'],
                    'confirmed': ['in_progress'],
                    'in_progress': ['ready_for_delivery'],
                    'ready_for_delivery': ['delivered'],
                    'delivered': [],
                    'cancelled': []
                }
            else:  # fabric_with_stitching
                return {
                    'pending': ['confirmed', 'cancelled'],
                    'confirmed': ['in_progress'],
                    'in_progress': ['ready_for_delivery'],
                    'ready_for_delivery': ['delivered'],
                    'delivered': [],
                    'cancelled': []
                }

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

