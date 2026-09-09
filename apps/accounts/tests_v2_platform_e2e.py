"""
V2 platform end-to-end flow:

  owner login -> business -> shop -> staff (all roles) -> switch shop
  tailor login -> shop register
  staff login -> switch shop
  customer order flow on shop created via v2

Run:
  uv run python manage.py test apps.accounts.tests_v2_platform_e2e -v 2
"""

from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.core.services import PhoneVerificationService
from apps.customers.models import Address, CustomerProfile
from apps.orders.models import Order
from apps.riders.models import RiderProfile, RiderProfileReview
from apps.tailors.models import Fabric, FabricCategory, ServiceArea, TailorProfile


User = get_user_model()

TEST_REST_FRAMEWORK = {
    **settings.REST_FRAMEWORK,
    'DEFAULT_THROTTLE_CLASSES': [],
}

STAFF_ROLES = ['manager', 'stitcher', 'cutter', 'receptionist', 'finisher']
STAFF_PHONES = [
    '0522222220',
    '0522222221',
    '0522222222',
    '0522222223',
    '0522222224',
]


@override_settings(
    REST_FRAMEWORK=TEST_REST_FRAMEWORK,
    SECURE_SSL_REDIRECT=False,
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    },
)
class V2PlatformEndToEndFlowTest(TestCase):
    OWNER_PHONE = '0500000001'
    TAILOR_PHONE = '0500000002'
    CUSTOMER_PHONE = '0500000004'
    TEST_OTP = PhoneVerificationService.TEST_OTP

    def setUp(self):
        from apps.accounts import views as account_views

        self._saved_throttles = (
            account_views.PhoneLoginView.throttle_classes,
            account_views.PhoneVerifyView.throttle_classes,
        )
        account_views.PhoneLoginView.throttle_classes = []
        account_views.PhoneVerifyView.throttle_classes = []

        patch(
            'apps.notifications.tasks.send_order_status_notification_task.delay'
        ).start()
        patch(
            'apps.notifications.tasks.send_rider_status_notification_task.delay'
        ).start()
        patch(
            'apps.notifications.tasks.send_tailor_status_notification_task.delay'
        ).start()
        patch(
            'apps.notifications.services.NotificationService.send_new_order_broadcast'
        ).start()
        patch(
            'apps.notifications.services.NotificationService.send_notification'
        ).start()
        patch('apps.customers.services.welcome_sms.queue_customer_welcome_sms').start()
        self.addCleanup(patch.stopall)

        self.client = APIClient()
        self.service_area = ServiceArea.objects.create(
            name='V2 Test Area',
            city='Riyadh',
            is_active=True,
        )

        self.measurement_rider = self._create_approved_rider(
            'v2_measurement_rider',
            '+966500000221',
        )
        self.delivery_rider = self._create_approved_rider(
            'v2_delivery_rider',
            '+966500000331',
        )

    def tearDown(self):
        from apps.accounts import views as account_views

        (
            account_views.PhoneLoginView.throttle_classes,
            account_views.PhoneVerifyView.throttle_classes,
        ) = self._saved_throttles

    def _url(self, name, **kwargs):
        if ':' in name and not name.startswith('v2:'):
            name = f'v2:{name}'
        return reverse(name, kwargs=kwargs)

    def _v2_login(self, phone, *, app_entry, name='V2 User', role='TAILOR'):
        self.client.post(self._url('accounts_v2:v2-phone-login'), {'phone': phone})
        return self.client.post(
            self._url('accounts_v2:v2-phone-verify'),
            {
                'phone': phone,
                'otp_code': self.TEST_OTP,
                'name': name,
                'role': role,
                'app_entry': app_entry,
            },
        )

    def _auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def _create_approved_rider(self, username, phone):
        user = User.objects.create_user(
            username=username,
            phone=phone,
            role='RIDER',
        )
        profile, _ = RiderProfile.objects.get_or_create(user=user)
        profile.full_name = username
        profile.vehicle_type = 'bike'
        profile.is_available = True
        profile.save(update_fields=['full_name', 'vehicle_type', 'is_available'])
        review, _ = RiderProfileReview.objects.get_or_create(profile=profile)
        review.review_status = 'approved'
        review.save(update_fields=['review_status'])
        return user

    def _post_action(self, client, order_id, action, role, data=None):
        payload = {'action': action, 'role': role}
        if data is not None:
            payload['data'] = data
        return client.post(
            reverse('orders:order-action', kwargs={'order_id': order_id}),
            payload,
            format='json',
        )

    def test_v2_owner_tailor_staff_and_order_flow(self):
        owner_verify = self._v2_login(
            self.OWNER_PHONE,
            app_entry='owner',
            name='V2 Owner',
        )
        self.assertEqual(owner_verify.status_code, status.HTTP_201_CREATED)
        owner_token = owner_verify.data['data']['tokens']['access_token']
        self.assertTrue(owner_verify.data['data']['is_new_user'])
        self._auth(owner_token)

        me = self.client.get(self._url('accounts_v2:v2-me'), {'app_entry': 'owner'})
        self.assertEqual(me.status_code, status.HTTP_200_OK)
        self.assertTrue(me.data['data']['onboarding']['needs_business'])
        self.assertTrue(me.data['data']['onboarding']['needs_shop'])

        business_resp = self.client.post(
            self._url('tailors_v2:v2-business'),
            {
                'name': 'V2 Ahmed Tailoring',
                'contact_phone': self.OWNER_PHONE,
                'city': 'Riyadh',
            },
            format='json',
        )
        self.assertEqual(business_resp.status_code, status.HTTP_201_CREATED)
        business_id = business_resp.data['data']['id']

        shop_resp = self.client.post(
            self._url('tailors_v2:v2-shops'),
            {
                'name': 'V2 Main Branch',
                'contact_number': self.OWNER_PHONE,
                'address': 'King Fahd Road, Riyadh',
                'service_area_id': self.service_area.id,
                'establishment_year': 2020,
                'experience_years': 6,
            },
            format='json',
        )
        self.assertEqual(shop_resp.status_code, status.HTTP_201_CREATED)
        shop_id = shop_resp.data['data']['id']
        self.assertEqual(shop_resp.data['data']['business_id'], business_id)

        staff_ids = []
        for role, phone in zip(STAFF_ROLES, STAFF_PHONES, strict=True):
            staff_resp = self.client.post(
                self._url('tailors_v2:v2-staff'),
                {
                    'name': f'V2 {role.title()}',
                    'phone': phone,
                    'roles': [role],
                    'permissions': ['can_manage_orders'],
                    'shop_id': shop_id,
                },
                format='json',
            )
            self.assertEqual(staff_resp.status_code, status.HTTP_201_CREATED, staff_resp.data)
            self.assertEqual(staff_resp.data['data']['assignments'][0]['roles'], [role])
            staff_ids.append(staff_resp.data['data']['id'])

        self.assertEqual(len(staff_ids), 5)

        switch_resp = self.client.post(
            self._url('accounts_v2:v2-switch-shop'),
            {'shop_id': shop_id, 'app_entry': 'owner'},
            format='json',
        )
        self.assertEqual(switch_resp.status_code, status.HTTP_200_OK)
        owner_work_token = switch_resp.data['data']['tokens']['access_token']
        self._auth(owner_work_token)

        fabric_category = FabricCategory.objects.create(
            name='V2 Fabric Category',
            slug='v2-fabric-category',
        )
        fabric = Fabric.objects.create(
            tailor_id=shop_id,
            name='V2 Cotton Fabric',
            price=Decimal('150.00'),
            stock=10,
            is_active=True,
            approval_status='approved',
            category=fabric_category,
        )

        tailor_verify = self._v2_login(
            self.TAILOR_PHONE,
            app_entry='tailor',
            name='V2 Single Tailor',
        )
        self.assertIn(
            tailor_verify.status_code,
            [status.HTTP_200_OK, status.HTTP_201_CREATED],
        )
        self._auth(tailor_verify.data['data']['tokens']['access_token'])
        tailor_me = self.client.get(
            self._url('accounts_v2:v2-me'),
            {'app_entry': 'tailor'},
        )
        self.assertTrue(tailor_me.data['data']['onboarding']['needs_shop'])
        tailor_shop = self.client.post(
            self._url('tailors_v2:v2-shops'),
            {
                'name': 'V2 Tailor Solo Shop',
                'contact_number': self.TAILOR_PHONE,
                'address': 'Olaya Street, Riyadh',
                'service_area_id': self.service_area.id,
            },
            format='json',
            HTTP_X_APP_ENTRY='tailor',
        )
        self.assertEqual(tailor_shop.status_code, status.HTTP_201_CREATED, tailor_shop.data)

        manager_phone = STAFF_PHONES[0]
        staff_verify = self._v2_login(
            manager_phone,
            app_entry='staff',
            name='V2 Manager',
        )
        self.assertEqual(staff_verify.status_code, status.HTTP_200_OK)
        self._auth(staff_verify.data['data']['tokens']['access_token'])
        staff_me = self.client.get(
            self._url('accounts_v2:v2-me'),
            {'app_entry': 'staff'},
        )
        self.assertEqual(staff_me.data['data']['membership']['type'], 'staff')
        self.assertGreater(staff_me.data['data']['session']['assigned_shops_count'], 0)

        staff_switch = self.client.post(
            self._url('accounts_v2:v2-switch-shop'),
            {'shop_id': shop_id, 'app_entry': 'staff'},
            format='json',
        )
        self.assertEqual(staff_switch.status_code, status.HTTP_200_OK)

        self._run_customer_order_flow(
            shop_id=shop_id,
            fabric=fabric,
            owner_token=owner_work_token,
        )

    def _run_customer_order_flow(self, *, shop_id, fabric, owner_token):
        customer_client = APIClient()
        customer_client.post(reverse('accounts:phone-login'), {'phone': self.CUSTOMER_PHONE})
        customer_verify = customer_client.post(
            reverse('accounts:phone-verify'),
            {
                'phone': self.CUSTOMER_PHONE,
                'otp_code': self.TEST_OTP,
                'name': 'V2 Customer',
                'role': 'USER',
            },
        )
        self.assertIn(
            customer_verify.status_code,
            [status.HTTP_200_OK, status.HTTP_201_CREATED],
        )
        customer = User.objects.get(phone=self.CUSTOMER_PHONE)
        CustomerProfile.objects.get_or_create(user=customer)
        address = Address.objects.create(
            user=customer,
            street='V2 Customer Street',
            city='Riyadh',
            country='Saudi Arabia',
            latitude=Decimal('24.713600'),
            longitude=Decimal('46.675300'),
        )
        customer_client.force_authenticate(user=customer)

        shop = TailorProfile.objects.get(id=shop_id)
        order_resp = customer_client.post(
            reverse('orders:order-create'),
            {
                'tailor': shop.shop_owner_user_id,
                'shop': shop_id,
                'order_type': 'fabric_with_stitching',
                'service_mode': 'home_delivery',
                'payment_method': 'cod',
                'delivery_address': address.id,
                'items': [
                    {
                        'fabric': fabric.id,
                        'quantity': 1,
                        'measurements': {},
                        'custom_instructions': 'V2 platform order',
                    }
                ],
            },
            format='json',
        )
        self.assertEqual(order_resp.status_code, status.HTTP_201_CREATED, order_resp.data)
        order_id = order_resp.data['data']['id']

        tailor_client = APIClient()
        tailor_client.credentials(HTTP_AUTHORIZATION=f'Bearer {owner_token}')

        accept_resp = self._post_action(
            tailor_client,
            order_id,
            'accept_order',
            'TAILOR',
            {
                'assigned_rider_id': self.measurement_rider.id,
                'rider_assignment_type': 'measurement',
            },
        )
        self.assertEqual(accept_resp.status_code, status.HTTP_200_OK, accept_resp.data)

        for action in ('accept_order', 'start_measuring'):
            rider_client = APIClient()
            rider_client.force_authenticate(user=self.measurement_rider)
            response = self._post_action(rider_client, order_id, action, 'RIDER')
            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        measure_resp = self._post_action(
            rider_client,
            order_id,
            'record_measurements',
            'RIDER',
            {'measurements': {'chest': 100, 'length': 140}},
        )
        self.assertEqual(measure_resp.status_code, status.HTTP_200_OK, measure_resp.data)

        stitching_date = (timezone.now().date() + timedelta(days=5)).isoformat()
        stitch_start = self._post_action(
            tailor_client,
            order_id,
            'start_stitching',
            'TAILOR',
            {'stitching_completion_date': stitching_date},
        )
        self.assertEqual(stitch_start.status_code, status.HTTP_200_OK, stitch_start.data)

        stitch_finish = self._post_action(
            tailor_client,
            order_id,
            'finish_stitching',
            'TAILOR',
        )
        self.assertEqual(stitch_finish.status_code, status.HTTP_200_OK, stitch_finish.data)

        mark_ready = self._post_action(
            tailor_client,
            order_id,
            'mark_ready',
            'TAILOR',
            {'assigned_rider_id': self.delivery_rider.id},
        )
        self.assertEqual(mark_ready.status_code, status.HTTP_200_OK, mark_ready.data)

        delivery_client = APIClient()
        delivery_client.force_authenticate(user=self.delivery_rider)
        for action in ('accept_order', 'pickup_order', 'start_delivery'):
            response = self._post_action(delivery_client, order_id, action, 'RIDER')
            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        collect_resp = self._post_action(
            delivery_client,
            order_id,
            'collect_cash_payment',
            'RIDER',
            {},
        )
        self.assertEqual(collect_resp.status_code, status.HTTP_200_OK, collect_resp.data)

        deliver_resp = self._post_action(
            delivery_client,
            order_id,
            'mark_delivered',
            'RIDER',
        )
        self.assertEqual(deliver_resp.status_code, status.HTTP_200_OK, deliver_resp.data)

        order = Order.objects.get(id=order_id)
        self.assertEqual(order.status, 'delivered')
        fabric.refresh_from_db()
        self.assertEqual(fabric.stock, 9)

    def test_v2_list_endpoints_use_bounded_queries(self):
        owner_verify = self._v2_login(self.OWNER_PHONE, app_entry='owner', name='Query Owner')
        self._auth(owner_verify.data['data']['tokens']['access_token'])
        self.client.post(
            self._url('tailors_v2:v2-business'),
            {'name': 'Query Business', 'contact_phone': self.OWNER_PHONE},
            format='json',
        )
        shop_resp = self.client.post(
            self._url('tailors_v2:v2-shops'),
            {
                'name': 'Query Shop',
                'address': 'Riyadh',
                'service_area_id': self.service_area.id,
            },
            format='json',
        )
        shop_id = shop_resp.data['data']['id']
        for role, phone in zip(STAFF_ROLES[:2], STAFF_PHONES[:2], strict=True):
            self.client.post(
                self._url('tailors_v2:v2-staff'),
                {
                    'name': role,
                    'phone': phone,
                    'roles': [role],
                    'shop_id': shop_id,
                },
                format='json',
            )

        from django.test.utils import CaptureQueriesContext
        from django.db import connection

        with CaptureQueriesContext(connection) as shop_ctx:
            shops = self.client.get(self._url('tailors_v2:v2-shops'))
        self.assertEqual(shops.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(shop_ctx), 6)

        with CaptureQueriesContext(connection) as staff_ctx:
            staff = self.client.get(self._url('tailors_v2:v2-staff'))
        self.assertEqual(staff.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(staff_ctx), 6)
