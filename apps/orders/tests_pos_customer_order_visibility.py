from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.customers.models import Address, CustomerProfile, FamilyMember
from apps.tailors.models import Fabric, FabricCategory, TailorProfile
from apps.orders.models import Order


User = get_user_model()


@override_settings(
    SECURE_SSL_REDIRECT=False,
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    },
)
class PosCustomerOrderVisibilityTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.tailor_user = User.objects.create_user(
            username='pos_tailor',
            phone='+966500000001',
            role='TAILOR',
        )
        self.tailor_profile, _ = TailorProfile.objects.get_or_create(user=self.tailor_user)
        self.tailor_profile.shop_name = 'POS Tailor Shop'
        self.tailor_profile.shop_status = True
        self.tailor_profile.save(update_fields=['shop_name', 'shop_status'])
        self.fabric_category = FabricCategory.objects.create(
            name='Cotton',
            slug='cotton',
        )
        self.fabric = Fabric.objects.create(
            tailor=self.tailor_profile,
            name='White Cotton',
            price=Decimal('100.00'),
            stock=5,
            is_active=True,
            category=self.fabric_category,
        )
        self.other_tailor_user = User.objects.create_user(
            username='other_pos_tailor',
            phone='+966500000003',
            role='TAILOR',
        )
        self.other_tailor_profile, _ = TailorProfile.objects.get_or_create(user=self.other_tailor_user)
        self.other_tailor_profile.shop_name = 'Other POS Tailor Shop'
        self.other_tailor_profile.shop_status = True
        self.other_tailor_profile.save(update_fields=['shop_name', 'shop_status'])
        self.other_fabric = Fabric.objects.create(
            tailor=self.other_tailor_profile,
            name='Black Cotton',
            price=Decimal('120.00'),
            stock=5,
            is_active=True,
            category=self.fabric_category,
        )

    def _create_pos_customer(self):
        self.client.force_authenticate(user=self.tailor_user)
        response = self.client.post(
            '/api/tailors/pos/customers/create/',
            {'phone': '966500000002', 'name': 'POS Customer'},
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.data)
        customer = User.objects.get(id=response.data['data']['id'])
        self.assertEqual(customer.phone, '+966500000002')
        self.assertEqual(customer.customer_profile.pos_created_by, self.tailor_user)
        return customer

    def test_tailor_created_walk_in_order_is_visible_to_pos_customer_with_item_details(self):
        customer = self._create_pos_customer()

        self.client.force_authenticate(user=self.tailor_user)
        create_response = self.client.post(
            '/api/orders/create/',
            {
                'customer': customer.id,
                'tailor': self.tailor_user.id,
                'order_type': 'fabric_with_stitching',
                'service_mode': 'walk_in',
                'payment_method': 'cod',
                'items': [
                    {
                        'fabric': self.fabric.id,
                        'quantity': 1,
                        'measurements': {'chest': 102, 'length': 144},
                        'custom_styles': [
                            {
                                'style_type': 'collar',
                                'index': 1,
                                'label': 'Classic Collar',
                                'asset_path': 'custom_styles/classic_collar.png',
                                'text': 'Keep collar firm',
                            }
                        ],
                        'custom_instructions': 'Use white buttons',
                    }
                ],
            },
            format='json',
        )

        self.assertEqual(create_response.status_code, 201, create_response.data)
        order_id = create_response.data['data']['id']
        order = Order.objects.get(id=order_id)
        self.assertEqual(order.customer, customer)
        self.assertEqual(order.tailor, self.tailor_user)
        self.assertEqual(order.status, 'confirmed')
        self.assertEqual(order.tailor_status, 'accepted')
        self.assertEqual(order.payment_status, 'paid')

        self.client.force_authenticate(user=customer)
        list_response = self.client.get('/api/orders/customer/my-orders/')
        self.assertEqual(list_response.status_code, 200, list_response.data)
        orders = list_response.data['data']
        self.assertEqual(len(orders), 1)
        self.assertEqual(orders[0]['id'], order_id)
        self.assertEqual(orders[0]['items'][0]['measurements'], {'chest': 102, 'length': 144})
        self.assertEqual(orders[0]['items'][0]['custom_styles'][0]['label'], 'Classic Collar')
        self.assertEqual(orders[0]['items'][0]['custom_styles'][0]['text'], 'Keep collar firm')

        detail_response = self.client.get(f'/api/orders/{order_id}/')
        self.assertEqual(detail_response.status_code, 200, detail_response.data)
        self.assertEqual(detail_response.data['data']['customer'], customer.id)
        self.assertEqual(detail_response.data['data']['items'][0]['custom_instructions'], 'Use white buttons')

    def test_tailor_created_order_can_use_customer_family_member_and_address(self):
        customer = self._create_pos_customer()
        family_member = FamilyMember.objects.create(user=customer, name='Ali', relationship='son')
        address = Address.objects.create(
            user=customer,
            street='King Fahd Road',
            city='Riyadh',
            country='Saudi Arabia',
            latitude=Decimal('24.713600'),
            longitude=Decimal('46.675300'),
        )

        self.client.force_authenticate(user=self.tailor_user)
        response = self.client.post(
            '/api/orders/create/',
            {
                'customer': customer.id,
                'tailor': self.tailor_user.id,
                'order_type': 'fabric_with_stitching',
                'service_mode': 'home_delivery',
                'payment_method': 'cod',
                'delivery_address': address.id,
                'items': [
                    {
                        'fabric': self.fabric.id,
                        'quantity': 1,
                        'family_member': family_member.id,
                        'measurements': {'shoulder': 45},
                    }
                ],
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201, response.data)
        order = Order.objects.get(id=response.data['data']['id'])
        self.assertEqual(order.customer, customer)
        self.assertEqual(order.delivery_address, address)
        self.assertEqual(order.order_items.get().family_member, family_member)

    def test_pos_customer_create_requires_phone_and_name(self):
        self.client.force_authenticate(user=self.tailor_user)
        response = self.client.post('/api/tailors/pos/customers/create/', {}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data['success'])
        self.assertTrue(response.data['errors'])

    def test_other_customer_cannot_view_pos_order_detail(self):
        customer = self._create_pos_customer()
        other_customer = User.objects.create_user(username='other_customer', role='USER')
        CustomerProfile.objects.create(user=other_customer)

        self.client.force_authenticate(user=self.tailor_user)
        create_response = self.client.post(
            '/api/orders/create/',
            {
                'customer': customer.id,
                'tailor': self.tailor_user.id,
                'order_type': 'fabric_only',
                'service_mode': 'walk_in',
                'payment_method': 'cod',
                'items': [{'fabric': self.fabric.id, 'quantity': 1}],
            },
            format='json',
        )
        self.assertEqual(create_response.status_code, 201, create_response.data)

        self.client.force_authenticate(user=other_customer)
        detail_response = self.client.get(f"/api/orders/{create_response.data['data']['id']}/")
        self.assertEqual(detail_response.status_code, 403)

    def test_tailor_pos_customer_orders_are_scoped_to_current_tailor(self):
        customer = self._create_pos_customer()

        self.client.force_authenticate(user=self.tailor_user)
        current_tailor_response = self.client.post(
            '/api/orders/create/',
            {
                'customer': customer.id,
                'tailor': self.tailor_user.id,
                'order_type': 'fabric_with_stitching',
                'service_mode': 'walk_in',
                'payment_method': 'cod',
                'items': [
                    {
                        'fabric': self.fabric.id,
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
        self.assertEqual(current_tailor_response.status_code, 201, current_tailor_response.data)
        current_tailor_order_id = current_tailor_response.data['data']['id']

        self.client.force_authenticate(user=self.other_tailor_user)
        other_tailor_response = self.client.post(
            '/api/orders/create/',
            {
                'customer': customer.id,
                'tailor': self.other_tailor_user.id,
                'order_type': 'fabric_only',
                'service_mode': 'walk_in',
                'payment_method': 'cod',
                'items': [{'fabric': self.other_fabric.id, 'quantity': 1}],
            },
            format='json',
        )
        self.assertEqual(other_tailor_response.status_code, 201, other_tailor_response.data)
        other_tailor_order_id = other_tailor_response.data['data']['id']

        self.client.force_authenticate(user=self.tailor_user)
        list_response = self.client.get(f'/api/tailors/pos/customers/{customer.id}/orders/')
        self.assertEqual(list_response.status_code, 200, list_response.data)
        order_ids = [order['id'] for order in list_response.data['data']]
        self.assertEqual(order_ids, [current_tailor_order_id])
        self.assertEqual(list_response.data['data'][0]['items'][0]['measurements'], {'chest': 102})
        self.assertEqual(list_response.data['data'][0]['items'][0]['custom_styles'][0]['label'], 'Square Cuff')

        detail_response = self.client.get(
            f'/api/tailors/pos/customers/{customer.id}/orders/{current_tailor_order_id}/'
        )
        self.assertEqual(detail_response.status_code, 200, detail_response.data)
        self.assertEqual(detail_response.data['data']['id'], current_tailor_order_id)
        self.assertEqual(detail_response.data['data']['items'][0]['measurements'], {'chest': 102})

        cross_tailor_detail_response = self.client.get(
            f'/api/tailors/pos/customers/{customer.id}/orders/{other_tailor_order_id}/'
        )
        self.assertEqual(cross_tailor_detail_response.status_code, 404)

    def test_tailor_can_create_walk_in_stitching_only_order_without_catalog_fabric(self):
        customer = self._create_pos_customer()
        initial_stock = self.fabric.stock

        self.client.force_authenticate(user=self.tailor_user)
        response = self.client.post(
            '/api/orders/create/',
            {
                'customer': customer.id,
                'tailor': self.tailor_user.id,
                'order_type': 'stitching_only',
                'service_mode': 'walk_in',
                'payment_method': 'cod',
                'stitching_price': '80.00',
                'items': [
                    {
                        'quantity': 1,
                        'measurements': {'chest': 102, 'length': 144},
                        'custom_styles': [
                            {
                                'style_type': 'collar',
                                'index': 1,
                                'label': 'Classic Collar',
                                'asset_path': 'custom_styles/classic_collar.png',
                            }
                        ],
                        'custom_instructions': 'Customer brought own white fabric.',
                    }
                ],
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201, response.data)
        order_id = response.data['data']['id']
        order = Order.objects.get(id=order_id)
        item = order.order_items.get()
        self.assertEqual(order.order_type, 'stitching_only')
        self.assertEqual(order.customer, customer)
        self.assertEqual(order.tailor, self.tailor_user)
        self.assertEqual(order.service_mode, 'walk_in')
        self.assertEqual(order.stitching_price, Decimal('80.00'))
        self.assertEqual(order.subtotal, Decimal('0.00'))
        self.assertEqual(order.total_amount, Decimal('80.00'))
        self.assertEqual(order.payment_status, 'paid')
        self.assertIsNone(item.fabric)
        self.assertEqual(item.unit_price, Decimal('0.00'))
        self.assertEqual(item.measurements, {'chest': 102, 'length': 144})

        self.fabric.refresh_from_db()
        self.assertEqual(self.fabric.stock, initial_stock)

        self.client.force_authenticate(user=customer)
        customer_orders_response = self.client.get('/api/orders/customer/my-orders/')
        self.assertEqual(customer_orders_response.status_code, 200, customer_orders_response.data)
        self.assertEqual(customer_orders_response.data['data'][0]['id'], order_id)
        self.assertEqual(customer_orders_response.data['data'][0]['items'][0]['fabric'], None)
        self.assertEqual(
            customer_orders_response.data['data'][0]['items'][0]['custom_instructions'],
            'Customer brought own white fabric.',
        )

        self.client.force_authenticate(user=self.tailor_user)
        pos_detail_response = self.client.get(
            f'/api/tailors/pos/customers/{customer.id}/orders/{order_id}/'
        )
        self.assertEqual(pos_detail_response.status_code, 200, pos_detail_response.data)
        self.assertEqual(pos_detail_response.data['data']['order_type'], 'stitching_only')
        self.assertEqual(pos_detail_response.data['data']['items'][0]['fabric'], None)

    def test_stitching_only_rejects_home_delivery_and_catalog_fabric(self):
        customer = self._create_pos_customer()

        self.client.force_authenticate(user=self.tailor_user)
        home_delivery_response = self.client.post(
            '/api/orders/create/',
            {
                'customer': customer.id,
                'tailor': self.tailor_user.id,
                'order_type': 'stitching_only',
                'service_mode': 'home_delivery',
                'payment_method': 'cod',
                'stitching_price': '80.00',
                'delivery_address': {
                    'latitude': 24.7136,
                    'longitude': 46.6753,
                    'formatted_address': 'Riyadh',
                },
                'items': [{'quantity': 1, 'measurements': {'chest': 102}}],
            },
            format='json',
        )
        self.assertEqual(home_delivery_response.status_code, 400)
        self.assertIn('walk-in', str(home_delivery_response.data['errors']))

        catalog_fabric_response = self.client.post(
            '/api/orders/create/',
            {
                'customer': customer.id,
                'tailor': self.tailor_user.id,
                'order_type': 'stitching_only',
                'service_mode': 'walk_in',
                'payment_method': 'cod',
                'stitching_price': '80.00',
                'items': [
                    {
                        'fabric': self.fabric.id,
                        'quantity': 1,
                        'measurements': {'chest': 102},
                    }
                ],
            },
            format='json',
        )
        self.assertEqual(catalog_fabric_response.status_code, 400)
        self.assertIn('catalog fabric', str(catalog_fabric_response.data['errors']))
