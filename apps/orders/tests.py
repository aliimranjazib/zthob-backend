from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal
from rest_framework.test import APIClient
from rest_framework import status
from apps.orders.models import Order, OrderItem, OrderStatusHistory
from apps.orders.services import OrderCalculationService
from apps.orders.serializers import OrderCreateSerializer
from apps.tailors.models import TailorProfile, Fabric, FabricCategory, FabricType
from apps.customers.models import Address

User = get_user_model()


class OrderCalculationServiceTest(TestCase):
    """Test OrderCalculationService methods"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username=f'testuser_{id(self)}',
            email=f'test_{id(self)}@example.com',
            password='testpass123',
            role='TAILOR'
        )
        self.tailor_profile, _ = TailorProfile.objects.get_or_create(
            user=self.user,
            defaults={
                'shop_name': 'Test Tailor Shop',
                'shop_status': True
            }
        )
        self.fabric_category = FabricCategory.objects.create(
            name='Fabric',
            slug='fabric'
        )
        self.fabric = Fabric.objects.create(
            tailor=self.tailor_profile,
            name='Test Fabric',
            price=Decimal('100.00'),
            stock=10,
            is_active=True,
            category=self.fabric_category
        )
    
    def test_calculate_subtotal_with_valid_items(self):
        """Test subtotal calculation with valid items"""
        items_data = [
            {'fabric': self.fabric, 'quantity': 2},
            {'fabric': self.fabric, 'quantity': 3}
        ]
        subtotal = OrderCalculationService.calculate_subtotal(items_data)
        expected = Decimal('100.00') * 2 + Decimal('100.00') * 3
        self.assertEqual(subtotal, expected)
        self.assertEqual(subtotal, Decimal('500.00'))
    
    def test_calculate_subtotal_with_empty_items(self):
        """Test subtotal calculation with empty items list"""
        items_data = []
        subtotal = OrderCalculationService.calculate_subtotal(items_data)
        self.assertEqual(subtotal, Decimal('0.00'))
    
    def test_calculate_subtotal_with_single_item(self):
        """Test subtotal calculation with single item"""
        items_data = [{'fabric': self.fabric, 'quantity': 1}]
        subtotal = OrderCalculationService.calculate_subtotal(items_data)
        self.assertEqual(subtotal, Decimal('100.00'))
    
    def test_calculate_tax_with_default_rate(self):
        """Test tax calculation with default 15% rate"""
        subtotal = Decimal('100.00')
        tax_amount = OrderCalculationService.calculate_tax(subtotal)
        expected = Decimal('100.00') * Decimal('0.15')
        self.assertEqual(tax_amount, expected)
        self.assertEqual(tax_amount, Decimal('15.00'))
    
    def test_calculate_tax_with_custom_rate(self):
        """Test tax calculation with custom rate"""
        subtotal = Decimal('100.00')
        tax_amount = OrderCalculationService.calculate_tax(subtotal, Decimal('0.20'))
        self.assertEqual(tax_amount, Decimal('20.00'))
    
    def test_calculate_tax_with_zero_subtotal(self):
        """Test tax calculation with zero subtotal"""
        subtotal = Decimal('0.00')
        tax_amount = OrderCalculationService.calculate_tax(subtotal)
        self.assertEqual(tax_amount, Decimal('0.00'))
    
    def test_calculate_tax_with_negative_subtotal(self):
        """Test tax calculation with negative subtotal (edge case)"""
        subtotal = Decimal('-10.00')
        tax_amount = OrderCalculationService.calculate_tax(subtotal)
        self.assertEqual(tax_amount, Decimal('0.00'))
    
    def test_calculate_delivery_fee_below_threshold(self):
        """Test delivery fee when subtotal is below 500"""
        subtotal = Decimal('499.99')
        delivery_fee = OrderCalculationService.calculate_delivery_fee(subtotal)
        self.assertEqual(delivery_fee, Decimal('25.00'))
    
    def test_calculate_delivery_fee_at_threshold(self):
        """Test delivery fee when subtotal equals 500"""
        subtotal = Decimal('500.00')
        delivery_fee = OrderCalculationService.calculate_delivery_fee(subtotal)
        self.assertEqual(delivery_fee, Decimal('0.00'))
    
    def test_calculate_delivery_fee_above_threshold(self):
        """Test delivery fee when subtotal is above 500"""
        subtotal = Decimal('500.01')
        delivery_fee = OrderCalculationService.calculate_delivery_fee(subtotal)
        self.assertEqual(delivery_fee, Decimal('0.00'))
    
    def test_calculate_all_totals_complete(self):
        """Test complete totals calculation"""
        items_data = [
            {'fabric': self.fabric, 'quantity': 2}
        ]
        totals = OrderCalculationService.calculate_all_totals(items_data)
        
        self.assertIn('subtotal', totals)
        self.assertIn('tax_amount', totals)
        self.assertIn('delivery_fee', totals)
        self.assertIn('total_amount', totals)
        
        # Verify calculations
        self.assertEqual(totals['subtotal'], Decimal('200.00'))
        self.assertEqual(totals['tax_amount'], Decimal('30.00'))  # 15% of 200
        self.assertEqual(totals['delivery_fee'], Decimal('25.00'))  # Below threshold
        self.assertEqual(totals['total_amount'], Decimal('255.00'))  # 200 + 30 + 25
    
    def test_calculate_all_totals_free_delivery(self):
        """Test totals calculation with free delivery (above threshold)"""
        items_data = [
            {'fabric': self.fabric, 'quantity': 5}  # 5 * 100 = 500
        ]
        totals = OrderCalculationService.calculate_all_totals(items_data)
        
        self.assertEqual(totals['subtotal'], Decimal('500.00'))
        self.assertEqual(totals['tax_amount'], Decimal('75.00'))  # 15% of 500
        self.assertEqual(totals['delivery_fee'], Decimal('0.00'))  # Free delivery
        self.assertEqual(totals['total_amount'], Decimal('575.00'))  # 500 + 75 + 0


class OrderCreateSerializerTest(TestCase):
    """Test OrderCreateSerializer"""
    
    def setUp(self):
        """Set up test data"""
        # Create customer
        self.customer = User.objects.create_user(
            username=f'customer_ser_{id(self)}',
            email=f'customer_ser_{id(self)}@example.com',
            password='testpass123',
            role='USER'
        )
        
        # Create tailor
        self.tailor_user = User.objects.create_user(
            username=f'tailor_ser_{id(self)}',
            email=f'tailor_ser_{id(self)}@example.com',
            password='testpass123',
            role='TAILOR'
        )
        self.tailor_profile, _ = TailorProfile.objects.get_or_create(
            user=self.tailor_user,
            defaults={
                'shop_name': 'Test Tailor Shop',
                'shop_status': True
            }
        )
        
        # Create fabric category
        self.fabric_category = FabricCategory.objects.create(
            name='Fabric',
            slug='fabric'
        )
        
        # Create fabric
        self.fabric = Fabric.objects.create(
            tailor=self.tailor_profile,
            name='Test Fabric',
            price=Decimal('100.00'),
            stock=10,
            is_active=True,
            category=self.fabric_category
        )
        
        # Create delivery address
        self.address = Address.objects.create(
            user=self.customer,
            street='123 Test St',
            city='Riyadh',
            country='Saudi Arabia'
        )
    
    def test_validate_items_empty_list(self):
        """Test validation with empty items list"""
        serializer = OrderCreateSerializer()
        with self.assertRaises(Exception) as context:
            serializer.validate_items([])
        self.assertIn('at least one item', str(context.exception))
    
    def test_validate_items_insufficient_stock(self):
        """Test that insufficient stock is caught during order creation (not in validate_items)"""
        # Note: Stock validation happens in create() method, not validate_items()
        # This test verifies that validate_items() passes but create() fails
        items_data = [
            {'fabric': self.fabric.id, 'quantity': 15}  # More than available stock (10)
        ]
        
        data = {
            'customer': self.customer.id,
            'tailor': self.tailor_user.id,
            'order_type': 'fabric_only',
            'payment_method': 'cod',
            'delivery_address': self.address.id,
            'items': items_data
        }
        
        mock_request = type('obj', (object,), {'user': self.customer})()
        serializer = OrderCreateSerializer(data=data, context={'request': mock_request, 'tailor': self.tailor_user})
        # validate_items should pass (doesn't check stock)
        self.assertTrue(serializer.is_valid())
        
        # But create() should fail due to insufficient stock
        from rest_framework import serializers as drf_serializers
        with self.assertRaises(drf_serializers.ValidationError) as context:
            serializer.save()
        self.assertIn('Insufficient stock', str(context.exception))
    
    def test_validate_items_inactive_fabric(self):
        """Test validation with inactive fabric"""
        self.fabric.is_active = False
        self.fabric.save()
        
        items_data = [
            {'fabric': self.fabric.id, 'quantity': 2}
        ]
        
        serializer = OrderCreateSerializer(context={'tailor': self.tailor_user})
        with self.assertRaises(Exception) as context:
            serializer.validate_items(items_data)
        self.assertIn('not available for purchase', str(context.exception))
    
    def test_validate_items_zero_quantity(self):
        """Test validation with zero quantity"""
        items_data = [
            {'fabric': self.fabric.id, 'quantity': 0}
        ]
        
        serializer = OrderCreateSerializer(context={'tailor': self.tailor_user})
        with self.assertRaises(Exception) as context:
            serializer.validate_items(items_data)
        self.assertIn('greater than 0', str(context.exception))
    
    def test_validate_tailor_not_tailor_role(self):
        """Test validation with user who is not a tailor"""
        serializer = OrderCreateSerializer()
        with self.assertRaises(Exception) as context:
            serializer.validate_tailor(self.customer)
        self.assertIn('not a tailor', str(context.exception))
    
    def test_validate_tailor_not_accepting_orders(self):
        """Test validation with tailor not accepting orders"""
        self.tailor_profile.shop_status = False
        self.tailor_profile.save()
        
        # Refresh from DB to ensure we have the latest data
        self.tailor_user.refresh_from_db()
        self.tailor_profile.refresh_from_db()
        
        serializer = OrderCreateSerializer()
        from rest_framework import serializers
        with self.assertRaises(serializers.ValidationError) as context:
            serializer.validate_tailor(self.tailor_user)
        self.assertIn('not accepting orders', str(context.exception))


class OrderCreateIntegrationTest(TestCase):
    """Integration tests for order creation"""
    
    def setUp(self):
        """Set up test data"""
        # Create customer
        self.customer = User.objects.create_user(
            username=f'customer_int_{id(self)}',
            email=f'customer_int_{id(self)}@example.com',
            password='testpass123',
            role='USER'
        )
        
        # Create tailor
        self.tailor_user = User.objects.create_user(
            username=f'tailor_int_{id(self)}',
            email=f'tailor_int_{id(self)}@example.com',
            password='testpass123',
            role='TAILOR'
        )
        self.tailor_profile, _ = TailorProfile.objects.get_or_create(
            user=self.tailor_user,
            defaults={
                'shop_name': 'Test Tailor Shop',
                'shop_status': True
            }
        )
        
        # Create fabric category
        self.fabric_category = FabricCategory.objects.create(
            name='Fabric',
            slug='fabric'
        )
        
        # Create fabric
        self.fabric = Fabric.objects.create(
            tailor=self.tailor_profile,
            name='Test Fabric',
            price=Decimal('100.00'),
            stock=10,
            is_active=True,
            category=self.fabric_category
        )
        
        # Create delivery address
        self.address = Address.objects.create(
            user=self.customer,
            street='123 Test St',
            city='Riyadh',
            country='Saudi Arabia'
        )
        
        # Create API client
        self.client = APIClient()
        self.client.force_authenticate(user=self.customer)
    
    def test_create_order_success(self):
        """Test successful order creation"""
        initial_stock = self.fabric.stock
        
        data = {
            'customer': self.customer.id,
            'tailor': self.tailor_user.id,
            'order_type': 'fabric_only',
            'payment_method': 'cod',
            'delivery_address': self.address.id,
            'items': [
                {
                    'fabric': self.fabric.id,
                    'quantity': 2
                }
            ]
        }
        
        mock_request = type('obj', (object,), {'user': self.customer})()
        serializer = OrderCreateSerializer(data=data, context={'request': mock_request})
        self.assertTrue(serializer.is_valid(), f"Serializer errors: {serializer.errors}")
        
        order = serializer.save()
        
        # Verify order was created
        self.assertIsNotNone(order)
        self.assertIsNotNone(order.order_number)
        self.assertEqual(order.status, 'pending')
        self.assertEqual(order.payment_status, 'pending')
        self.assertEqual(order.customer, self.customer)
        self.assertEqual(order.tailor, self.tailor_user)
        
        # Verify calculations
        self.assertEqual(order.subtotal, Decimal('200.00'))  # 2 * 100
        self.assertEqual(order.tax_amount, Decimal('30.00'))  # 15% of 200
        self.assertEqual(order.delivery_fee, Decimal('25.00'))  # Below threshold
        self.assertEqual(order.total_amount, Decimal('255.00'))  # 200 + 30 + 25
        
        # Verify stock was deducted
        self.fabric.refresh_from_db()
        self.assertEqual(self.fabric.stock, initial_stock - 2)
        
        # Verify order items were created
        order_items = order.order_items.all()
        self.assertEqual(order_items.count(), 1)
        self.assertEqual(order_items[0].fabric, self.fabric)
        self.assertEqual(order_items[0].quantity, 2)
        self.assertEqual(order_items[0].unit_price, Decimal('100.00'))
        
        # Verify status history was created
        history = OrderStatusHistory.objects.filter(order=order)
        self.assertEqual(history.count(), 1)
        self.assertEqual(history[0].status, 'pending')
    
    def test_create_order_stock_deduction(self):
        """Test that stock is correctly deducted"""
        initial_stock = self.fabric.stock
        
        data = {
            'customer': self.customer.id,
            'tailor': self.tailor_user.id,
            'order_type': 'fabric_only',
            'payment_method': 'cod',
            'delivery_address': self.address.id,
            'items': [
                {
                    'fabric': self.fabric.id,
                    'quantity': 3
                }
            ]
        }
        
        mock_request = type('obj', (object,), {'user': self.customer})()
        serializer = OrderCreateSerializer(data=data, context={'request': mock_request})
        serializer.is_valid()
        order = serializer.save()
        
        # Verify stock was deducted
        self.fabric.refresh_from_db()
        self.assertEqual(self.fabric.stock, initial_stock - 3)
    
    def test_create_order_price_snapshot(self):
        """Test that order uses price snapshot at creation time"""
        original_price = self.fabric.price
        
        data = {
            'customer': self.customer.id,
            'tailor': self.tailor_user.id,
            'order_type': 'fabric_only',
            'payment_method': 'cod',
            'delivery_address': self.address.id,
            'items': [
                {
                    'fabric': self.fabric.id,
                    'quantity': 1
                }
            ]
        }
        
        mock_request = type('obj', (object,), {'user': self.customer})()
        serializer = OrderCreateSerializer(data=data, context={'request': mock_request})
        serializer.is_valid()
        order = serializer.save()
        
        # Change fabric price after order creation
        self.fabric.price = Decimal('200.00')
        self.fabric.save()
        
        # Verify order still has original price
        order_item = order.order_items.first()
        self.assertEqual(order_item.unit_price, original_price)
        self.assertEqual(order_item.unit_price, Decimal('100.00'))
        
        # Verify order total is still based on original price
        self.assertEqual(order.subtotal, Decimal('100.00'))
    
    def test_create_order_free_delivery_threshold(self):
        """Test free delivery when order exceeds threshold"""
        # Create fabric with price that makes order >= 500
        data = {
            'customer': self.customer.id,
            'tailor': self.tailor_user.id,
            'order_type': 'fabric_only',
            'payment_method': 'cod',
            'delivery_address': self.address.id,
            'items': [
                {
                    'fabric': self.fabric.id,
                    'quantity': 5  # 5 * 100 = 500
                }
            ]
        }
        
        mock_request = type('obj', (object,), {'user': self.customer})()
        serializer = OrderCreateSerializer(data=data, context={'request': mock_request})
        serializer.is_valid()
        order = serializer.save()
        
        # Verify free delivery
        self.assertEqual(order.subtotal, Decimal('500.00'))
        self.assertEqual(order.delivery_fee, Decimal('0.00'))
        self.assertEqual(order.total_amount, Decimal('575.00'))  # 500 + 75 (tax) + 0 (delivery)


class OrderPaymentStatusUpdateViewTest(TestCase):
    """Comprehensive tests for OrderPaymentStatusUpdateView"""
    
    def setUp(self):
        """Set up test data"""
        # Create customer
        self.customer = User.objects.create_user(
            username=f'customer_pay_{id(self)}',
            email=f'customer_pay_{id(self)}@example.com',
            password='testpass123',
            role='USER'
        )
        
        # Create another customer (for permission tests)
        self.other_customer = User.objects.create_user(
            username=f'other_customer_{id(self)}',
            email=f'other_customer_{id(self)}@example.com',
            password='testpass123',
            role='USER'
        )
        
        # Create tailor
        self.tailor_user = User.objects.create_user(
            username=f'tailor_pay_{id(self)}',
            email=f'tailor_pay_{id(self)}@example.com',
            password='testpass123',
            role='TAILOR'
        )
        self.tailor_profile, _ = TailorProfile.objects.get_or_create(
            user=self.tailor_user,
            defaults={
                'shop_name': 'Test Tailor Shop',
                'shop_status': True
            }
        )
        
        # Create admin
        self.admin_user = User.objects.create_user(
            username=f'admin_pay_{id(self)}',
            email=f'admin_pay_{id(self)}@example.com',
            password='testpass123',
            role='ADMIN'
        )
        
        # Create fabric category
        self.fabric_category = FabricCategory.objects.create(
            name='Fabric',
            slug='fabric'
        )
        
        # Create fabric
        self.fabric = Fabric.objects.create(
            tailor=self.tailor_profile,
            name='Test Fabric',
            price=Decimal('100.00'),
            stock=10,
            is_active=True,
            category=self.fabric_category
        )
        
        # Create delivery address
        self.address = Address.objects.create(
            user=self.customer,
            street='123 Test St',
            city='Riyadh',
            country='Saudi Arabia'
        )
        
        # Create an order with pending payment status
        self.order = Order.objects.create(
            customer=self.customer,
            tailor=self.tailor_user,
            order_type='fabric_only',
            payment_method='cod',
            delivery_address=self.address,
            status='pending',
            payment_status='pending',
            subtotal=Decimal('100.00'),
            tax_amount=Decimal('15.00'),
            delivery_fee=Decimal('25.00'),
            total_amount=Decimal('140.00')
        )
        
        # Create order item
        OrderItem.objects.create(
            order=self.order,
            fabric=self.fabric,
            quantity=1,
            unit_price=Decimal('100.00')
        )
        
        # Create API clients
        self.customer_client = APIClient()
        self.customer_client.force_authenticate(user=self.customer)
        
        self.other_customer_client = APIClient()
        self.other_customer_client.force_authenticate(user=self.other_customer)
        
        self.tailor_client = APIClient()
        self.tailor_client.force_authenticate(user=self.tailor_user)
        
        self.admin_client = APIClient()
        self.admin_client.force_authenticate(user=self.admin_user)
        
        self.unauth_client = APIClient()
    
    # ========== PERMISSION TESTS ==========
    
    def test_customer_can_update_own_order_payment_status(self):
        """Test that customer can update their own order's payment status"""
        url = f'/api/orders/{self.order.id}/payment-status/'
        data = {'payment_status': 'paid'}
        
        response = self.customer_client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get('success'))
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, 'paid')
    
    def test_customer_cannot_update_other_customer_order(self):
        """Test that customer cannot update another customer's order payment status"""
        url = f'/api/orders/{self.order.id}/payment-status/'
        data = {'payment_status': 'paid'}
        
        response = self.other_customer_client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(response.data.get('success'))
        self.assertIn('own orders', response.data.get('message', ''))
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, 'pending')  # Should remain unchanged
    
    def test_admin_can_update_any_order_payment_status(self):
        """Test that admin can update any order's payment status"""
        url = f'/api/orders/{self.order.id}/payment-status/'
        data = {'payment_status': 'paid'}
        
        response = self.admin_client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get('success'))
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, 'paid')
    
    def test_tailor_cannot_update_payment_status(self):
        """Test that tailor cannot update payment status"""
        url = f'/api/orders/{self.order.id}/payment-status/'
        data = {'payment_status': 'paid'}
        
        response = self.tailor_client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(response.data.get('success'))
        self.assertIn('Only customers and admins', response.data.get('message', ''))
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, 'pending')  # Should remain unchanged
    
    def test_unauthenticated_user_cannot_update_payment_status(self):
        """Test that unauthenticated user cannot update payment status"""
        url = f'/api/orders/{self.order.id}/payment-status/'
        data = {'payment_status': 'paid'}
        
        response = self.unauth_client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, 'pending')  # Should remain unchanged
    
    # ========== VALIDATION TESTS ==========
    
    def test_missing_payment_status_field(self):
        """Test that missing payment_status field returns 400"""
        url = f'/api/orders/{self.order.id}/payment-status/'
        data = {}
        
        response = self.customer_client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data.get('success'))
        self.assertIn('payment_status', str(response.data))
    
    def test_invalid_payment_status_value(self):
        """Test that invalid payment_status value returns 400"""
        url = f'/api/orders/{self.order.id}/payment-status/'
        data = {'payment_status': 'invalid_status'}
        
        response = self.customer_client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data.get('success'))
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, 'pending')  # Should remain unchanged
    
    def test_valid_payment_status_values(self):
        """Test that all valid payment status values are accepted"""
        valid_statuses = ['pending', 'paid', 'refunded']
        
        for payment_status in valid_statuses:
            # Reset order to pending for each test
            self.order.payment_status = 'pending'
            self.order.save()
            
            url = f'/api/orders/{self.order.id}/payment-status/'
            data = {'payment_status': payment_status}
            
            response = self.customer_client.patch(url, data, format='json')
            
            self.assertEqual(response.status_code, status.HTTP_200_OK, 
                           f"Failed for status: {payment_status}")
            self.order.refresh_from_db()
            self.assertEqual(self.order.payment_status, payment_status)
    
    def test_order_not_found(self):
        """Test that non-existent order returns 404"""
        url = '/api/orders/99999/payment-status/'
        data = {'payment_status': 'paid'}
        
        response = self.customer_client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    # ========== BUSINESS LOGIC TESTS ==========
    
    def test_cannot_change_refunded_order_payment_status(self):
        """Test that refunded order's payment status cannot be changed"""
        self.order.payment_status = 'refunded'
        self.order.save()
        
        url = f'/api/orders/{self.order.id}/payment-status/'
        data = {'payment_status': 'paid'}
        
        response = self.customer_client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data.get('success'))
        self.assertIn('refunded', response.data.get('message', '').lower())
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, 'refunded')  # Should remain unchanged
    
    def test_cannot_change_from_paid_to_pending(self):
        """Test that payment status cannot be changed from paid to pending"""
        self.order.payment_status = 'paid'
        self.order.save()
        
        url = f'/api/orders/{self.order.id}/payment-status/'
        data = {'payment_status': 'pending'}
        
        response = self.customer_client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data.get('success'))
        self.assertIn('paid to pending', response.data.get('message', '').lower())
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, 'paid')  # Should remain unchanged
    
    def test_can_change_from_pending_to_paid(self):
        """Test that payment status can be changed from pending to paid"""
        self.order.payment_status = 'pending'
        self.order.save()
        
        url = f'/api/orders/{self.order.id}/payment-status/'
        data = {'payment_status': 'paid'}
        
        response = self.customer_client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get('success'))
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, 'paid')
    
    def test_can_change_from_pending_to_refunded(self):
        """Test that payment status can be changed from pending to refunded"""
        self.order.payment_status = 'pending'
        self.order.save()
        
        url = f'/api/orders/{self.order.id}/payment-status/'
        data = {'payment_status': 'refunded'}
        
        response = self.customer_client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get('success'))
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, 'refunded')
    
    def test_can_change_from_paid_to_refunded(self):
        """Test that payment status can be changed from paid to refunded"""
        self.order.payment_status = 'paid'
        self.order.save()
        
        url = f'/api/orders/{self.order.id}/payment-status/'
        data = {'payment_status': 'refunded'}
        
        response = self.customer_client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get('success'))
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, 'refunded')
    
    def test_same_payment_status_no_change(self):
        """Test that setting the same payment status still succeeds"""
        self.order.payment_status = 'paid'
        self.order.save()
        
        url = f'/api/orders/{self.order.id}/payment-status/'
        data = {'payment_status': 'paid'}
        
        response = self.customer_client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get('success'))
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, 'paid')
    
    # ========== SUCCESS CASE TESTS ==========
    
    def test_successful_payment_status_update_creates_history(self):
        """Test that successful payment status update creates history entry"""
        initial_history_count = OrderStatusHistory.objects.filter(order=self.order).count()
        
        url = f'/api/orders/{self.order.id}/payment-status/'
        data = {'payment_status': 'paid'}
        
        response = self.customer_client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify history was created
        history_count = OrderStatusHistory.objects.filter(order=self.order).count()
        self.assertEqual(history_count, initial_history_count + 1)
        
        # Verify history entry details
        latest_history = OrderStatusHistory.objects.filter(order=self.order).latest('created_at')
        self.assertEqual(latest_history.changed_by, self.customer)
        self.assertIn('Payment status changed', latest_history.notes)
        self.assertIn('pending', latest_history.notes)
        self.assertIn('paid', latest_history.notes)
    
    def test_successful_payment_status_update_returns_order_data(self):
        """Test that successful update returns complete order data"""
        url = f'/api/orders/{self.order.id}/payment-status/'
        data = {'payment_status': 'paid'}
        
        response = self.customer_client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get('success'))
        self.assertIn('data', response.data)
        
        order_data = response.data['data']
        self.assertEqual(order_data['id'], self.order.id)
        self.assertEqual(order_data['payment_status'], 'paid')
        self.assertIn('order_number', order_data)
        self.assertIn('total_amount', order_data)
    
    def test_payment_status_update_preserves_other_order_fields(self):
        """Test that payment status update doesn't affect other order fields"""
        original_status = self.order.status
        original_total = self.order.total_amount
        
        url = f'/api/orders/{self.order.id}/payment-status/'
        data = {'payment_status': 'paid'}
        
        response = self.customer_client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        
        # Verify other fields are unchanged
        self.assertEqual(self.order.status, original_status)
        self.assertEqual(self.order.total_amount, original_total)
        self.assertEqual(self.order.customer, self.customer)
        self.assertEqual(self.order.tailor, self.tailor_user)
    
    # ========== EDGE CASE TESTS ==========
    
    def test_payment_status_update_with_empty_string(self):
        """Test that empty string payment_status is rejected"""
        url = f'/api/orders/{self.order.id}/payment-status/'
        data = {'payment_status': ''}
        
        response = self.customer_client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, 'pending')
    
    def test_payment_status_update_with_null_value(self):
        """Test that null payment_status is rejected"""
        url = f'/api/orders/{self.order.id}/payment-status/'
        data = {'payment_status': None}
        
        response = self.customer_client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, 'pending')
    
    def test_payment_status_update_with_numeric_value(self):
        """Test that numeric payment_status is rejected"""
        url = f'/api/orders/{self.order.id}/payment-status/'
        data = {'payment_status': 123}
        
        response = self.customer_client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, 'pending')
    
    def test_multiple_rapid_payment_status_updates(self):
        """Test handling of multiple rapid payment status updates"""
        url = f'/api/orders/{self.order.id}/payment-status/'
        
        # First update: pending -> paid
        data1 = {'payment_status': 'paid'}
        response1 = self.customer_client.patch(url, data1, format='json')
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, 'paid')
        
        # Second update: paid -> refunded
        data2 = {'payment_status': 'refunded'}
        response2 = self.customer_client.patch(url, data2, format='json')
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, 'refunded')
        
        # Third update: refunded -> paid (should fail)
        data3 = {'payment_status': 'paid'}
        response3 = self.customer_client.patch(url, data3, format='json')
        self.assertEqual(response3.status_code, status.HTTP_400_BAD_REQUEST)
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, 'refunded')  # Should remain refunded
