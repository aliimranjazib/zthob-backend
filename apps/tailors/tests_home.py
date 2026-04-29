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
        # Profile is created automatically by signal
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

    def test_get_home_data_new_structure(self):
        # 1. Create some orders
        # Overdue order
        Order.objects.create(
            customer=self.customer_user,
            tailor=self.tailor_user,
            status='pending',
            payment_status='paid',
            estimated_delivery_date=self.today - timezone.timedelta(days=1),
            subtotal=Decimal('100.00'),
            total_amount=Decimal('100.00')
        )
        
        # Due today + stitching started
        Order.objects.create(
            customer=self.customer_user,
            tailor=self.tailor_user,
            status='in_progress',
            tailor_status='stitching_started',
            payment_status='paid',
            estimated_delivery_date=self.today,
            subtotal=Decimal('150.00'),
            total_amount=Decimal('150.00')
        )
        
        # Express order (paid)
        Order.objects.create(
            customer=self.customer_user,
            tailor=self.tailor_user,
            status='pending',
            payment_status='paid',
            is_express=True,
            subtotal=Decimal('120.00'),
            total_amount=Decimal('120.00')
        )

        # Completed order today (to verify revenue)
        Order.objects.create(
            customer=self.customer_user,
            tailor=self.tailor_user,
            status='delivered',
            payment_status='paid',
            subtotal=Decimal('200.00'),
            total_amount=Decimal('200.00')
        )
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data['data']
        
        # Verify Financials
        self.assertEqual(float(data['financials']['today_revenue']), 200.0)
        
        # Verify Urgent Alerts
        overdue_alert = next(a for a in data['urgent_alerts'] if a['type'] == 'overdue')
        self.assertEqual(overdue_alert['count'], 1)
        self.assertEqual(overdue_alert['filter_params']['is_overdue'], 'true')
        
        due_today_alert = next(a for a in data['urgent_alerts'] if a['type'] == 'due_today')
        self.assertEqual(due_today_alert['count'], 1)
        self.assertEqual(due_today_alert['filter_params']['delivery_due'], 'today')
        
        # Verify Task Summary
        needs_acc = next(t for t in data['task_summary'] if t['label'] == 'Needs Acceptance')
        self.assertEqual(needs_acc['count'], 2) # Both pending orders
        
        # Verify Express
        self.assertEqual(data['express_orders']['total_count'], 1)
        self.assertEqual(len(data['express_orders']['items']), 1)

    def test_order_list_new_filters(self):
        # Create overdue order
        Order.objects.create(
            customer=self.customer_user,
            tailor=self.tailor_user,
            status='pending',
            payment_status='paid',
            estimated_delivery_date=self.today - timezone.timedelta(days=2)
        )
        # Create normal order
        Order.objects.create(
            customer=self.customer_user,
            tailor=self.tailor_user,
            status='pending',
            payment_status='paid',
            estimated_delivery_date=self.today + timezone.timedelta(days=2)
        )
        
        list_url = reverse('orders:tailor-orders')
        
        # Test overdue filter
        response = self.client.get(f"{list_url}?is_overdue=true")
        self.assertEqual(len(response.data['data']), 1)
        
        # Test delivery_due filter
        # Create one due today
        Order.objects.create(
            customer=self.customer_user,
            tailor=self.tailor_user,
            status='pending',
            payment_status='paid',
            estimated_delivery_date=self.today
        )
        response = self.client.get(f"{list_url}?delivery_due=today")
        self.assertEqual(len(response.data['data']), 1)

    def test_unauthorized_access(self):
        self.client.force_authenticate(user=self.customer_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
