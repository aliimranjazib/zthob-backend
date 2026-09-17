from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.customization.models import UserStylePreset
from apps.customers.models import CustomerProfile, TailorPOSCustomerLink
from apps.tailors.models import Fabric, FabricCategory, TailorProfile


User = get_user_model()


@override_settings(
    SECURE_SSL_REDIRECT=False,
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    },
)
class POSCreateCustomerShopLinkTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.tailor_user = User.objects.create_user(
            username='pos_create_tailor_a',
            phone='+966500000201',
            role='TAILOR',
            first_name='Shop',
            last_name='A',
        )
        self.tailor_profile, _ = TailorProfile.objects.get_or_create(user=self.tailor_user)
        self.tailor_profile.shop_name = 'Shop A'
        self.tailor_profile.shop_status = True
        self.tailor_profile.save(update_fields=['shop_name', 'shop_status'])

        self.other_tailor_user = User.objects.create_user(
            username='pos_create_tailor_b',
            phone='+966500000203',
            role='TAILOR',
            first_name='Shop',
            last_name='B',
        )
        self.other_tailor_profile, _ = TailorProfile.objects.get_or_create(user=self.other_tailor_user)
        self.other_tailor_profile.shop_name = 'Shop B'
        self.other_tailor_profile.shop_status = True
        self.other_tailor_profile.save(update_fields=['shop_name', 'shop_status'])

        self.fabric_category = FabricCategory.objects.create(
            name='Cotton POS Link',
            slug='cotton-pos-link',
        )
        self.fabric = Fabric.objects.create(
            tailor=self.tailor_profile,
            name='Shop A Cotton',
            price=Decimal('100.00'),
            stock=5,
            is_active=True,
            category=self.fabric_category,
        )
        self.other_fabric = Fabric.objects.create(
            tailor=self.other_tailor_profile,
            name='Shop B Cotton',
            price=Decimal('120.00'),
            stock=5,
            is_active=True,
            category=self.fabric_category,
        )
        self.create_url = '/api/tailors/pos/customers/create/'

    def _create_walk_in_order(self, *, tailor, fabric, customer_id):
        self.client.force_authenticate(user=tailor)
        response = self.client.post(
            '/api/orders/create/',
            {
                'customer': customer_id,
                'tailor': tailor.id,
                'order_type': 'fabric_with_stitching',
                'service_mode': 'walk_in',
                'payment_method': 'cod',
                'items': [
                    {
                        'fabric': fabric.id,
                        'quantity': 1,
                        'measurements': {'chest': 102},
                        'custom_styles': [
                            {
                                'style_type': 'cuff',
                                'index': 2,
                                'label': 'Square Cuff',
                                'asset_path': 'custom_styles/square_cuff.png',
                            }
                        ],
                    }
                ],
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.data)
        return response.data['data']['id']

    def _list_customers(self, tailor):
        self.client.force_authenticate(user=tailor)
        response = self.client.get('/api/tailors/pos/customers/')
        self.assertEqual(response.status_code, 200, response.data)
        return response.data['data']

    def test_new_phone_creates_customer_link_and_allows_order(self):
        self.client.force_authenticate(user=self.tailor_user)
        response = self.client.post(
            self.create_url,
            {'phone': '966500000202', 'name': 'Walk In Ahmed'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertFalse(response.data['data']['is_existing'])
        self.assertEqual(response.data['data']['name'], 'Walk In Ahmed')
        self.assertIsNone(response.data['data']['measurements'])

        customer = User.objects.get(id=response.data['data']['id'])
        self.assertEqual(customer.customer_profile.pos_created_by, self.tailor_user)
        self.assertTrue(
            TailorPOSCustomerLink.objects.filter(
                customer=customer,
                tailor=self.tailor_user,
            ).exists()
        )

        order_id = self._create_walk_in_order(
            tailor=self.tailor_user,
            fabric=self.fabric,
            customer_id=customer.id,
        )
        self.assertTrue(order_id)

    def test_same_shop_second_add_keeps_name_and_still_allows_order(self):
        self.client.force_authenticate(user=self.tailor_user)
        first = self.client.post(
            self.create_url,
            {'phone': '966500000204', 'name': 'Original Name'},
            format='json',
        )
        self.assertEqual(first.status_code, status.HTTP_201_CREATED, first.data)
        customer_id = first.data['data']['id']

        second = self.client.post(
            self.create_url,
            {'phone': '966500000204', 'name': 'Typed Different Name'},
            format='json',
        )
        self.assertEqual(second.status_code, status.HTTP_200_OK, second.data)
        self.assertTrue(second.data['data']['is_existing'])
        self.assertEqual(second.data['data']['name'], 'Original Name')
        self.assertEqual(second.data['message'], 'Customer already exists')

        customer = User.objects.get(id=customer_id)
        self.assertEqual(customer.first_name, 'Original')
        self.assertEqual(customer.last_name, 'Name')
        self.assertEqual(customer.customer_profile.pos_created_by, self.tailor_user)

        self._create_walk_in_order(
            tailor=self.tailor_user,
            fabric=self.fabric,
            customer_id=customer_id,
        )

    @patch('apps.customers.services.customer_provisioning.queue_customer_welcome_sms')
    def test_existing_customer_app_user_is_linked_without_leaking_profile_data(self, mock_queue):
        existing = User.objects.create_user(
            username='app_customer_pos',
            phone='0500000205',
            role='USER',
            first_name='Khalid',
            last_name='App',
        )
        CustomerProfile.objects.create(
            user=existing,
            measurements={'chest': 40, 'length': 55},
        )
        UserStylePreset.objects.create(
            user=existing,
            name='App Preset',
            styles=[{'category': 'collar', 'style_id': 1}],
            is_default=True,
        )

        self.client.force_authenticate(user=self.tailor_user)
        response = self.client.post(
            self.create_url,
            {'phone': '0500000205', 'name': 'Should Be Ignored'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertFalse(response.data['data']['is_existing'])
        self.assertEqual(response.data['data']['id'], existing.id)
        self.assertEqual(response.data['data']['name'], 'Khalid App')
        self.assertIsNone(response.data['data']['measurements'])
        self.assertEqual(response.data['data']['total_orders'], 0)
        mock_queue.assert_not_called()

        existing.refresh_from_db()
        self.assertEqual(existing.first_name, 'Khalid')
        self.assertEqual(existing.last_name, 'App')
        self.assertIsNone(existing.customer_profile.pos_created_by_id)
        self.assertTrue(
            TailorPOSCustomerLink.objects.filter(
                customer=existing,
                tailor=self.tailor_user,
            ).exists()
        )

        customers = self._list_customers(self.tailor_user)
        entry = next(item for item in customers if item['id'] == existing.id)
        self.assertIsNone(entry['measurements'])
        self.assertEqual(entry['style_presets'], [])
        self.assertEqual(entry['order_styles'], [])
        self.assertEqual(entry['total_orders'], 0)

        self._create_walk_in_order(
            tailor=self.tailor_user,
            fabric=self.fabric,
            customer_id=existing.id,
        )

    def test_other_shop_add_reuses_account_without_showing_previous_shop_data(self):
        self.client.force_authenticate(user=self.tailor_user)
        create_a = self.client.post(
            self.create_url,
            {'phone': '966500000206', 'name': 'Shared Customer'},
            format='json',
        )
        self.assertEqual(create_a.status_code, status.HTTP_201_CREATED, create_a.data)
        customer_id = create_a.data['data']['id']
        customer = User.objects.get(id=customer_id)
        customer.customer_profile.measurements = {'chest': 99}
        customer.customer_profile.save(update_fields=['measurements'])

        order_a_id = self._create_walk_in_order(
            tailor=self.tailor_user,
            fabric=self.fabric,
            customer_id=customer_id,
        )

        self.client.force_authenticate(user=self.other_tailor_user)
        create_b = self.client.post(
            self.create_url,
            {'phone': '966500000206', 'name': 'Name From Shop B'},
            format='json',
        )
        self.assertEqual(create_b.status_code, status.HTTP_201_CREATED, create_b.data)
        self.assertFalse(create_b.data['data']['is_existing'])
        self.assertEqual(create_b.data['data']['id'], customer_id)
        self.assertEqual(create_b.data['data']['name'], 'Shared Customer')
        self.assertIsNone(create_b.data['data']['measurements'])
        self.assertEqual(create_b.data['data']['total_orders'], 0)

        customer.refresh_from_db()
        self.assertEqual(customer.first_name, 'Shared')
        self.assertEqual(customer.customer_profile.pos_created_by, self.tailor_user)
        self.assertTrue(
            TailorPOSCustomerLink.objects.filter(
                customer=customer,
                tailor=self.other_tailor_user,
            ).exists()
        )

        shop_a_list = self._list_customers(self.tailor_user)
        shop_a_entry = next(item for item in shop_a_list if item['id'] == customer_id)
        self.assertEqual(shop_a_entry['measurements'], {'chest': 99})
        self.assertEqual(shop_a_entry['total_orders'], 1)
        self.assertEqual(len(shop_a_entry['order_styles']), 1)

        shop_b_list = self._list_customers(self.other_tailor_user)
        shop_b_entry = next(item for item in shop_b_list if item['id'] == customer_id)
        self.assertIsNone(shop_b_entry['measurements'])
        self.assertEqual(shop_b_entry['style_presets'], [])
        self.assertEqual(shop_b_entry['order_styles'], [])
        self.assertEqual(shop_b_entry['total_orders'], 0)

        order_b_id = self._create_walk_in_order(
            tailor=self.other_tailor_user,
            fabric=self.other_fabric,
            customer_id=customer_id,
        )

        self.client.force_authenticate(user=self.other_tailor_user)
        b_orders = self.client.get(f'/api/tailors/pos/customers/{customer_id}/orders/')
        self.assertEqual(b_orders.status_code, 200, b_orders.data)
        self.assertEqual([order['id'] for order in b_orders.data['data']], [order_b_id])

        self.client.force_authenticate(user=self.tailor_user)
        a_orders = self.client.get(f'/api/tailors/pos/customers/{customer_id}/orders/')
        self.assertEqual(a_orders.status_code, 200, a_orders.data)
        self.assertEqual([order['id'] for order in a_orders.data['data']], [order_a_id])

    def test_non_customer_phone_is_rejected_without_mutation(self):
        rider = User.objects.create_user(
            username='pos_blocked_rider',
            phone='0500000207',
            role='RIDER',
            first_name='Rider',
            last_name='Person',
        )

        self.client.force_authenticate(user=self.tailor_user)
        rider_response = self.client.post(
            self.create_url,
            {'phone': '0500000207', 'name': 'Fake Customer'},
            format='json',
        )
        self.assertEqual(rider_response.status_code, status.HTTP_400_BAD_REQUEST, rider_response.data)
        self.assertFalse(rider_response.data['success'])

        rider.refresh_from_db()
        self.assertEqual(rider.first_name, 'Rider')
        self.assertEqual(rider.role, 'RIDER')
        self.assertFalse(CustomerProfile.objects.filter(user=rider).exists())
        self.assertFalse(
            TailorPOSCustomerLink.objects.filter(customer=rider, tailor=self.tailor_user).exists()
        )

        tailor_response = self.client.post(
            self.create_url,
            {'phone': '+966500000203', 'name': 'Other Tailor As Customer'},
            format='json',
        )
        self.assertEqual(tailor_response.status_code, status.HTTP_400_BAD_REQUEST, tailor_response.data)
        self.other_tailor_user.refresh_from_db()
        self.assertEqual(self.other_tailor_user.first_name, 'Shop')
        self.assertEqual(self.other_tailor_user.role, 'TAILOR')
