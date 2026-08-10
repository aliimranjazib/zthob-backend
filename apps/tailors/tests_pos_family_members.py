from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.customers.models import CustomerDataAuditLog, CustomerProfile, FamilyMember
from apps.orders.models import Order, OrderItem
from apps.tailors.models import Fabric, FabricCategory, TailorProfile

User = get_user_model()


@override_settings(
    SECURE_SSL_REDIRECT=False,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}},
)
class POSFamilyMemberTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.tailor_user = User.objects.create_user(
            username='pos_tailor_family',
            phone='0500000101',
            role='TAILOR',
        )
        self.tailor_profile, _ = TailorProfile.objects.get_or_create(user=self.tailor_user)
        self.tailor_profile.shop_name = 'Family POS Shop'
        self.tailor_profile.shop_status = True
        self.tailor_profile.save(update_fields=['shop_name', 'shop_status'])

        self.other_tailor_user = User.objects.create_user(
            username='other_tailor_family',
            phone='0500000102',
            role='TAILOR',
        )
        self.other_tailor_profile, _ = TailorProfile.objects.get_or_create(user=self.other_tailor_user)
        self.other_tailor_profile.shop_status = True
        self.other_tailor_profile.save(update_fields=['shop_status'])

        self.fabric_category = FabricCategory.objects.create(name='Cotton', slug='cotton-family')
        self.fabric = Fabric.objects.create(
            tailor=self.tailor_profile,
            name='Family Fabric',
            price=Decimal('100.00'),
            stock=10,
            is_active=True,
            category=self.fabric_category,
        )

        self.customer = User.objects.create_user(
            username='family_customer',
            phone='0500000103',
            role='USER',
            first_name='POS',
            last_name='Customer',
        )
        CustomerProfile.objects.create(user=self.customer, pos_created_by=self.tailor_user)

    def _family_url(self, customer_id=None, family_member_id=None):
        customer_id = customer_id or self.customer.id
        base = f'/api/tailors/pos/customers/{customer_id}/family/'
        if family_member_id:
            return f'{base}{family_member_id}/'
        return base

    def test_tailor_can_create_and_list_family_member(self):
        self.client.force_authenticate(user=self.tailor_user)
        response = self.client.post(
            self._family_url(),
            {'name': 'Ahmed', 'relationship': 'son'},
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['data']['name'], 'Ahmed')
        self.assertEqual(response.data['data']['created_source'], 'tailor_pos')

        list_response = self.client.get(self._family_url())
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.data['data']), 1)
        self.assertTrue(
            CustomerDataAuditLog.objects.filter(
                customer=self.customer,
                entity_type='family_member',
                action='create',
            ).exists()
        )

    def test_other_tailor_cannot_access_unrelated_customer_family(self):
        self.client.force_authenticate(user=self.other_tailor_user)
        response = self.client.get(self._family_url())
        self.assertEqual(response.status_code, 404)

    def test_customer_sees_tailor_created_family_member(self):
        self.client.force_authenticate(user=self.tailor_user)
        create_response = self.client.post(
            self._family_url(),
            {'name': 'Sara'},
            format='json',
        )
        family_id = create_response.data['data']['id']

        self.client.force_authenticate(user=self.customer)
        response = self.client.get('/api/customers/family/')
        self.assertEqual(response.status_code, 200)
        ids = [item['id'] for item in response.data['data']]
        self.assertIn(family_id, ids)

    def test_tailor_can_edit_pos_created_family_before_customer_edit(self):
        self.client.force_authenticate(user=self.tailor_user)
        create_response = self.client.post(
            self._family_url(),
            {'name': 'Old Name'},
            format='json',
        )
        family_id = create_response.data['data']['id']

        patch_response = self.client.patch(
            self._family_url(family_member_id=family_id),
            {'name': 'Updated Name'},
            format='json',
        )
        self.assertEqual(patch_response.status_code, 200)
        self.assertEqual(patch_response.data['data']['name'], 'Updated Name')

    def test_tailor_cannot_edit_family_after_customer_edit(self):
        family_member = FamilyMember.objects.create(
            user=self.customer,
            name='Customer Owned',
            created_source='tailor_pos',
            created_by_tailor=self.tailor_user,
            created_by_shop=self.tailor_profile,
        )
        family_member.customer_edited_at = timezone.now()
        family_member.save(update_fields=['customer_edited_at'])

        self.client.force_authenticate(user=self.tailor_user)
        response = self.client.patch(
            self._family_url(family_member_id=family_member.id),
            {'name': 'Blocked'},
            format='json',
        )
        self.assertEqual(response.status_code, 403)

    def test_walk_in_order_stores_recipient_snapshot(self):
        family_member = FamilyMember.objects.create(
            user=self.customer,
            name='Ali Snapshot',
            relationship='brother',
            created_source='tailor_pos',
            created_by_tailor=self.tailor_user,
            created_by_shop=self.tailor_profile,
        )

        self.client.force_authenticate(user=self.tailor_user)
        response = self.client.post(
            '/api/orders/create/',
            {
                'customer': self.customer.id,
                'tailor': self.tailor_user.id,
                'order_type': 'fabric_with_stitching',
                'service_mode': 'walk_in',
                'payment_method': 'cod',
                'items': [
                    {
                        'fabric': self.fabric.id,
                        'quantity': 1,
                        'family_member': family_member.id,
                        'measurements': {'chest': 100},
                    }
                ],
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.data)

        item = OrderItem.objects.get(order_id=response.data['data']['id'])
        self.assertEqual(item.recipient_display_name, 'Ali Snapshot')
        self.assertEqual(item.recipient_type, 'family_member')
        self.assertEqual(item.recipient_relationship, 'brother')

    def test_renamed_family_member_does_not_change_old_order_snapshot(self):
        family_member = FamilyMember.objects.create(
            user=self.customer,
            name='Before Rename',
            created_source='tailor_pos',
            created_by_tailor=self.tailor_user,
            created_by_shop=self.tailor_profile,
        )

        self.client.force_authenticate(user=self.tailor_user)
        create_response = self.client.post(
            '/api/orders/create/',
            {
                'customer': self.customer.id,
                'tailor': self.tailor_user.id,
                'order_type': 'fabric_with_stitching',
                'service_mode': 'walk_in',
                'payment_method': 'cod',
                'items': [
                    {
                        'fabric': self.fabric.id,
                        'quantity': 1,
                        'family_member': family_member.id,
                    }
                ],
            },
            format='json',
        )
        order_id = create_response.data['data']['id']
        family_member.name = 'After Rename'
        family_member.save(update_fields=['name'])

        item = OrderItem.objects.get(order_id=order_id)
        self.assertEqual(item.recipient_display_name, 'Before Rename')

    def test_tailor_measurements_do_not_overwrite_customer_profile(self):
        profile = self.customer.customer_profile
        profile.measurements = {'chest': 90}
        profile.save(update_fields=['measurements'])

        self.client.force_authenticate(user=self.tailor_user)
        create_response = self.client.post(
            '/api/orders/create/',
            {
                'customer': self.customer.id,
                'tailor': self.tailor_user.id,
                'order_type': 'fabric_with_stitching',
                'service_mode': 'walk_in',
                'payment_method': 'cod',
                'items': [
                    {
                        'fabric': self.fabric.id,
                        'quantity': 1,
                        'measurements': {'chest': 110},
                    }
                ],
            },
            format='json',
        )
        order_id = create_response.data['data']['id']

        measure_response = self.client.post(
            f'/api/tailors/orders/{order_id}/measurements/',
            {'measurements': {'chest': 112, 'length': 140}},
            format='json',
        )
        self.assertEqual(measure_response.status_code, 200, measure_response.data)

        profile.refresh_from_db()
        self.assertEqual(profile.measurements.get('chest'), 90)
        item = OrderItem.objects.get(order_id=order_id)
        self.assertEqual(item.measurements.get('chest'), 112)

    def test_replace_profile_measurements_flag_allows_overwrite(self):
        profile = self.customer.customer_profile
        profile.measurements = {'chest': 90}
        profile.save(update_fields=['measurements'])

        self.client.force_authenticate(user=self.tailor_user)
        create_response = self.client.post(
            '/api/orders/create/',
            {
                'customer': self.customer.id,
                'tailor': self.tailor_user.id,
                'order_type': 'fabric_with_stitching',
                'service_mode': 'walk_in',
                'payment_method': 'cod',
                'items': [{'fabric': self.fabric.id, 'quantity': 1}],
            },
            format='json',
        )
        order_id = create_response.data['data']['id']

        response = self.client.post(
            f'/api/tailors/orders/{order_id}/measurements/',
            {
                'measurements': {'chest': 112},
                'replace_profile_measurements': True,
            },
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        profile.refresh_from_db()
        self.assertEqual(profile.measurements.get('chest'), 112)

    def test_cannot_delete_family_member_with_active_order(self):
        family_member = FamilyMember.objects.create(
            user=self.customer,
            name='Locked Member',
            created_source='tailor_pos',
            created_by_tailor=self.tailor_user,
            created_by_shop=self.tailor_profile,
        )

        self.client.force_authenticate(user=self.tailor_user)
        self.client.post(
            '/api/orders/create/',
            {
                'customer': self.customer.id,
                'tailor': self.tailor_user.id,
                'order_type': 'fabric_with_stitching',
                'service_mode': 'walk_in',
                'payment_method': 'cod',
                'items': [
                    {
                        'fabric': self.fabric.id,
                        'quantity': 1,
                        'family_member': family_member.id,
                    }
                ],
            },
            format='json',
        )

        delete_response = self.client.delete(
            self._family_url(family_member_id=family_member.id)
        )
        self.assertEqual(delete_response.status_code, 409)

    def test_customer_edit_sets_customer_edited_at(self):
        family_member = FamilyMember.objects.create(
            user=self.customer,
            name='Editable',
            created_source='customer_app',
        )

        self.client.force_authenticate(user=self.customer)
        response = self.client.put(
            f'/api/customers/family/{family_member.id}/',
            {'name': 'Edited By Customer'},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        family_member.refresh_from_db()
        self.assertIsNotNone(family_member.customer_edited_at)
