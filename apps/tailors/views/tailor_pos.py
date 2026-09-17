from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from django.contrib.auth import get_user_model
from django.db.models import Count, Max

from apps.tailors.serializers.tailor_pos import (
    TailorCustomerSerializer,
    CreateCustomerSerializer,
)
from apps.customers.models import CustomerProfile, TailorPOSCustomerLink
from apps.orders.models import Order
from apps.orders.serializers import OrderListSerializer, OrderSerializer
from apps.tailors.services.pos_customer_access import (
    ensure_pos_customer_link,
    pos_owned_by_tailor,
    tailor_has_pos_access_to_customer,
)
from apps.tailors.services.pos_customer_styles import get_customer_order_styles, get_customer_style_presets
from zthob.utils import api_response

User = get_user_model()


from apps.tailors.permissions import IsShopStaff
from .base import BaseTailorAPIView


def _pos_list_measurements(owner_user, customer_profile):
    if pos_owned_by_tailor(tailor_owner_user=owner_user, profile=customer_profile):
        return customer_profile.measurements
    return None


def _pos_list_presets(owner_user, customer_profile, presets):
    if pos_owned_by_tailor(tailor_owner_user=owner_user, profile=customer_profile):
        return presets
    return []


class TailorCustomerListView(BaseTailorAPIView):
    """
    GET /api/tailors/pos/customers/
    Returns all unique customers who have:
      1. Previously ordered from this tailor shop, OR
      2. Were created via this tailor shop's POS, OR
      3. Were added to this shop via POS (reused existing account).
    """
    permission_classes = [IsAuthenticated, IsShopStaff]
    required_employee_permission = 'can_manage_pos'


    def get(self, request):
        shop_profile = self.get_tailor_profile(request.user)
        if not shop_profile:
             return api_response(success=False, message="Shop profile not found", status_code=404)
        
        owner_user = shop_profile.shop_owner_user
        
        # --- Source 1: Customers who placed orders with this shop ---
        order_customer_data = (
            Order.objects.filter(tailor=owner_user, shop=shop_profile)

            .values('customer')
            .annotate(
                total_orders=Count('id'),
                last_order_date=Max('created_at'),
            )
        )
        # Build a dict keyed by customer user ID
        order_map = {
            entry['customer']: {
                'total_orders': entry['total_orders'],
                'last_order_date': entry['last_order_date'],
            }
            for entry in order_customer_data
        }

        created_user_ids = set(
            CustomerProfile.objects.filter(
                pos_created_by=owner_user,
            ).values_list('user_id', flat=True)
        )
        linked_user_ids = set(
            TailorPOSCustomerLink.objects.filter(
                tailor=owner_user,
            ).values_list('customer_id', flat=True)
        )

        all_user_ids = set(order_map.keys()) | created_user_ids | linked_user_ids

        users = User.objects.filter(id__in=all_user_ids).in_bulk()
        profiles = {
            cp.user_id: cp
            for cp in CustomerProfile.objects.filter(user_id__in=all_user_ids)
        }

        styles_map = get_customer_order_styles(owner_user, all_user_ids, request)
        presets_map = get_customer_style_presets(all_user_ids, request)

        results = []

        for user_id in all_user_ids:
            user = users.get(user_id)
            if not user:
                continue
            customer_profile = profiles.get(user_id)
            stats = order_map.get(user_id)
            results.append({
                'id': user.id,
                'name': user.get_full_name() or user.username,
                'phone': user.phone or '',
                'email': user.email,
                'total_orders': stats['total_orders'] if stats else 0,
                'last_order_date': stats['last_order_date'] if stats else None,
                'measurements': _pos_list_measurements(owner_user, customer_profile),
                'order_styles': styles_map.get(user_id, []),
                'style_presets': _pos_list_presets(
                    owner_user,
                    customer_profile,
                    presets_map.get(user_id, []),
                ),
            })

        # Sort: customers with orders first (by last_order_date), then zero-order at the end
        results.sort(
            key=lambda x: (x['last_order_date'] is None, x['last_order_date'] or ''),
            reverse=True
        )

        serializer = TailorCustomerSerializer(results, many=True)
        return api_response(
            success=True,
            message="Customers retrieved successfully",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )


