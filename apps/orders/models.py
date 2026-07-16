from django.db import models
from django.db.models import Q
from django.conf import settings
from django.utils import timezone
from django.dispatch import receiver
from apps.core.models import BaseModel
from decimal import Decimal
from django_fsm import FSMField, transition
from django_fsm.signals import post_transition

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
        ('stitching_only', 'Stitching Only'),
        ('measurement_service', 'Measurement Service Only'),
    )
    SERVICE_MODE_CHOICES = (
        ('home_delivery', 'Home Delivery'),
        ('walk_in', 'Walk-In Service'),
    )
    # Main order status (simplified)
    ORDER_STATUS_CHOICES=(
        ("pending", "Pending"),                    # Initial state
        ("confirmed", "Confirmed"),                # Tailor accepted
        ("in_progress", "In Progress"),            # Being processed
        ("ready_for_delivery", "Ready for Delivery"), # For Home Delivery
        ("ready_for_pickup", "Ready for Pickup"),   # NEW: For Walk-In orders
        ("delivered", "Delivered"),                # Completed (Home Delivery)
        ("collected", "Collected"),                # NEW: Completed (Walk-In)
        ("cancelled", "Cancelled"),                # Order cancelled
    )
    
    # Rider activity status
    RIDER_STATUS_CHOICES = (
        ("none", "Not Assigned"),                  # No rider assigned yet
        ("accepted", "Accepted Order"),            # Rider accepted the order
        ("on_way_to_pickup", "On Way to Pickup"),  # Rider en route to pickup from tailor
        ("picked_up", "Picked Up"),               # Rider picked up order from tailor
        ("on_way_to_delivery", "On Way to Delivery"), # Rider en route to customer
        ("on_way_to_measurement", "On Way to Measurement"), # Rider en route to take measurements (stitching only)
        ("measuring", "Measuring"), # Rider is taking measurements
        ("measurement_taken", "Measurement Taken"), # Rider took measurements (stitching only)
        ("delivered", "Delivered"),                # Rider delivered to customer
    )
    
    # Tailor activity status
    TAILOR_STATUS_CHOICES = (
        ("none", "New"),                          # No tailor activity
        ("accepted", "Accepted Order"),           # Tailor accepted the order
        ("in_progress", "In Progress"),           # Tailor is working on the order
        ("stitching_started", "Started Stitching"), # Tailor started stitching (stitching only)
        ("stitched", "Finished Stitching"),       # Tailor finished stitching (stitching only)
        ("measurements_complete", "Measurements Complete"),  # Measurement service complete
        ("record_measurements", "Record Measurements"),      # Virtual status for recording process
    )
    PAYMENT_STATUS_CHOICES = (
        ("pending", "Pending"),
        ("partially_paid", "Partially Paid"),
        ("paid", "Paid"),
        ("refunded", "Refunded"),
    )
    PAYMENT_METHOD_CHOICES = (
        ("cod", "Cash on Delivery"),
        ("credit_card", "Credit Card"),
        ("bank_transfer", "Bank Transfer"),
    )
    PAYMENT_PLAN_CHOICES = (
        ("full", "Full Payment"),
        ("partial", "Partial Payment"),
        ("pay_later", "Pay Later"),
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
    null=True,  # Allow null for home delivery measurement orders
    blank=True,
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
    assigned_rider=models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_deliveries',
        limit_choices_to={'role': 'RIDER'},
        help_text='Rider specifically assigned by tailor when accepting the order (used for targeted notifications)'
    )
    measurement_rider=models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='measurement_orders',
        limit_choices_to={'role': 'RIDER'},
        help_text='Rider assigned to take customer measurements'
    )
    delivery_rider=models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='delivery_orders',
        limit_choices_to={'role': 'RIDER'},
        help_text='Rider assigned to deliver the finished order'
    )
    order_type=models.CharField(
        max_length=25,
        choices=ORDER_TYPE_CHOICES,
        default='fabric_with_stitching',
        help_text="Type of order - fabric only, fabric with stitching, stitching only, or measurement service"
    )
    service_mode = models.CharField(
        max_length=20,
        choices=SERVICE_MODE_CHOICES,
        default='home_delivery',
        help_text="Service mode - Home Delivery or Walk-In"
    )
    order_number=models.CharField(
    max_length=20,
    unique=True,
    editable=False,
    help_text="Unique order number generated automatically"
    )

    idempotency_key = models.UUIDField(
        null=True,
        blank=True,
        unique=True,
        help_text="Unique key from frontend to prevent duplicate order creation"
    )

    status=models.CharField(
    max_length=20,
    choices=ORDER_STATUS_CHOICES,
    default="pending",
    db_index=True,
    help_text="Main status of the order"
    )
    
    rider_status=FSMField(
        max_length=30,
        choices=RIDER_STATUS_CHOICES,
        default="none",
        db_index=True,
        protected=False,  # Allow direct assignment for backward compatibility
        help_text="Current rider activity status"
    )
    
    tailor_status=FSMField(
        max_length=30,
        choices=TAILOR_STATUS_CHOICES,
        default="none",
        db_index=True,
        protected=False,  # Allow direct assignment for backward compatibility
        help_text="Current tailor activity status"
    )

    subtotal=models.DecimalField(
    max_digits=10,
    decimal_places=2,
    default=Decimal('0.00'),
    help_text="sub total before taxes and fees"
    )

    stitching_price=models.DecimalField(
    max_digits=10,
    decimal_places=2,
    default=Decimal('0.00'),
    help_text="Total stitching price for order (for fabric_with_stitching and stitching_only orders)"
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

    system_fee=models.DecimalField(
    max_digits=10,
    decimal_places=2,
    default=Decimal('0.00'),
    help_text="Fixed system fee (SAR)"
    )

    measurement_fee=models.DecimalField(
    max_digits=10,
    decimal_places=2,
    default=Decimal('0.00'),
    help_text="One-time measurement rider fee snapshot for this order"
    )

    total_amount=models.DecimalField(
    max_digits=10,
    decimal_places=2,
    default=Decimal('0.00'),
    help_text="Total amount including taxes and fees"
    )

    # Express Delivery (Extra Fast Stitching)
    is_express = models.BooleanField(
        default=False,
        help_text="Whether this order uses express delivery (extra fast stitching)"
    )
    express_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Extra fee for express delivery"
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
    payment_plan = models.CharField(
        max_length=20,
        choices=PAYMENT_PLAN_CHOICES,
        default='full',
        help_text="Customer selected payment plan"
    )
    payment_option = models.CharField(
        max_length=30,
        null=True,
        blank=True,
        help_text="Backend-controlled checkout payment option selected by customer"
    )
    payment_reference = models.CharField(
        max_length=150,
        null=True,
        blank=True,
        unique=True,
        help_text="External payment gateway reference for paid online orders"
    )
    deposit_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Advance amount paid at order creation for partial-payment orders"
    )
    paid_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total amount collected so far"
    )
    remaining_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Outstanding balance to collect before handover"
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

    delivery_latitude=models.DecimalField(
    max_digits=9,
    decimal_places=6,
    null=True,
    blank=True,
    help_text="Delivery latitude"
    )

    delivery_longitude=models.DecimalField(
    max_digits=9,
    decimal_places=6,
    null=True,
    blank=True,
    help_text="Delivery longitude"
    )
    delivery_formatted_address=models.TextField(
    null=True,
    blank=True,
    help_text="Formatted address from geocoding (current location)"
    )
    delivery_street=models.CharField(
    max_length=100,
    null=True,
    blank=True,
    help_text="Delivery street"
    )
    delivery_city=models.CharField(
    max_length=100,
    null=True,
    blank=True,
    help_text="Delivery city"
    )
    delivery_extra_info=models.TextField(
    null=True,
    blank=True,
    help_text="Delivery extra info"
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
    stitching_completion_date=models.DateField(
        null=True,
        blank=True,
        help_text="Stitching completion date"
    )
    stitching_completion_time=models.TimeField(
        null=True,
        blank=True,
        help_text="Stitching completion time"
    )

    
    # Custom styles for the order
    custom_styles = models.JSONField(
        default=None,
        blank=True,
        null=True,
        help_text="Array of custom style selections (optional). Format: [{'style_type': 'collar', 'index': 0, 'label': 'Collar Style 1', 'asset_path': 'assets/thobs/collar/collar1.png'}]"
    )
    
    # Free measurement tracking
    is_free_measurement = models.BooleanField(
        default=False,
        help_text="Whether this is a free first-time measurement order"
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
            self.total_amount=self.subtotal+self.stitching_price+self.tax_amount+self.delivery_fee+self.express_fee

        # Auto-sync main status based on rider_status and tailor_status
        # This preserves the existing auto-sync logic from OrderStatusTransitionService
        self._sync_main_status()

        super().save(*args, **kwargs)
    
    def _sync_main_status(self):
        """
        Safety net for syncing main status in final states.
        Middle-state transitions are now explicitly handled by OrderAction classes.
        """
        # 1. Delivered state
        if self.rider_status == 'delivered' or self.status == 'delivered':
            self.status = 'delivered'
            self.rider_status = 'delivered'
        
        # 2. Collected state (Walk-In)
        if self.status == 'collected':
            self.tailor_status = 'stitched' # Ensure tailor status is at least stitched

        # 3. Cancelled state
        if self.status == 'cancelled':
            # No changes needed
            pass

    # ============================================================================
    # RIDER FSM TRANSITIONS
    # ============================================================================
    
    @transition(field=rider_status, source='none', target='accepted')
    def rider_accept_order(self, user=None):
        """Rider accepts the order"""
        pass
    
    @transition(field=rider_status, source='accepted', target='on_way_to_pickup')
    def rider_start_pickup(self):
        """Rider starts going to pickup location (fabric_only)"""
        pass
    
    @transition(field=rider_status, source='accepted', target='on_way_to_measurement')
    def rider_start_measurement(self):
        """Rider starts going to take measurements (fabric_with_stitching)"""
        pass
    
    @transition(field=rider_status, source='on_way_to_measurement', target='measuring')
    def rider_start_measuring(self):
        """Rider starts taking measurements"""
        pass
    
    @transition(field=rider_status, source='measuring', target='measurement_taken')
    def rider_complete_measurements(self):
        """Rider completes measurements"""
        pass
    
    @transition(field=rider_status, source=['accepted', 'measurement_taken'], target='on_way_to_pickup')
    def rider_start_pickup_after_measurement(self):
        """Rider starts going to pickup after measurements (fabric_with_stitching)"""
        pass
    
    @transition(field=rider_status, source='on_way_to_pickup', target='picked_up')
    def rider_mark_picked_up(self):
        """Rider picks up order from tailor"""
        pass
    
    @transition(field=rider_status, source='picked_up', target='on_way_to_delivery')
    def rider_start_delivery(self):
        """Rider starts delivery to customer"""
        pass
    
    @transition(field=rider_status, source='on_way_to_delivery', target='delivered')
    def rider_mark_delivered(self):
        """Rider delivers order to customer"""
        self.actual_delivery_date = timezone.now().date()
    
    # ============================================================================
    # TAILOR FSM TRANSITIONS
    # ============================================================================
    
    @transition(field=tailor_status, source='none', target='accepted')
    def tailor_accept_order(self, user=None):
        """Tailor accepts the order"""
        pass
    
    @transition(field=tailor_status, source='accepted', target='in_progress')
    def tailor_start_work(self):
        """Tailor starts working on order"""
        pass
    
    @transition(field=tailor_status, source=['accepted', 'in_progress'], target='stitching_started')
    def tailor_start_stitching(self):
        """Tailor starts stitching (fabric_with_stitching only)"""
        pass
    
    @transition(field=tailor_status, source='stitching_started', target='stitched')
    def tailor_finish_stitching(self):
        """Tailor finishes stitching"""
        pass

    # ============================================================================
    # CUSTOMER ACTIONS
    # ============================================================================
    def mark_as_collected(self):
        """Allow customer to mark the order as collected (for Walk-In Mode)"""
        if self.service_mode == 'walk_in' and self.status == 'ready_for_pickup':
            self.status = 'collected'
            self.save()
            return True, "Order marked as collected"
        return False, "Order is not ready for pickup or not a walk-in order"


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
                order_type=self.order_type,
                service_mode=self.service_mode
        )
        self.subtotal = totals['subtotal']
        self.stitching_price = totals.get('stitching_price', Decimal('0.00'))
        self.tax_amount = totals['tax_amount']
        self.delivery_fee = totals['delivery_fee']
        self.system_fee = totals.get('system_fee', Decimal('0.00'))
        self.measurement_fee = totals.get('measurement_fee', Decimal('0.00'))
        self.express_fee = totals.get('express_fee', Decimal('0.00'))
        self.total_amount = totals['total_amount']
        self.save(update_fields=['subtotal', 'stitching_price', 'tax_amount', 'delivery_fee', 'system_fee', 'measurement_fee', 'express_fee', 'total_amount'])

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
            # Check items for recipients
            item_recipients = self.order_items.filter(family_member__isnull=False).values_list('family_member__name', flat=True).distinct()
            if item_recipients.exists():
                recipient = f"Family ({', '.join(item_recipients)})"
                # If customer is also a recipient
                if self.order_items.filter(family_member__isnull=True).exists():
                    recipient = f"{self.customer.username} & {recipient}"
            else:
                recipient = self.customer.username if self.customer else 'Unknown'
        
        # Get customer username
        customer_name = self.customer.username if self.customer else 'Unknown'
        
        return f"Order {self.order_number or 'N/A'} - {recipient} (by {customer_name}) to {tailor_name}"

    @property
    def has_remaining_balance(self):
        return (self.remaining_amount or Decimal('0.00')) > Decimal('0.00')

    def apply_payment_summary(self, paid_amount=None, payment_plan=None, payment_option=None, save=True):
        """Synchronize payment summary fields from the collected amount."""
        total = self.total_amount or Decimal('0.00')
        paid = Decimal(paid_amount if paid_amount is not None else self.paid_amount or Decimal('0.00'))
        if paid < Decimal('0.00'):
            paid = Decimal('0.00')
        if paid > total:
            paid = total

        self.paid_amount = paid
        self.remaining_amount = total - paid
        if payment_plan:
            self.payment_plan = payment_plan
        if payment_option:
            self.payment_option = payment_option

        if self.payment_status != 'refunded':
            if total == Decimal('0.00') or self.remaining_amount == Decimal('0.00'):
                self.payment_status = 'paid'
            elif self.paid_amount > Decimal('0.00'):
                self.payment_status = 'partially_paid'
            else:
                self.payment_status = 'pending'

        if save:
            self.save(update_fields=[
                'payment_plan',
                'payment_option',
                'payment_status',
                'paid_amount',
                'remaining_amount',
                'updated_at',
            ])

    @property
    def items_count(self):
        """ Return total number of items in this orders """
        return self.order_items.count()

    @property
    def can_be_cancelled(self):
        """Check if order can still be cancelled"""
        return self.status in ['pending','confirmed']
    
    @property
    def all_items_have_measurements(self):
        """Check if all order items have measurements"""
        from apps.orders.measurement_utils import has_measurement_values

        # For fabric_only orders, measurements not required
        if self.order_type == 'fabric_only':
            return True

        if not self.order_items.exists():
            return False

        for item in self.order_items.all().only('measurements'):
            if not has_measurement_values(item.measurements):
                return False

        return True
    
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
    null=True,  # Allow null for measurement orders
    blank=True,  # Not required
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

    custom_styles = models.JSONField(
        default=None,
        blank=True,
        null=True,
        help_text="Custom style selections for this item. Format: [{'style_type': 'collar', 'index': 0, 'label': 'Collar Style 1', 'asset_path': 'assets/thobs/collar/collar1.png'}]"
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

    family_member=models.ForeignKey(
    'customers.FamilyMember',
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    help_text="Family member this item is for (optional - if not specified, item is for the customer)"
    )

    class Meta:
        ordering = ['created_at']
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"

    def save(self,*args,**kwargs):
        self.total_price=self.quantity * self.unit_price
        super().save(*args,**kwargs)

    def __str__(self):
        fabric_name = self.fabric.name if self.fabric else "No Fabric"
        return f"{fabric_name} x{self.quantity} - {self.order.order_number}"


class OrderPayment(BaseModel):
    PAYMENT_TYPE_CHOICES = (
        ('deposit', 'Deposit'),
        ('remaining_balance', 'Remaining Balance'),
        ('full_payment', 'Full Payment'),
        ('refund', 'Refund'),
        ('adjustment', 'Adjustment'),
    )
    PAYMENT_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    )

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='payments',
        help_text="Order this payment belongs to"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Payment amount"
    )
    payment_method = models.CharField(
        max_length=20,
        choices=Order.PAYMENT_METHOD_CHOICES,
        help_text="How this payment was collected"
    )
    payment_type = models.CharField(
        max_length=30,
        choices=PAYMENT_TYPE_CHOICES,
        help_text="Business purpose of this payment"
    )
    status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='paid',
        db_index=True
    )
    payment_reference = models.CharField(
        max_length=150,
        null=True,
        blank=True,
        unique=True,
        help_text="Gateway or manual collection reference"
    )
    collected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='collected_order_payments'
    )
    notes = models.TextField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order', 'status']),
            models.Index(fields=['payment_method', 'created_at']),
        ]

    def __str__(self):
        return f"{self.order.order_number} - {self.payment_type} - {self.amount}"


class CheckoutSession(BaseModel):
    """
    Temporary checkout draft. It lets customers review/pay before we create a real order.
    """
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('payment_initiated', 'Payment Initiated'),
        ('order_created', 'Order Created'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
        ('payment_failed', 'Payment Failed'),
    )

    booking_unique_key = models.CharField(
        max_length=40,
        unique=True,
        db_index=True,
        help_text="Public checkout key sent to the payment gateway/frontend"
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='checkout_sessions',
        help_text="Customer who owns this checkout draft"
    )
    order = models.OneToOneField(
        'orders.Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='checkout_session',
        help_text="Order created from this checkout session"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        db_index=True
    )
    request_payload = models.JSONField(
        help_text="Original order creation payload from the mobile app"
    )
    pricing_snapshot = models.JSONField(
        default=dict,
        blank=True,
        help_text="Backend-calculated totals shown on checkout"
    )
    client_idempotency_key = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_index=True,
        help_text="Optional frontend retry key for checkout creation"
    )
    payment_method = models.CharField(
        max_length=20,
        choices=Order.PAYMENT_METHOD_CHOICES,
        null=True,
        blank=True
    )
    payment_plan = models.CharField(
        max_length=20,
        choices=Order.PAYMENT_PLAN_CHOICES,
        null=True,
        blank=True
    )
    payment_option = models.CharField(max_length=30, null=True, blank=True)
    payment_reference = models.CharField(
        max_length=150,
        null=True,
        blank=True,
        unique=True,
        help_text="Gateway transaction/reference supplied after frontend payment"
    )
    payment_confirmed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(db_index=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Checkout Session'
        verbose_name_plural = 'Checkout Sessions'
        constraints = [
            models.UniqueConstraint(
                fields=['customer', 'client_idempotency_key'],
                condition=Q(client_idempotency_key__isnull=False),
                name='unique_customer_checkout_idempotency_key'
            )
        ]

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"{self.booking_unique_key} - {self.status}"


class RemainingPaymentSession(BaseModel):
    """
    Gateway-confirmed payment session for an existing order's outstanding balance.
    """
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('payment_initiated', 'Payment Initiated'),
        ('payment_completed', 'Payment Completed'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
        ('payment_failed', 'Payment Failed'),
    )

    booking_unique_key = models.CharField(
        max_length=40,
        unique=True,
        db_index=True,
        help_text="Public remaining-balance payment key sent to the payment gateway/frontend"
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='remaining_payment_sessions',
        help_text="Customer who owns this payment session"
    )
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.CASCADE,
        related_name='remaining_payment_sessions',
        help_text="Order whose remaining balance is being paid"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        db_index=True
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='SAR')
    payment_reference = models.CharField(
        max_length=150,
        null=True,
        blank=True,
        unique=True,
        help_text="Gateway transaction/reference supplied after verified payment"
    )
    payment_confirmed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order', 'status']),
            models.Index(fields=['customer', 'status']),
        ]

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"{self.booking_unique_key} - {self.order_id} - {self.status}"


