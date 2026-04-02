from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.contrib.auth import get_user_model
from django.db.models import Count, Max

from apps.tailors.permissions import IsTailor
from apps.tailors.serializers.tailor_pos import (
    TailorCustomerSerializer,
    CreateCustomerSerializer,
)
from apps.customers.models import CustomerProfile
from apps.orders.models import Order
from zthob.utils import api_response

User = get_user_model()


from apps.tailors.permissions import IsShopStaff
from .base import BaseTailorAPIView

class TailorCustomerListView(BaseTailorAPIView):
    """
    GET /api/tailors/pos/customers/
    Returns all unique customers who have:
      1. Previously ordered from this tailor shop, OR
      2. Were created via this tailor shop's POS.
    """
    permission_classes = [IsAuthenticated, IsShopStaff]
    required_employee_permission = 'can_manage_pos'


    def get(self, request):
        profile = self.get_tailor_profile(request.user)
        if not profile:
             return api_response(success=False, message="Shop profile not found", status_code=404)
        
        owner_user = profile.user
        
        # --- Source 1: Customers who placed orders with this shop ---
        order_customer_data = (
            Order.objects.filter(tailor=owner_user)

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

        # --- Source 2: Customers created via this tailor's POS with no orders yet ---
        # Note: We filter by owner_user for consistency
        pos_profiles = CustomerProfile.objects.filter(
            pos_created_by=owner_user
        ).exclude(
            user_id__in=order_map.keys()  # skip those already in order_map
        ).select_related('user')


        # Collect all user IDs to fetch
        all_user_ids = set(order_map.keys()) | {p.user_id for p in pos_profiles}

        # Fetch all users in a single query
        users = User.objects.filter(id__in=all_user_ids).in_bulk()

        # Fetch all customer profiles in a single query
        profiles = {
            cp.user_id: cp
            for cp in CustomerProfile.objects.filter(user_id__in=all_user_ids)
        }

        results = []

        # Add order-based customers
        for user_id, stats in order_map.items():
            user = users.get(user_id)
            if not user:
                continue
            profile = profiles.get(user_id)
            results.append({
                'id': user.id,
                'name': user.get_full_name() or user.username,
                'phone': user.phone or '',
                'email': user.email,
                'total_orders': stats['total_orders'],
                'last_order_date': stats['last_order_date'],
                'measurements': profile.measurements if profile else None,
            })

        # Add POS-created, zero-order customers
        for profile in pos_profiles:
            user = profile.user
            if not user:
                continue
            results.append({
                'id': user.id,
                'name': user.get_full_name() or user.username,
                'phone': user.phone or '',
                'email': user.email,
                'total_orders': 0,
                'last_order_date': None,
                'measurements': profile.measurements,
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
    """
    permission_classes = [IsAuthenticated, IsShopStaff]
    required_employee_permission = 'can_manage_pos'


    def post(self, request):
        profile = self.get_tailor_profile(request.user)
        if not profile:
             return api_response(success=False, message="Shop profile not found", status_code=404)
        owner_user = profile.user

        serializer = CreateCustomerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data['phone']
        name = serializer.validated_data['name']

        # Check if user with this phone already exists
        # Handle format variations: +966511111113, 966511111113, 0511111113, 511111113
        phone_variations = [phone]
        stripped = phone.lstrip('+')
        if stripped not in phone_variations:
            phone_variations.append(stripped)
        if stripped.startswith('966'):
            local = '0' + stripped[3:]
            phone_variations.append(local)
            phone_variations.append(stripped[3:])  # without 0 prefix
        elif stripped.startswith('0'):
            intl = '966' + stripped[1:]
            phone_variations.append(intl)
            phone_variations.append('+' + intl)

        existing_user = User.objects.filter(phone__in=phone_variations).first()

        if existing_user:
            # Update name if provided
            name_parts = name.strip().split(' ', 1)
            existing_user.first_name = name_parts[0]
            existing_user.last_name = name_parts[1] if len(name_parts) > 1 else ''
            existing_user.save(update_fields=['first_name', 'last_name'])

            # Tag with this tailor if not already tagged
            try:
                cust_profile = existing_user.customer_profile
                if not cust_profile.pos_created_by:
                    cust_profile.pos_created_by = owner_user
                    cust_profile.save(update_fields=['pos_created_by'])
                measurements = cust_profile.measurements
            except CustomerProfile.DoesNotExist:
                cust_profile = CustomerProfile.objects.create(
                    user=existing_user,
                    pos_created_by=owner_user
                )
                measurements = None

            total_orders = Order.objects.filter(
                customer=existing_user, tailor=owner_user
            ).count()


            return api_response(
                success=True,
                message="Customer already exists",
                data={
                    'id': existing_user.id,
                    'name': existing_user.get_full_name() or existing_user.username,
                    'phone': existing_user.phone,
                    'email': existing_user.email,
                    'total_orders': total_orders,
                    'last_order_date': None,
                    'measurements': measurements,
                    'is_existing': True,
                },
                status_code=status.HTTP_200_OK,
            )

        # Split name into first + last
        name_parts = name.strip().split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        # Create user with phone as username
        user = User.objects.create(
            username=phone,
            phone=phone,
            first_name=first_name,
            last_name=last_name,
            role='USER',
            is_active=True,
        )

        # Create customer profile and tag it with the tailor shop owner
        CustomerProfile.objects.create(
            user=user,
            pos_created_by=owner_user,  # track which shop owns this customer
        )

        return api_response(
            success=True,
            message="Customer created successfully",
            data={
                'id': user.id,
                'name': user.get_full_name(),
                'phone': user.phone,
                'email': user.email,
                'total_orders': 0,
                'last_order_date': None,
                'measurements': None,
                'is_existing': False,
            },
            status_code=status.HTTP_201_CREATED,
        )