class TailorCreateCustomerView(BaseTailorAPIView):
    """
    POST /api/tailors/pos/customers/create/
    Creates a new customer account (User + CustomerProfile) and tags it with this tailor shop.
    If the phone already belongs to a customer, reuses that account and links this shop.
    """
    permission_classes = [IsAuthenticated, IsShopStaff]
    required_employee_permission = 'can_manage_pos'


    def post(self, request):
        shop_profile = self.get_tailor_profile(request.user)
        if not shop_profile:
             return api_response(success=False, message="Shop profile not found", status_code=404)
        owner_user = shop_profile.shop_owner_user

        serializer = CreateCustomerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from apps.customers.services.customer_provisioning import (
            NonCustomerPhoneError,
            lookup_or_create_customer,
            normalize_customer_phone,
        )

        phone = normalize_customer_phone(serializer.validated_data['phone'])
        name = serializer.validated_data['name']

        try:
            result = lookup_or_create_customer(
                phone=phone,
                name=name,
                pos_created_by=owner_user,
                update_name=False,
                claim_pos_created_by_if_empty=False,
                require_customer_role=True,
            )
        except NonCustomerPhoneError as exc:
            return api_response(
                success=False,
                message=str(exc),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        already_in_shop = tailor_has_pos_access_to_customer(
            tailor_owner_user=owner_user,
            customer_user=result.user,
        )
        ensure_pos_customer_link(
            tailor_owner_user=owner_user,
            customer_user=result.user,
        )

        customer_name = result.user.get_full_name() or result.user.username
        shop_order_count = Order.objects.filter(
            customer=result.user, tailor=owner_user, shop=shop_profile
        ).count()
        owned_measurements = (
            result.profile.measurements
            if pos_owned_by_tailor(tailor_owner_user=owner_user, profile=result.profile)
            else None
        )

        if result.created:
            return api_response(
                success=True,
                message="Customer created successfully",
                data={
                    'id': result.user.id,
                    'name': customer_name,
                    'phone': result.user.phone,
                    'email': result.user.email,
                    'total_orders': 0,
                    'last_order_date': None,
                    'measurements': None,
                    'is_existing': False,
                },
                status_code=status.HTTP_201_CREATED,
            )

        if already_in_shop:
            return api_response(
                success=True,
                message="Customer already exists",
                data={
                    'id': result.user.id,
                    'name': customer_name,
                    'phone': result.user.phone,
                    'email': result.user.email,
                    'total_orders': shop_order_count,
                    'last_order_date': None,
                    'measurements': owned_measurements,
                    'is_existing': True,
                },
                status_code=status.HTTP_200_OK,
            )

        return api_response(
            success=True,
            message="Customer created successfully",
            data={
                'id': result.user.id,
                'name': customer_name,
                'phone': result.user.phone,
                'email': result.user.email,
                'total_orders': 0,
                'last_order_date': None,
                'measurements': None,
                'is_existing': False,
            },
            status_code=status.HTTP_201_CREATED,
        )


class TailorPOSCustomerOrdersView(BaseTailorAPIView):
    """
    GET /api/tailors/pos/customers/{customer_id}/orders/
    Returns orders for a selected POS customer, scoped to this tailor shop only.
    """
    permission_classes = [IsAuthenticated, IsShopStaff]
    required_employee_permission = 'can_manage_pos'

    def get(self, request, customer_id):
        profile = self.get_tailor_profile(request.user)
        if not profile:
            return api_response(success=False, message="Shop profile not found", status_code=404)

        orders = (
            Order.objects.filter(
                customer_id=customer_id,
                tailor=profile.shop_owner_user,
                shop=profile,
            )
            .select_related('customer', 'tailor', 'delivery_address', 'rider')
            .prefetch_related('order_items__fabric', 'order_items__customer_fabric_images')
            .order_by('-created_at')
        )

        status_filter = request.query_params.get('status')
        if status_filter:
            orders = orders.filter(status=status_filter)

        serializer = OrderListSerializer(
            orders,
            many=True,
            context={'request': request, 'role': 'TAILOR'},
        )
        return api_response(
            success=True,
            message="Customer orders retrieved successfully",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )


class TailorPOSCustomerOrderDetailView(BaseTailorAPIView):
    """
    GET /api/tailors/pos/customers/{customer_id}/orders/{order_id}/
    Returns one selected POS customer order, scoped to this tailor shop only.
    """
    permission_classes = [IsAuthenticated, IsShopStaff]
    required_employee_permission = 'can_manage_pos'

    def get(self, request, customer_id, order_id):
        profile = self.get_tailor_profile(request.user)
        if not profile:
            return api_response(success=False, message="Shop profile not found", status_code=404)

        try:
            order = (
                Order.objects.select_related(
                    'customer',
                    'tailor',
                    'delivery_address',
                    'rider',
                    'family_member',
                )
                .prefetch_related('order_items__fabric', 'order_items__customer_fabric_images', 'status_history')
                .get(
                    id=order_id,
                    customer_id=customer_id,
                    tailor=profile.shop_owner_user,
                    shop=profile,
                )
            )
        except Order.DoesNotExist:
            return api_response(
                success=False,
                message="Order not found for this customer",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        serializer = OrderSerializer(order, context={'request': request, 'role': 'TAILOR'})
        return api_response(
            success=True,
            message="Customer order details retrieved successfully",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )
