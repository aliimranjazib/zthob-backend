# apps/orders/actions.py
from abc import ABC, abstractmethod
from rest_framework.exceptions import ValidationError, PermissionDenied
from django.utils import timezone
from django.db.models import Q
from apps.customers.models import FamilyMember
from apps.orders.payments import money
from zthob.translations import get_language_from_request, translate_message

class BaseOrderAction(ABC):
    """
    Base class for all Order Actions.
    Each action defines its own permissions, requirements, and execution logic.
    """
    key = None  # Unique identifier for the action
    label = None  # Human-readable label
    allowed_roles = []  # Roles allowed to perform this action

    def __init__(self, order, user, data=None, requested_role=None, request=None):
        self.order = order
        self.user = user
        self.data = data or {}
        self.requested_role = requested_role
        self.request = request
        
        # Capture state before execution for notification logic
        self._old_status = order.status
        self._old_tailor_status = order.tailor_status
        self._old_rider_status = order.rider_status

    def validate(self):
        # 1. Check Role Permission (Multi-role support)
        has_permission = False
        
        if not self.allowed_roles:
            has_permission = True
        else:
            for role in self.allowed_roles:
                if role == 'USER' and self.user.is_customer: has_permission = True
                elif role == 'TAILOR' and self.user.is_tailor: has_permission = True
                elif role == 'RIDER' and self.user.is_rider: has_permission = True
                elif role == 'ADMIN' and self.user.is_admin: has_permission = True
                
                if has_permission: break
        
        if not has_permission:
            raise PermissionDenied("You do not have the required role to perform this action.")

        # 2. Check Custom Requirements
        self._check_requirements()

    @abstractmethod
    def _check_requirements(self):
        pass

    @abstractmethod
    def execute(self):
        pass

    def post_execute(self):
        """Send notifications ONLY for statuses that actually changed"""
        from apps.notifications.services import NotificationService
        
        # 1. Order Status changed?
        if self.order.status != self._old_status:
            NotificationService.send_order_status_notification(
                self.order, self._old_status, self.order.status, self.user
            )
            
        # 2. Tailor Status changed?
        if self.order.tailor_status != self._old_tailor_status:
            NotificationService.send_tailor_status_notification(
                self.order, self._old_tailor_status, self.order.tailor_status, self.user
            )
            
        # 3. Rider Status changed?
        if self.order.rider_status != self._old_rider_status:
            NotificationService.send_rider_status_notification(
                self.order, self._old_rider_status, self.order.rider_status, self.user
            )

    def get_available_action_data(self):
        language = get_language_from_request(self.request) if self.request else 'en'
        return {
            'key': self.key,
            'label': translate_message(self.label, language),
            'role': self.requested_role or (self.allowed_roles[0] if self.allowed_roles else 'USER')
        }


class CancelOrderAction(BaseOrderAction):
    key = 'cancel_order'
    label = 'Cancel Order'
    allowed_roles = ['USER', 'ADMIN']

    def _check_requirements(self):
        if self.order.status != 'pending':
            raise ValidationError(f"Only pending orders can be cancelled. Current status: {self.order.status}")
        if not self.user.is_admin and self.order.customer != self.user:
            raise PermissionDenied("You can only cancel your own orders.")

    def execute(self):
        self.order.status = 'cancelled'
        self.order.save()
        return "Order cancelled successfully."


