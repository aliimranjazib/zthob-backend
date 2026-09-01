"""Rider customer field APIs — lookup/create, measurements, styles."""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from apps.customization.models import UserStylePreset
from apps.customization.preset_styles import enrich_preset_style
from apps.customization.serializers import UserStylePresetSerializer
from apps.customers.services.audit_log import log_customer_data_change
from apps.customers.services.customer_provisioning import lookup_or_create_customer
from apps.orders.measurement_utils import has_measurement_values, prepare_measurements_payload, public_measurements
from apps.tailors.services.pos_profile_write_policy import apply_customer_profile_measurements
from apps.riders.customer_field import (
    build_rider_customer_payload,
    get_customer_user_or_none,
    require_approved_rider,
)
from zthob.utils import api_response

from ..serializers import (
    RiderCustomerLookupSerializer,
    RiderCustomerMeasurementsSerializer,
    RiderCustomerStylePresetSerializer,
)


class RiderCustomerLookupOrCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=RiderCustomerLookupSerializer,
        summary='Lookup or create customer',
        description='Find customer by phone or create a new account with name and phone.',
        tags=['Rider Customers'],
    )
    def post(self, request):
        _, error_response = require_approved_rider(request)
        if error_response:
            return error_response

        serializer = RiderCustomerLookupSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(
                success=False,
                message='Validation failed',
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        result = lookup_or_create_customer(
            phone=serializer.validated_data['phone'],
            name=serializer.validated_data['name'],
            pos_created_by=None,
        )

        action = 'update' if result.is_existing else 'create'
        log_customer_data_change(
            customer=result.user,
            actor_user=request.user,
            actor_role=getattr(request.user, 'role', ''),
            entity_type='customer_profile',
            entity_id=result.profile.id,
            action=action,
            after={
                'name': result.user.get_full_name(),
                'phone': result.user.phone,
            },
            source='rider_app',
        )

        payload = build_rider_customer_payload(
            result.user,
            request,
            is_existing=result.is_existing,
        )

        if result.is_existing:
            return api_response(
                success=True,
                message='Customer already exists',
                data=payload,
                status_code=status.HTTP_200_OK,
            )

        return api_response(
            success=True,
            message='Customer created successfully',
            data=payload,
            status_code=status.HTTP_201_CREATED,
        )


class RiderCustomerDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='Get customer details',
        description='Return customer profile data with measurements and style presets.',
        tags=['Rider Customers'],
    )
    def get(self, request, customer_id):
        _, error_response = require_approved_rider(request)
        if error_response:
            return error_response

        customer = get_customer_user_or_none(customer_id)
        if not customer:
            return api_response(
                success=False,
                message='Customer not found',
                status_code=status.HTTP_404_NOT_FOUND,
            )

        payload = build_rider_customer_payload(customer, request)
        return api_response(
            success=True,
            message='Customer retrieved successfully',
            data=payload,
            status_code=status.HTTP_200_OK,
        )


class RiderCustomerMeasurementsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=RiderCustomerMeasurementsSerializer,
        summary='Save customer measurements',
        description='Save measurements to the customer profile from a rider field visit.',
        tags=['Rider Customers'],
    )
    def post(self, request, customer_id):
        _, error_response = require_approved_rider(request)
        if error_response:
            return error_response

        customer = get_customer_user_or_none(customer_id)
        if not customer:
            return api_response(
                success=False,
                message='Customer not found',
                status_code=status.HTTP_404_NOT_FOUND,
            )

        serializer = RiderCustomerMeasurementsSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(
                success=False,
                message='Validation failed',
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        profile = customer.customer_profile
        replace_existing = serializer.validated_data.get('replace_existing', False)
        if (
            has_measurement_values(profile.measurements)
            and not replace_existing
        ):
            return api_response(
                success=False,
                message='Customer already has measurements. Send replace_existing=true to overwrite.',
                data={
                    'customer_id': customer.id,
                    'existing_measurements': public_measurements(profile.measurements),
                },
                status_code=status.HTTP_409_CONFLICT,
            )

        measurements_data = prepare_measurements_payload(
            serializer.validated_data['measurements'],
            unit=serializer.validated_data.get('unit'),
            title=serializer.validated_data.get('title'),
            notes=serializer.validated_data.get('notes'),
        )

        updated, _message = apply_customer_profile_measurements(
            customer_profile=profile,
            measurements_data=measurements_data,
            actor_user=request.user,
            actor_role=getattr(request.user, 'role', ''),
            replace_profile_measurements=replace_existing,
            source='rider_app',
        )

        if not updated:
            return api_response(
                success=False,
                message='Customer profile measurements were not updated because existing data is protected.',
                data={
                    'customer_id': customer.id,
                    'existing_measurements': public_measurements(profile.measurements),
                },
                status_code=status.HTTP_409_CONFLICT,
            )

        profile.refresh_from_db()
        return api_response(
            success=True,
            message='Measurements saved successfully',
            data={
                'customer_id': customer.id,
                'measurements': public_measurements(profile.measurements),
                'profile_updated': True,
                'replaced_existing': replace_existing,
            },
            status_code=status.HTTP_200_OK,
        )


class RiderCustomerStylesView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=RiderCustomerStylePresetSerializer,
        summary='Save customer style preset',
        description='Create or update a style preset on the customer account.',
        tags=['Rider Customers'],
    )
    def post(self, request, customer_id):
        _, error_response = require_approved_rider(request)
        if error_response:
            return error_response

        customer = get_customer_user_or_none(customer_id)
        if not customer:
            return api_response(
                success=False,
                message='Customer not found',
                status_code=status.HTTP_404_NOT_FOUND,
            )

        serializer = RiderCustomerStylePresetSerializer(
            data=request.data,
            context={'request': request, 'style_owner_customer': customer},
        )
        if not serializer.is_valid():
            return api_response(
                success=False,
                message='Validation failed',
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        preset_name = serializer.validated_data['preset_name'].strip()
        description = serializer.validated_data.get('description')
        set_as_default = serializer.validated_data.get('set_as_default', False)

        preset_styles = [
            enrich_preset_style(
                {
                    'category': style['category'],
                    'style_id': style['style_id'],
                    **({'text': str(style['text'])} if style.get('text') is not None else {}),
                    **(
                        {'reference_image_ids': style['reference_image_ids']}
                        if style.get('reference_image_ids') is not None
                        else {}
                    ),
                },
                idx,
                request.user,
                customer=customer,
            )
            for idx, style in enumerate(serializer.validated_data['styles'])
        ]

        if set_as_default:
            UserStylePreset.objects.filter(user=customer).update(is_default=False)

        preset, created = UserStylePreset.objects.update_or_create(
            user=customer,
            name=preset_name,
            defaults={
                'description': description or '',
                'styles': preset_styles,
                'is_default': set_as_default,
            },
        )

        log_customer_data_change(
            customer=customer,
            actor_user=request.user,
            actor_role=getattr(request.user, 'role', ''),
            entity_type='customer_profile',
            entity_id=customer.customer_profile.id,
            action='create' if created else 'update',
            after=UserStylePresetSerializer(preset, context={'request': request}).data,
            source='rider_app',
        )

        all_presets = UserStylePreset.objects.filter(user=customer).order_by(
            '-is_default',
            '-updated_at',
            '-id',
        )
        return api_response(
            success=True,
            message='Style preset saved successfully',
            data={
                'customer_id': customer.id,
                'style_preset': UserStylePresetSerializer(
                    preset,
                    context={'request': request},
                ).data,
                'all_style_presets': UserStylePresetSerializer(
                    all_presets,
                    many=True,
                    context={'request': request},
                ).data,
            },
            status_code=status.HTTP_201_CREATED,
        )
