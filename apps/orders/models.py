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
        ("none", "None"),                          # No tailor activity
        ("accepted", "Accepted Order"),           # Tailor accepted the order
        ("in_progress", "In Progress"),           # Tailor is working on the order
        ("stitching_started", "Started Stitching"), # Tailor started stitching (stitching only)
        ("stitched", "Finished Stitching"),       # Tailor finished stitching (stitching only)
        ("measurements_complete", "Measurements Complete"),  # Measurement service complete
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
    order_type=models.CharField(
        max_length=25,
        choices=ORDER_TYPE_CHOICES,
        default='fabric_with_stitching',
        help_text="Type of order - fabric only or fabric with stitching"
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
    status=models.CharField(
    max_length=20,
    choices=ORDER_STATUS_CHOICES,
    default="pending",
    help_text="Main status of the order"
    )
    
    rider_status=FSMField(
        max_length=30,
        choices=RIDER_STATUS_CHOICES,
        default="none",
        protected=False,  # Allow direct assignment for backward compatibility
        help_text="Current rider activity status"
    )
    
    tailor_status=FSMField(
        max_length=30,
        choices=TAILOR_STATUS_CHOICES,
        default="none",
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
    help_text="Total stitching price for order (only for fabric_with_stitching orders)"
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
            self.total_amount=self.subtotal+self.stitching_price+self.tax_amount+self.delivery_fee

        # Auto-sync main status based on rider_status and tailor_status
        # This preserves the existing auto-sync logic from OrderStatusTransitionService
        self._sync_main_status()

        super().save(*args, **kwargs)
    
    def _sync_main_status(self):
        """
        Automatically sync main status based on rider_status and tailor_status.
        This ensures the main status reflects the current state of the order.
        """
        # If collected (Walk-In final state)
        if self.status == 'collected':
            return

        # If delivered by rider, main status should be delivered
        if self.rider_status == 'delivered':
            self.status = 'delivered'
            return
        
        # If cancelled, keep cancelled
        if self.status == 'cancelled':
            return

        # NEW: For Walk-In flow
        if self.service_mode == 'walk_in':
            if self.status == 'pending':
                if self.tailor_status != 'none':
                    self.status = 'confirmed'
                else:
                    return
            elif self.status == 'confirmed' and self.tailor_status in ['in_progress', 'stitching_started']:
                 self.status = 'in_progress'
            elif self.tailor_status == 'stitched' and self.status != 'collected':
                self.status = 'ready_for_pickup'
            elif self.tailor_status == 'measurements_complete' and self.status != 'collected':
                # For measurement service walk-in orders - measurements are done, ready for pickup
                self.status = 'ready_for_pickup'
            return

        # For measurement_service flow (Home Delivery)
        if self.order_type == 'measurement_service':
            if self.service_mode == 'home_delivery':
                # Home delivery measurement: rider-driven flow (no tailor confirmation needed)
                if self.status == 'pending' and self.rider_status == 'accepted':
                    self.status = 'confirmed'
                elif self.status == 'confirmed' and self.rider_status in ['on_way_to_measurement', 'measuring']:
                    self.status = 'in_progress'
                elif self.rider_status == 'delivered':
                    self.status = 'delivered'
            # Walk-in measurement handled in walk_in flow above
            return

        # For fabric_only flow (Home Delivery)
        if self.order_type == 'fabric_only':
            if self.status == 'pending':
                if self.tailor_status != 'none':
                    self.status = 'confirmed'
                else:
                    return
            elif self.status == 'confirmed' and self.rider_status in ['accepted', 'on_way_to_pickup', 'picked_up', 'on_way_to_delivery']:
                self.status = 'in_progress'
            elif self.rider_status == 'picked_up' and self.status == 'in_progress':
                self.status = 'ready_for_delivery'
        
        # For fabric_with_stitching flow (Home Delivery)
        else:  # fabric_with_stitching
            if self.status == 'pending':
                if self.tailor_status != 'none':
                    self.status = 'confirmed'
                else:
                    return
            elif self.status == 'confirmed' and self.rider_status in ['accepted', 'on_way_to_measurement', 'measurement_taken']:
                self.status = 'in_progress'
            elif self.tailor_status == 'stitched' and self.rider_status in ['on_way_to_pickup', 'picked_up', 'on_way_to_delivery']:
                self.status = 'ready_for_delivery'

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
    
    @transition(field=rider_status, source='measurement_taken', target='on_way_to_pickup')
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
        self.total_amount = totals['total_amount']
        self.save(update_fields=['subtotal', 'stitching_price', 'tax_amount', 'delivery_fee', 'total_amount'])

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
        # For fabric_only orders, measurements not required
        if self.order_type == 'fabric_only':
            return True
        
        # For measurement_service and fabric_with_stitching, check measurements
        items_without_measurements = self.order_items.filter(
            Q(measurements__isnull=True) | Q(measurements={})
        )
        
        return items_without_measurements.count() == 0
    
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
        # Determine which field changed based on transition method name
        if name.startswith('rider_'):
            # Rider status transition - send rider status notification
            NotificationService.send_rider_status_notification(
                order=instance,
                old_rider_status=source,  # ✅ Correct old value from FSM
                new_rider_status=target,  # ✅ Correct new value from FSM
                changed_by=user
            )
            logger.info(f"Sent rider status notification: {source} → {target} for order {instance.order_number}")
            
        elif name.startswith('tailor_'):
            # Tailor status transition - send tailor status notification
            NotificationService.send_tailor_status_notification(
                order=instance,
                old_tailor_status=source,  # ✅ Correct old value from FSM
                new_tailor_status=target,  # ✅ Correct new value from FSM
                changed_by=user
            )
            logger.info(f"Sent tailor status notification: {source} → {target} for order {instance.order_number}")
            
    except Exception as e:
        # Log error but don't fail the transition
        logger.error(f"Failed to send notification for {name}: {str(e)}")