class CheckoutPaymentAttempt(BaseModel):
    """A single MyFatoorah invoice attempt for checkout or remaining payment."""

    PURPOSE_CHOICES = (
        ('checkout', 'Checkout'),
        ('remaining_balance', 'Remaining Balance'),
    )
    STATUS_CHOICES = (
        ('prepared', 'Prepared'),
        ('invoice_created', 'Invoice Created'),
        ('pending', 'Pending'),
        ('succeeded', 'Succeeded'),
        ('requires_review', 'Requires Review'),
        ('failed', 'Failed'),
        ('expired', 'Expired'),
    )

    attempt_reference = models.CharField(max_length=40, unique=True, db_index=True)
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='checkout_payment_attempts',
    )
    checkout = models.ForeignKey(
        CheckoutSession,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='payment_attempts',
    )
    remaining_session = models.ForeignKey(
        RemainingPaymentSession,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='payment_attempts',
    )
    purpose = models.CharField(max_length=30, choices=PURPOSE_CHOICES)
    provider = models.CharField(max_length=30, default='myfatoorah')
    payment_option = models.CharField(max_length=30)
    expected_amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='SAR')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='prepared',
        db_index=True,
    )
    client_idempotency_key = models.CharField(max_length=100, null=True, blank=True)
    invoice_id = models.CharField(max_length=100, null=True, blank=True, unique=True)
    payment_id = models.CharField(max_length=150, null=True, blank=True, unique=True)
    gateway_status = models.CharField(max_length=50, null=True, blank=True)
    gateway_payment_method = models.CharField(max_length=100, null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.CharField(max_length=255, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    expires_at = models.DateTimeField(db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['checkout', 'status']),
            models.Index(fields=['remaining_session', 'status']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    (Q(checkout__isnull=False) & Q(remaining_session__isnull=True))
                    | (Q(checkout__isnull=True) & Q(remaining_session__isnull=False))
                ),
                name='payment_attempt_has_one_parent',
            ),
            models.UniqueConstraint(
                fields=['customer', 'client_idempotency_key'],
                condition=Q(client_idempotency_key__isnull=False),
                name='unique_customer_payment_attempt_idempotency',
            ),
        ]

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"{self.attempt_reference} - {self.status}"


