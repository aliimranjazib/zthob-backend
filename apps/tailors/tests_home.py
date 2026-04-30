from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.orders.models import Order
from apps.tailors.models import TailorProfile
from decimal import Decimal

User = get_user_model()

class TailorHomeAPITest(APITestCase):
    def setUp(self):
        # Create a Tailor
        self.tailor_user = User.objects.create_user(
            username='tailor_test', 
            password='password123',
            role='TAILOR'
        )
        self.tailor_profile = self.tailor_user.tailor_profile
        self.tailor_profile.shop_name = 'Test Shop'
        self.tailor_profile.shop_status = True
        self.tailor_profile.save()
        
        # Create a Customer
        self.customer_user = User.objects.create_user(
            username='customer_test',
            password='password123',
            role='USER'
        )
        
        self.client.force_authenticate(user=self.tailor_user)
        self.url = reverse('tailor-home')
        self.today = timezone.now().date()

    def test_get_home_data_two_sections(self):
        # Create Delivery Order
        Order.objects.create(
            customer=self.customer_user,
            tailor=self.tailor_user,
            service_mode='home_delivery',
            tailor_status='none',
            payment_status='paid'
        )
        
        # Create Shop Order
        Order.objects.create(
            customer=self.customer_user,
            tailor=self.tailor_user,
            service_mode='walk_in',
            tailor_status='none',
            payment_status='paid'
        )
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data['data']
        
        # Verify Delivery Section
        del_new = next(b for b in data['delivery_orders'] if b['label'] == 'New Requests')
        self.assertEqual(del_new['count'], 1)
        
        # Verify Shop Section
        shop_new = next(b for b in data['shop_orders'] if b['label'] == 'New Shop Orders')
        self.assertEqual(shop_new['count'], 1)

    def test_in_stitching_filter(self):
        # Create order in stitching
        Order.objects.create(
            customer=self.customer_user,
            tailor=self.tailor_user,
            service_mode='home_delivery',
            tailor_status='stitching_started',
            payment_status='paid'
        )
        
        list_url = reverse('orders:tailor-orders')
        response = self.client.get(f"{list_url}?in_stitching=true")
        self.assertEqual(len(response.data['data']), 1)

    def test_unauthorized_access(self):
        self.client.force_authenticate(user=self.customer_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
