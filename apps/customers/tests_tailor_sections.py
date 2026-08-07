from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.customers.models import Address
from apps.orders.models import Order
from apps.tailors.models import TailorProfile, TailorProfileReview

User = get_user_model()

RIYADH_LAT = 24.7136
RIYADH_LNG = 46.6753


class CustomerTailorSectionListTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = User.objects.create_user(
            username='section_customer',
            password='testpass123',
            role='USER',
        )

        self.featured_tailor = self._create_tailor(
            'featured_tailor',
            shop_name='Featured Shop',
            is_featured=True,
            is_express=True,
            avg_rating=Decimal('4.8'),
            rating_count=20,
        )
        self.express_tailor = self._create_tailor(
            'express_tailor',
            shop_name='Express Shop',
            is_express=True,
            avg_rating=Decimal('4.2'),
            rating_count=10,
        )
        self.popular_tailor = self._create_tailor(
            'popular_tailor',
            shop_name='Popular Shop',
            avg_rating=Decimal('3.5'),
            rating_count=5,
        )
        self.new_tailor = self._create_tailor(
            'new_tailor',
            shop_name='New Shop',
            avg_rating=Decimal('4.0'),
            rating_count=2,
        )
        self.inactive_tailor = self._create_tailor(
            'inactive_tailor',
            shop_name='Inactive Shop',
            shop_status=False,
        )

        for _ in range(3):
            Order.objects.create(
                customer=self.customer,
                tailor=self.popular_tailor,
                order_type='fabric_with_stitching',
                service_mode='home_delivery',
                status='pending',
                total_amount=Decimal('100.00'),
                paid_amount=Decimal('0.00'),
                remaining_amount=Decimal('100.00'),
            )

        self.far_tailor = self._create_tailor(
            'far_tailor',
            shop_name='Far Shop',
            is_featured=True,
            latitude=30.6682,
            longitude=73.1114,
        )

    def _create_tailor(
        self,
        username,
        *,
        shop_name='Test Shop',
        shop_status=True,
        is_featured=False,
        is_express=False,
        avg_rating=Decimal('0.00'),
        rating_count=0,
        latitude=RIYADH_LAT,
        longitude=RIYADH_LNG,
        review_status='approved',
    ):
        user = User.objects.create_user(
            username=username,
            password='testpass123',
            role='TAILOR',
        )
        profile, _ = TailorProfile.objects.get_or_create(
            user=user,
            defaults={'shop_name': shop_name, 'shop_status': shop_status},
        )
        profile.shop_name = shop_name
        profile.shop_status = shop_status
        profile.is_featured = is_featured
        profile.is_express_delivery_enabled = is_express
        profile.avg_overall_satisfaction = avg_rating
        profile.rating_count = rating_count
        profile.save()

        TailorProfileReview.objects.update_or_create(
            profile=profile,
            defaults={'review_status': review_status},
        )

        Address.objects.create(
            user=user,
            address='Test Address',
            street='Test Street',
            city='Riyadh',
            country='Saudi Arabia',
            latitude=latitude,
            longitude=longitude,
            address_tag='shop',
            is_default=True,
        )
        return user

    def test_invalid_section_returns_400(self):
        response = self.client.get('/api/customers/tailors/?section=invalid')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertIn('Invalid section', response.data['message'])

    def test_express_delivery_section_returns_only_express_tailors(self):
        response = self.client.get('/api/customers/tailors/?section=express_delivery')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = {item['user']['id'] for item in response.data['data']['results']}
        self.assertIn(self.featured_tailor.id, ids)
        self.assertIn(self.express_tailor.id, ids)
        self.assertNotIn(self.popular_tailor.id, ids)
        self.assertNotIn(self.new_tailor.id, ids)
        self.assertNotIn(self.inactive_tailor.id, ids)

    def test_featured_section_returns_only_featured_tailors(self):
        response = self.client.get('/api/customers/tailors/?section=featured')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = {item['user']['id'] for item in response.data['data']['results']}
        self.assertEqual(ids, {self.featured_tailor.id, self.far_tailor.id})

    def test_most_popular_section_orders_by_order_count(self):
        response = self.client.get('/api/customers/tailors/?section=most_popular')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [item['user']['id'] for item in response.data['data']['results']]
        self.assertEqual(ids[0], self.popular_tailor.id)

    def test_section_without_location_returns_national_list(self):
        response = self.client.get('/api/customers/tailors/?section=featured')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = {item['user']['id'] for item in response.data['data']['results']}
        self.assertIn(self.far_tailor.id, ids)

    def test_section_with_location_filters_like_home(self):
        response = self.client.get(
            '/api/customers/tailors/'
            f'?section=featured&lat={RIYADH_LAT}&lng={RIYADH_LNG}&radius=50'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = {item['user']['id'] for item in response.data['data']['results']}
        self.assertIn(self.featured_tailor.id, ids)
        self.assertNotIn(self.far_tailor.id, ids)

    def test_section_page_one_matches_home_preview_order(self):
        home_response = self.client.get(
            f'/api/customers/home/?lat={RIYADH_LAT}&lng={RIYADH_LNG}&radius=50'
        )
        list_response = self.client.get(
            '/api/customers/tailors/'
            f'?section=most_popular&lat={RIYADH_LAT}&lng={RIYADH_LNG}&radius=50&page_size=20'
        )

        self.assertEqual(home_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)

        home_ids = [item['id'] for item in home_response.data['data']['most_popular_tailors']]
        list_ids = [item['user']['id'] for item in list_response.data['data']['results']]
        self.assertEqual(home_ids, list_ids[:len(home_ids)])

    def test_pagination_shape(self):
        response = self.client.get('/api/customers/tailors/?section=new&page=1&page_size=2')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data['data']
        self.assertIn('count', data)
        self.assertIn('next', data)
        self.assertIn('previous', data)
        self.assertIn('results', data)
        self.assertLessEqual(len(data['results']), 2)

    def test_list_without_section_still_returns_all_active_tailors(self):
        response = self.client.get('/api/customers/tailors/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = {item['user']['id'] for item in response.data['data']['results']}
        self.assertIn(self.featured_tailor.id, ids)
        self.assertIn(self.express_tailor.id, ids)
        self.assertIn(self.popular_tailor.id, ids)
        self.assertIn(self.far_tailor.id, ids)
        self.assertNotIn(self.inactive_tailor.id, ids)

    def test_tailor_payload_includes_home_card_fields(self):
        response = self.client.get('/api/customers/tailors/?section=featured&page_size=1')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        tailor = response.data['data']['results'][0]
        self.assertIn('shop_name', tailor)
        self.assertIn('shop_image_url', tailor)
        self.assertIn('avg_overall_satisfaction', tailor)
        self.assertIn('rating_count', tailor)
        self.assertIn('address', tailor)
        self.assertIn('is_express', tailor)
        self.assertIn('express_delivery_days', tailor)
        self.assertIn('express_delivery_fee', tailor)
        self.assertIn('express_delivery_unit', tailor)
