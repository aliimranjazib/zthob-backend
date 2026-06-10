from django.test import TestCase
from django.contrib.auth import get_user_model
from unittest.mock import patch
from rest_framework.test import APITestCase
from rest_framework import status
from .models import TailorProfile, ServiceArea, TailorEmployee
from apps.customers.models import Address
from .serializers import TailorProfileSubmissionSerializer

User = get_user_model()

class TailorProfileSubmissionSerializerTest(TestCase):
    """Test cases for TailorProfileSubmissionSerializer validation."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.service_area = ServiceArea.objects.create(
            name='Test City',
            is_active=True
        )
        self.profile = TailorProfile.objects.create(user=self.user)
    
    def test_required_fields_validation(self):
        """Test that required fields are properly validated."""
        # Test with only required fields (excluding shop_image for now)
        data = {
            'shop_name': 'Test Shop',
            'address': 'Test Address',
            'service_areas': self.service_area.id
        }
        serializer = TailorProfileSubmissionSerializer(self.profile, data=data)
        # Note: This will fail due to shop_image requirement, but we're testing the field requirements
        # The important thing is that contact_number and working_hours are not in the errors
        if not serializer.is_valid():
            errors = serializer.errors
            # Check that contact_number and working_hours are not in the errors
            self.assertNotIn('contact_number', errors)
            self.assertNotIn('working_hours', errors)
            # Only shop_image should be the issue
            self.assertIn('non_field_errors', errors)
            self.assertIn('shop_image is required', str(errors['non_field_errors']))
    
    def test_optional_fields_not_required(self):
        """Test that contact_number and working_hours are optional."""
        data = {
            'shop_name': 'Test Shop',
            'address': 'Test Address',
            'service_areas': self.service_area.id,
            # contact_number and working_hours are missing - should not cause field errors
        }
        serializer = TailorProfileSubmissionSerializer(self.profile, data=data)
        if not serializer.is_valid():
            errors = serializer.errors
            # Check that contact_number and working_hours are not in the errors
            self.assertNotIn('contact_number', errors)
            self.assertNotIn('working_hours', errors)
            # Only shop_image should be the issue
            self.assertIn('non_field_errors', errors)
            self.assertIn('shop_image is required', str(errors['non_field_errors']))
    
    def test_service_areas_required(self):
        """Test that service_areas is required."""
        data = {
            'shop_name': 'Test Shop',
            'address': 'Test Address',
            # service_areas is missing - should be invalid
        }
        serializer = TailorProfileSubmissionSerializer(self.profile, data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('service_areas', serializer.errors)
    
    def test_contact_number_optional(self):
        """Test that contact_number can be empty or null."""
        data = {
            'shop_name': 'Test Shop',
            'address': 'Test Address',
            'service_areas': self.service_area.id,
            'contact_number': ''  # Empty string should be valid
        }
        serializer = TailorProfileSubmissionSerializer(self.profile, data=data)
        if not serializer.is_valid():
            errors = serializer.errors
            # contact_number should not be in the errors
            self.assertNotIn('contact_number', errors)
            # Only shop_image should be the issue
            self.assertIn('non_field_errors', errors)
            self.assertIn('shop_image is required', str(errors['non_field_errors']))
    
    def test_working_hours_optional(self):
        """Test that working_hours can be null."""
        data = {
            'shop_name': 'Test Shop',
            'address': 'Test Address',
            'service_areas': self.service_area.id,
            'working_hours': None  # None should be valid
        }
        serializer = TailorProfileSubmissionSerializer(self.profile, data=data)
        if not serializer.is_valid():
            errors = serializer.errors
            # working_hours should not be in the errors
            self.assertNotIn('working_hours', errors)
            # Only shop_image should be the issue
            self.assertIn('non_field_errors', errors)
            self.assertIn('shop_image is required', str(errors['non_field_errors']))


class TailorHomeEmployeePermissionTest(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username='owner',
            password='testpass123',
            role='TAILOR',
            phone='0500000201'
        )
        self.owner_profile = TailorProfile.objects.create(
            user=self.owner,
            shop_name='Owner Shop'
        )
        self.employee_user = User.objects.create_user(
            username='employee',
            password='testpass123',
            role='TAILOR',
            phone='0500000202'
        )
        self.employee = TailorEmployee.objects.create(
            tailor=self.owner_profile,
            user=self.employee_user,
            roles=['manager'],
            is_active=True
        )

    @patch('apps.tailors.views.home.TailorHomeService.get_dashboard_data')
    def test_employee_without_order_permission_cannot_access_home_api(self, mock_dashboard_data):
        self.client.force_authenticate(user=self.employee_user)

        response = self.client.get('/api/tailors/home/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        mock_dashboard_data.assert_not_called()

    @patch('apps.tailors.views.home.TailorHomeService.get_dashboard_data')
    def test_employee_with_order_permission_can_access_home_api(self, mock_dashboard_data):
        self.employee.can_manage_orders = True
        self.employee.save(update_fields=['can_manage_orders'])
        mock_dashboard_data.return_value = {
            'financials': {
                'today_revenue': '0.00',
                'today_label': "Today's Revenue",
                'weekly_revenue': '0.00',
                'weekly_label': 'Weekly Revenue',
            },
            'urgent_alerts': [],
            'delivery_orders': [],
            'shop_orders': [],
            'express_orders': {
                'total_count': 0,
                'filter_params': {},
                'items': [],
            },
            'recent_orders': [],
        }

        self.client.force_authenticate(user=self.employee_user)

        response = self.client.get('/api/tailors/home/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_dashboard_data.assert_called_once_with(self.owner, language='ar')

    def test_employee_with_stub_tailor_profile_still_uses_owner_shop_profile(self):
        TailorProfile.objects.create(user=self.employee_user, shop_name='')
        self.employee.can_manage_orders = True
        self.employee.can_manage_catalog = True
        self.employee.save(update_fields=['can_manage_orders', 'can_manage_catalog'])

        self.client.force_authenticate(user=self.employee_user)

        profile_response = self.client.get('/api/tailors/profile/')
        fabrics_response = self.client.get('/api/tailors/fabrics/')

        self.assertEqual(profile_response.status_code, status.HTTP_200_OK)
        self.assertEqual(profile_response.data['data']['id'], self.owner_profile.id)
        self.assertEqual(fabrics_response.status_code, status.HTTP_200_OK)

    def test_employee_without_shop_profile_permission_cannot_access_profile(self):
        self.client.force_authenticate(user=self.employee_user)

        response = self.client.get('/api/tailors/profile/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_employee_with_shop_profile_permission_can_access_profile(self):
        self.employee.can_manage_shop_profile = True
        self.employee.save(update_fields=['can_manage_shop_profile'])

        self.client.force_authenticate(user=self.employee_user)

        response = self.client.get('/api/tailors/profile/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['id'], self.owner_profile.id)

    def test_employee_with_shop_address_permission_reads_owner_address(self):
        Address.objects.create(
            user=self.owner,
            address='Owner Shop Address',
            street='Owner Shop Address',
            city='Riyadh',
            country='Saudi Arabia',
            is_default=True,
            address_tag='work',
        )
        self.employee.can_manage_shop_address = True
        self.employee.save(update_fields=['can_manage_shop_address'])

        self.client.force_authenticate(user=self.employee_user)

        response = self.client.get('/api/tailors/address/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['address'], 'Owner Shop Address')