class AcceptOrderAction(BaseOrderAction):
    key = 'accept_order'
    label = 'Accept Order'
    allowed_roles = ['TAILOR', 'RIDER']

    def _is_payment_ready(self):
        return self.order.payment_status in ['paid', 'partially_paid'] or (
            self.order.payment_method == 'cod' and self.order.payment_status == 'pending'
        )

    def _check_requirements(self):
        # 1. Role Check (with auto-detection)
        role = self.requested_role
        user_roles = self.user.get_all_roles()

        if not role:
            # If no role requested, try to infer it from user properties
            if self.user.is_tailor:
                role = 'TAILOR'
            elif self.user.is_rider:
                role = 'RIDER'
        
        if role == 'TAILOR':
            if not self._is_payment_ready():
                raise ValidationError("Order payment must be paid or pending COD before tailor can accept it.")
            if self.order.tailor and self.order.tailor != self.user:
                raise PermissionDenied("This order is already assigned to another tailor.")
            if self.order.tailor_status != 'none':
                raise ValidationError("Order is already accepted by a tailor.")
        
        elif role == 'RIDER':
            if not self._is_payment_ready():
                raise ValidationError("Order payment must be paid or pending COD before rider can accept it.")
            if self.order.rider and self.order.rider != self.user:
                raise PermissionDenied("This order is already assigned to another rider.")
            if self.order.rider_status != 'none':
                raise ValidationError("Order is already accepted by a rider.")
        else:
             raise PermissionDenied(f"Invalid role '{role}' or missing role for this action.")

    def execute(self):
        # Infer role if not provided
        role = self.requested_role
        user_roles = self.user.get_all_roles()
        if not role:
            if self.user.is_tailor: role = 'TAILOR'
            elif self.user.is_rider: role = 'RIDER'
        
        if role == 'TAILOR':
            # Assign the tailor if not already assigned
            if not self.order.tailor:
                self.order.tailor = self.user
            
            self.order.tailor_status = 'accepted'
            if self.order.status == 'pending':
                self.order.status = 'confirmed'
            
            # Optional: Assign a specific rider during acceptance
            assigned_rider_id = self.data.get('assigned_rider_id')
            if assigned_rider_id:
                from apps.accounts.models import CustomUser
                try:
                    assigned_rider = CustomUser.objects.get(id=assigned_rider_id, role='RIDER')
                    self.order.assigned_rider = assigned_rider
                    self.order.rider = assigned_rider
                except CustomUser.DoesNotExist:
                    pass
        
        elif role == 'RIDER':
            if not self.order.rider:
                self.order.rider = self.user
            if self.order.order_type == 'measurement_service':
                self.order.status = 'confirmed'
                
            if self.order.all_items_have_measurements:
                self.order.rider_status = 'measurement_taken'
            else:
                self.order.rider_status = 'accepted'
        
        self.order.save()
        return f"Order accepted successfully as {role}."


class StartMeasuringAction(BaseOrderAction):
    key = 'start_measuring'
    label = 'Start Measuring'
    allowed_roles = ['RIDER']

    def _check_requirements(self):
        if self.order.all_items_have_measurements:
            raise ValidationError("Measurements are already recorded.")
        if self.order.rider != self.user and self.order.assigned_rider != self.user:
            raise PermissionDenied("You are not the assigned rider for this order.")
        if self.order.rider_status != 'accepted':
            raise ValidationError("You must accept the order before starting measurement.")

    def execute(self):
        self.order.rider_status = 'on_way_to_measurement'
        self.order.status = 'in_progress'
        self.order.save()
        return "You are now on your way to take measurements."