class MyFatoorahWebhookEvent(BaseModel):
    """Minimal webhook receipt used for deduplication and retry tracking."""

    event_reference = models.CharField(max_length=100, unique=True, db_index=True)
    event_name = models.CharField(max_length=100)
    invoice_id = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    payment_id = models.CharField(max_length=150, null=True, blank=True, db_index=True)
    transaction_status = models.CharField(max_length=50, null=True, blank=True)
    attempts = models.PositiveIntegerField(default=0)
    processed_at = models.DateTimeField(null=True, blank=True)
    last_error = models.CharField(max_length=255, null=True, blank=True)


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
        ordering=['-created_at']
        verbose_name='Order Status History'
        verbose_name_plural='Order Status Histories'

    def __str__(self):
        return f"{self.order.order_number} - {self.status} (changed by {self.changed_by.username})"


# ============================================================================
# FSM SIGNAL HANDLERS FOR AUTOMATIC NOTIFICATIONS
# ============================================================================

@receiver(post_transition, sender=Order)
def send_notification_on_status_transition(sender, instance, name, source, target, **kwargs):
    """
    Automatically send notifications when order status transitions occur.
    This fixes the bug where old_status and new_status were the same.
    
    Args:
        sender: Order model class
        instance: The order instance
        name: Name of the transition method (e.g., 'rider_accept_order')
        source: Previous status value
        target: New status value
        **kwargs: Additional arguments including method_kwargs
    """
    from apps.notifications.services import NotificationService
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Get the user who made the change from method arguments
    method_kwargs = kwargs.get('method_kwargs', {})
    user = method_kwargs.get('user')
    
    try:
        from apps.notifications.tasks import (
            send_rider_status_notification_task,
            send_tailor_status_notification_task
        )
        
        user_id = user.id if user and hasattr(user, 'id') else None

        # Determine which field changed based on transition method name
        if name.startswith('rider_'):
            send_rider_status_notification_task.delay(
                order_id=instance.id,
                old_status=source,
                new_status=target,
                user_id=user_id
            )
            logger.info(f"Queued rider status notification task: {source} → {target} for order {instance.order_number}")
            
        elif name.startswith('tailor_'):
            send_tailor_status_notification_task.delay(
                order_id=instance.id,
                old_status=source,
                new_status=target,
                user_id=user_id
            )
            logger.info(f"Queued tailor status notification task: {source} → {target} for order {instance.order_number}")
            
    except Exception as e:
        # Log error but don't fail the transition
        logger.error(f"Failed to send notification for {name}: {str(e)}")
