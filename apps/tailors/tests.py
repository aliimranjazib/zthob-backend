from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from .models import TailorProfile, ServiceArea
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