class RecordMeasurementsAction(BaseOrderAction):
    key = 'record_measurements'
    label = 'Record Measurements'
    allowed_roles = ['TAILOR', 'RIDER', 'ADMIN']

    def _resolve_role(self):
        """Resolve role from requested role or authenticated user roles."""
        if self.requested_role:
            return self.requested_role
        if self.user.is_admin:
            return 'ADMIN'
        if self.user.is_tailor:
            return 'TAILOR'
        if self.user.is_rider:
            return 'RIDER'
        return None

    def _check_requirements(self):
        # 1. State check
        if self.order.status in ['delivered', 'collected', 'cancelled']:
            raise ValidationError("Cannot record measurements for a finalized order.")

        # 2. Measurement check (apply to all roles)
        if self.order.all_items_have_measurements:
            raise ValidationError("Measurements are already recorded.")

        # 3. Role-specific logic
        role = self._resolve_role()
        if role not in ['TAILOR', 'RIDER', 'ADMIN']:
            raise PermissionDenied("Invalid role for recording measurements.")

        family_member_id = self.data.get('family_member')
        if family_member_id is not None:
            try:
                family_member = FamilyMember.objects.get(id=family_member_id)
            except FamilyMember.DoesNotExist:
                raise ValidationError("Family member not found.")
            if family_member.user_id != self.order.customer_id:
                raise ValidationError("Family member must belong to the order customer.")
        
        if role == 'TAILOR':
            if self.order.tailor != self.user and not self.user.is_admin:
                raise PermissionDenied("You are not the assigned tailor for this order.")
            if self.order.service_mode == 'home_delivery':
                raise ValidationError("Rider must record measurements for home delivery orders.")
        
        elif role == 'RIDER':
            if self.order.rider != self.user and self.order.assigned_rider != self.user:
                raise PermissionDenied("You are not the assigned rider for this order.")
            if self.order.rider_status not in ['on_way_to_measurement', 'accepted', 'measuring']:
                raise ValidationError("Invalid state to record measurements.")

    def execute(self):
        measurements = self.data.get('measurements')
        if not measurements:
            raise ValidationError("Measurement data is required.")
        family_member_id = self.data.get('family_member')

        # Update only selected recipient items (family member OR customer/self).
        if family_member_id is not None:
            recipient_items = self.order.order_items.filter(family_member_id=family_member_id)
        else:
            recipient_items = self.order.order_items.filter(family_member__isnull=True)

        if not recipient_items.exists():
            raise ValidationError("No order items found for the selected recipient.")

        recipient_items.update(measurements=measurements)

        self.order.measurement_taken_at = timezone.now()
        self.order.status = 'in_progress'

        role = self._resolve_role()

        if self.order.all_items_have_measurements:
            if role in ['RIDER', 'ADMIN']:
                self.order.rider_status = 'measurement_taken'
        elif role == 'RIDER' and self.order.rider_status in ['accepted', 'on_way_to_measurement', 'measuring']:
            self.order.rider_status = 'measuring'
        elif role == 'TAILOR':
            self.order.tailor_status = 'accepted'
            
        self.order.save()
        return "Measurements recorded successfully."


class StartStitchingAction(BaseOrderAction):
    key = 'start_stitching'
    label = 'Start Stitching'
    allowed_roles = ['TAILOR']

    def _check_requirements(self):
        if not self.order.all_items_have_measurements:
            raise ValidationError("Cannot start stitching. Measurements are missing.")
        
        if self.order.tailor_status not in ['accepted', 'in_progress']:
            raise ValidationError(f"Invalid tailor status: {self.order.tailor_status}")

    def execute(self):
        self.order.tailor_status = 'stitching_started'
        self.order.status = 'in_progress'
        
        # Optional: Save expected completion date/time
        date = self.data.get('stitching_completion_date')
        time = self.data.get('stitching_completion_time')
        if date:
            self.order.stitching_completion_date = date
        if time:
            self.order.stitching_completion_time = time
            
        self.order.save()
        return "Stitching has started."


class FinishStitchingAction(BaseOrderAction):
    key = 'finish_stitching'
    label = 'Finish Stitching'
    allowed_roles = ['TAILOR']

    def _check_requirements(self):
        if self.order.tailor_status != 'stitching_started':
            raise ValidationError(f"Cannot finish stitching. Current status: {self.order.tailor_status}")

    def execute(self):
        self.order.tailor_status = 'stitched'
        self.order.save()
        return "Stitching completed successfully."


class MarkReadyAction(BaseOrderAction):
    key = 'mark_ready'
    label = 'Mark Ready'
    allowed_roles = ['TAILOR']

    def _check_requirements(self):
        if self.order.tailor_status != 'stitched':
            raise ValidationError("You must finish stitching before marking the order as ready.")
        if self.order.status in ['ready_for_delivery', 'ready_for_pickup', 'delivered', 'collected', 'cancelled']:
            raise ValidationError("Order is already ready or finalized.")

    def execute(self):
        if self.order.service_mode == 'walk_in':
            self.order.status = 'ready_for_pickup'
        else:
            self.order.status = 'ready_for_delivery'
        
        self.order.save()
        return "Order is now ready for the next step."


class PickupOrderAction(BaseOrderAction):
    key = 'pickup_order'
    label = 'Pickup Order'
    allowed_roles = ['RIDER']

    def _check_requirements(self):
        if self.order.status != 'ready_for_delivery':
            raise ValidationError("Order is not ready for delivery.")
        if self.order.rider != self.user and self.order.assigned_rider != self.user:
            raise PermissionDenied("You are not the assigned rider for this order.")
        
        # HIDE if already picked up or in delivery
        if self.order.rider_status in ['picked_up', 'on_way_to_delivery', 'delivered']:
            raise ValidationError("Order is already picked up or in delivery.")

    def execute(self):
        self.order.rider_status = 'picked_up'
        self.order.save()
        return "Order picked up from tailor."


class StartDeliveryAction(BaseOrderAction):
    key = 'start_delivery'
    label = 'Start Delivery'
    allowed_roles = ['RIDER']

    def _check_requirements(self):
        if self.order.rider_status != 'picked_up':
            raise ValidationError("You must pickup the order before starting delivery.")
        if self.order.rider != self.user and self.order.assigned_rider != self.user:
            raise PermissionDenied("You are not the assigned rider for this order.")

    def execute(self):
        self.order.rider_status = 'on_way_to_delivery'
        self.order.save()
        return "You are now on your way to the customer."


class MarkDeliveredAction(BaseOrderAction):
    key = 'mark_delivered'
    label = 'Mark Delivered'
    allowed_roles = ['RIDER']

    def _check_requirements(self):
        if self.order.rider_status != 'on_way_to_delivery':
            raise ValidationError("Invalid state for delivery.")
        if self.order.rider != self.user and self.order.assigned_rider != self.user:
            raise PermissionDenied("You are not the assigned rider for this order.")
        if self.order.has_remaining_balance:
            raise ValidationError("Remaining payment must be collected before marking the order as delivered.")

    def execute(self):
        self.order.rider_status = 'delivered'
        self.order.status = 'delivered'
        self.order.actual_delivery_date = timezone.now().date()
        self.order.save()
        return "Order delivered successfully."


class CollectOrderAction(BaseOrderAction):
    key = 'collect_order'
    label = 'Collect Order'
    allowed_roles = ['USER', 'TAILOR', 'ADMIN']

    def _check_requirements(self):
        # 1. State check
        if self.order.status != 'ready_for_pickup':
            raise ValidationError("Order is not ready for pickup.")
        if self.order.has_remaining_balance:
            raise ValidationError("Remaining payment must be collected before marking the order as collected.")
        
        # 2. Permission check
        if self.user.is_admin or self.user.is_tailor:
            # Admins and the assigned Tailor can always mark as collected
            if self.user.is_tailor and self.order.tailor != self.user:
                raise PermissionDenied("Only the assigned tailor can mark this order as collected.")
            return
        
        # Customers can only mark their own orders as collected
        if self.order.customer != self.user:
            raise PermissionDenied("Only the customer or assigned tailor can mark the order as collected.")

    def execute(self):
        self.order.status = 'collected'
        self.order.save()
        return "Order marked as collected successfully."


class CollectCashPaymentAction(BaseOrderAction):
    key = 'collect_cash_payment'
    label = 'Collect Remaining Payment'
    allowed_roles = ['RIDER', 'TAILOR', 'ADMIN']

    def _resolve_role(self):
        if self.requested_role:
            return self.requested_role
        if self.user.is_admin:
            return 'ADMIN'
        if self.user.is_rider:
            return 'RIDER'
        if self.user.is_tailor:
            return 'TAILOR'
        return None

    def _check_requirements(self):
        if not self.order.has_remaining_balance:
            raise ValidationError("Payment has already been collected in full.")
        if self.order.payment_status == 'refunded':
            raise ValidationError("Cannot collect cash for a refunded order.")
        if self.order.status in ['cancelled']:
            raise ValidationError("Cannot collect cash for a cancelled order.")

        role = self._resolve_role()
        if role == 'ADMIN':
            return

        if self.order.service_mode == 'home_delivery':
            if role != 'RIDER':
                raise PermissionDenied("Only the assigned rider can collect cash for home delivery orders.")
            if self.order.rider != self.user and self.order.assigned_rider != self.user:
                raise PermissionDenied("You are not the assigned rider for this order.")
            if self.order.rider_status not in ['on_way_to_delivery', 'delivered']:
                raise ValidationError("Cash can be collected when the rider is delivering the order.")
            return

        if self.order.service_mode == 'walk_in':
            if role != 'TAILOR':
                raise PermissionDenied("Only the assigned tailor can collect cash for walk-in orders.")
            if self.order.tailor != self.user:
                raise PermissionDenied("You are not the assigned tailor for this order.")
            if self.order.status not in ['ready_for_pickup', 'collected']:
                raise ValidationError("Cash can be collected when the walk-in order is ready for pickup.")
            return

        raise ValidationError("Unsupported service mode for cash collection.")

    def execute(self):
        old_payment_status = self.order.payment_status
        amount = money(self.order.remaining_amount)
        payment_method = self.data.get('payment_method') or 'cod'
        payment_reference = self.data.get('payment_reference') or None
        notes = self.data.get('notes') or 'Remaining payment collected.'

        from apps.orders.models import OrderPayment, OrderStatusHistory

        if payment_method == 'credit_card' and not payment_reference:
            raise ValidationError("payment_reference is required for credit card collection.")
        if payment_method not in ['cod', 'credit_card', 'bank_transfer']:
            raise ValidationError("Invalid payment_method for collection.")

        if payment_reference and OrderPayment.objects.filter(payment_reference=payment_reference).exists():
            raise ValidationError("This payment reference has already been used.")

        OrderPayment.objects.create(
            order=self.order,
            amount=amount,
            payment_method=payment_method,
            payment_type='remaining_balance' if old_payment_status == 'partially_paid' else 'full_payment',
            status='paid',
            payment_reference=payment_reference,
            collected_by=self.user,
            notes=notes,
            metadata={'previous_payment_status': old_payment_status},
        )

        self.order.apply_payment_summary(self.order.paid_amount + amount, save=True)

        OrderStatusHistory.objects.create(
            order=self.order,
            status=self.order.status,
            previous_status=self.order.status,
            changed_by=self.user,
            notes=(
                f"Payment collected ({amount}). "
                f"Payment status changed from {old_payment_status} to {self.order.payment_status}."
            )
        )

        return "Payment collected successfully."

    def get_available_action_data(self):
        data = super().get_available_action_data()
        data['amount_due'] = str(self.order.remaining_amount)
        data['payment_status'] = self.order.payment_status
        return data


class OrderActionManager:
    """Registry for all available actions"""
    _actions = {
        'cancel_order': CancelOrderAction,
        'accept_order': AcceptOrderAction,
        'start_measuring': StartMeasuringAction,
        'record_measurements': RecordMeasurementsAction,
        'start_stitching': StartStitchingAction,
        'finish_stitching': FinishStitchingAction,
        'mark_ready': MarkReadyAction,
        'pickup_order': PickupOrderAction,
        'start_delivery': StartDeliveryAction,
        'mark_delivered': MarkDeliveredAction,
        'collect_order': CollectOrderAction,
        'collect_cash_payment': CollectCashPaymentAction,
    }

    @classmethod
    def get_action(cls, action_key, order, user, data=None, requested_role=None, request=None):
        action_class = cls._actions.get(action_key)
        if not action_class:
            raise ValidationError(f"Action '{action_key}' is not recognized.")
        return action_class(order, user, data, requested_role=requested_role, request=request)

    @classmethod
    def get_available_actions(cls, order, user, requested_role=None, request=None):
        available = []
        for action_class in cls._actions.values():
            # If a specific role is requested, only check actions allowed for that role
            if requested_role and requested_role not in action_class.allowed_roles:
                continue
                
            action = action_class(order, user, requested_role=requested_role, request=request)
            try:
                action.validate()
                available.append(action.get_available_action_data())
            except (ValidationError, PermissionDenied):
                continue
        return available
