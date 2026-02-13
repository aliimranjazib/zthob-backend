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


class TailorCustomerListView(APIView):
    """
    GET /api/tailors/pos/customers/
    Returns all unique customers who have previously ordered from this tailor.
    """
    permission_classes = [IsAuthenticated, IsTailor]

    def get(self, request):
        # Get all distinct customers who have orders with this tailor
        customer_data = (
            Order.objects.filter(tailor=request.user)
            .values('customer')
            .annotate(
                total_orders=Count('id'),
                last_order_date=Max('created_at'),
            )
            .order_by('-last_order_date')
        )

        results = []
        for entry in customer_data:
            try:
                user = User.objects.get(id=entry['customer'])
            except User.DoesNotExist:
                continue

            # Get measurements from customer profile
            measurements = None
            try:
                profile = user.customer_profile
                measurements = profile.measurements
            except CustomerProfile.DoesNotExist:
                pass

            results.append({
                'id': user.id,
                'name': user.get_full_name() or user.username,
                'phone': user.phone or '',
                'email': user.email,
                'total_orders': entry['total_orders'],
                'last_order_date': entry['last_order_date'],
                'measurements': measurements,
            })

        serializer = TailorCustomerSerializer(results, many=True)
        return api_response(
            success=True,
            message="Customers retrieved successfully",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )


class TailorCreateCustomerView(APIView):
    """
    POST /api/tailors/pos/customers/create/
    Creates a new customer account (User + CustomerProfile).
    """
    permission_classes = [IsAuthenticated, IsTailor]

    def post(self, request):
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

            measurements = None
            try:
                measurements = existing_user.customer_profile.measurements
            except CustomerProfile.DoesNotExist:
                pass

            total_orders = Order.objects.filter(
                customer=existing_user, tailor=request.user
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

        # Create empty customer profile
        CustomerProfile.objects.create(user=user)

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
