# apps/orders/actions.py
from abc import ABC, abstractmethod
from rest_framework.exceptions import ValidationError, PermissionDenied
from django.utils import timezone
from django.db.models import Q

class BaseOrderAction(ABC):
    """
    Base class for all Order Actions.
    Each action defines its own permissions, requirements, and execution logic.
    """
    key = None  # Unique identifier for the action
    label = None  # Human-readable label
    allowed_roles = []  # Roles allowed to perform this action

    def __init__(self, order, user, data=None):
        self.order = order
        self.user = user
        self.data = data or {}

    def validate(self):
        # 1. Check Role Permission (Multi-role support)
        user_roles = self.user.get_all_roles()
        has_permission = False
        
        if not self.allowed_roles:
            has_permission = True
        else:
            for role in self.allowed_roles:
                if role in user_roles:
                    has_permission = True
                    break
        
        if not has_permission:
            raise PermissionDenied(f"None of your roles ({user_roles}) are allowed to perform this action.")

        # 2. Check Custom Requirements
        self._check_requirements()

    @abstractmethod
    def _check_requirements(self):
        pass

    @abstractmethod
    def execute(self):
        pass

    def post_execute(self):
        """Send notifications after successful execution"""
        from apps.notifications.services import NotificationService
        
        # Trigger automatic status notifications based on the new state
        # We use the existing service to ensure translations work
        NotificationService.send_order_status_notification(self.order, "", self.order.status, self.user)
        NotificationService.send_tailor_status_notification(self.order, "", self.order.tailor_status, self.user)
        NotificationService.send_rider_status_notification(self.order, "", self.order.rider_status, self.user)


class CancelOrderAction(BaseOrderAction):
    key = 'cancel_order'
    label = 'Cancel Order'
    allowed_roles = ['USER', 'ADMIN']

    def _check_requirements(self):
        if self.order.status != 'pending':
            raise ValidationError(f"Only pending orders can be cancelled. Current status: {self.order.status}")
        if 'ADMIN' not in self.user.get_all_roles() and self.order.customer != self.user:
            raise PermissionDenied("You can only cancel your own orders.")

    def execute(self):
        self.order.status = 'cancelled'
        self.order.save()
        return "Order cancelled successfully."


class AcceptOrderAction(BaseOrderAction):
    key = 'accept_order'
    label = 'Accept Order'
    allowed_roles = ['TAILOR', 'RIDER']

    def _check_requirements(self):
        user_roles = self.user.get_all_roles()
        
        if 'TAILOR' in user_roles and self.order.tailor == self.user:
            if self.order.tailor_status != 'none':
                raise ValidationError("Order is already accepted by you.")
        elif 'RIDER' in user_roles:
            if self.order.rider_status != 'none':
                raise ValidationError("Order is already accepted by another rider.")
        else:
            raise PermissionDenied("You are not assigned to this order or don't have the required role.")

    def execute(self):
        user_roles = self.user.get_all_roles()
        
        if 'TAILOR' in user_roles and self.order.tailor == self.user:
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
                except CustomUser.DoesNotExist:
                    pass # Skip if invalid rider ID provided
        
        if 'RIDER' in user_roles:
            self.order.rider = self.user
            # Smart Check: If measurements already exist, skip to measurement_taken
            if self.order.all_items_have_measurements:
                self.order.rider_status = 'measurement_taken'
            else:
                self.order.rider_status = 'accepted'
        
        self.order.save()
        return "Order accepted successfully."


class StartMeasuringAction(BaseOrderAction):
    key = 'start_measuring'
    label = 'Start Measuring'
    allowed_roles = ['RIDER']

    def _check_requirements(self):
        if self.order.rider != self.user:
            raise PermissionDenied("You are not the assigned rider for this order.")
        if self.order.rider_status != 'accepted':
            raise ValidationError("You must accept the order before starting measurement.")

    def execute(self):
        self.order.rider_status = 'on_way_to_measurement'
        self.order.save()
        return "You are now on your way to take measurements."


class RecordMeasurementsAction(BaseOrderAction):
    key = 'record_measurements'
    label = 'Record Measurements'
    allowed_roles = ['TAILOR', 'RIDER', 'ADMIN']

    def _check_requirements(self):
        # 1. State check
        if self.order.status in ['delivered', 'collected', 'cancelled']:
            raise ValidationError("Cannot record measurements for a finalized order.")

        # 2. Sequential & Role Logic
        user_roles = self.user.get_all_roles()
        
        # Tailor Check
        if 'TAILOR' in user_roles and self.order.tailor == self.user:
            # Rule 1: Hide if already measured
            if self.order.all_items_have_measurements:
                raise ValidationError("Measurements are already recorded.")
            # Rule 2: Hide if it's Home Delivery (Rider's job)
            if self.order.service_mode == 'home_delivery':
                raise ValidationError("Rider must record measurements for home delivery orders.")
        
        # 3. Rider check
        if 'RIDER' in user_roles and self.order.rider == self.user:
            if self.order.rider_status not in ['on_way_to_measurement', 'accepted']:
                 raise ValidationError("Invalid state to record measurements.")

    def execute(self):
        measurements = self.data.get('measurements')
        if not measurements:
            raise ValidationError("Measurement data is required.")

        # Logic to save measurements to order items
        for item in self.order.order_items.all():
            item.measurements = measurements
            item.save()

        self.order.measurement_taken_at = timezone.now()
        
        user_roles = self.user.get_all_roles()
        if 'RIDER' in user_roles and self.order.rider == self.user:
            self.order.rider_status = 'measurement_taken'
        elif 'TAILOR' in user_roles and self.order.tailor == self.user:
            # For walk-in, tailor recording measurements completes the "measurement" phase
            self.order.tailor_status = 'accepted' 
            # In models.py _sync_main_status handles the rest
        
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
        if self.order.rider != self.user:
            raise PermissionDenied("You are not the assigned rider for this order.")

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

    def execute(self):
        self.order.rider_status = 'delivered'
        self.order.status = 'delivered'
        self.order.actual_delivery_date = timezone.now().date()
        self.order.save()
        return "Order delivered successfully."


class CollectOrderAction(BaseOrderAction):
    key = 'collect_order'
    label = 'Collect Order'
    allowed_roles = ['USER']

    def _check_requirements(self):
        if self.order.customer != self.user:
            raise PermissionDenied("Only the customer can mark the order as collected.")
        if self.order.status != 'ready_for_pickup':
            raise ValidationError("Order is not ready for pickup.")

    def execute(self):
        self.order.status = 'collected'
        self.order.save()
        return "Thank you for collecting your order!"


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
    }

    @classmethod
    def get_action(cls, action_key, order, user, data=None):
        action_class = cls._actions.get(action_key)
        if not action_class:
            raise ValidationError(f"Action '{action_key}' is not recognized.")
        return action_class(order, user, data)

    @classmethod
    def get_available_actions(cls, order, user):
        available = []
        for key, action_class in cls._actions.items():
            try:
                action = action_class(order, user)
                action.validate()
                available.append({
                    'key': action.key,
                    'label': action.label,
                    'role': action.allowed_roles[0] if action.allowed_roles else None
                })
            except (ValidationError, PermissionDenied):
                continue
        return available
