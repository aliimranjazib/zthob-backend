from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.customization.models import CustomStyle, CustomStyleCategory, UserStylePreset
from apps.customers.models import CustomerDataAuditLog, CustomerProfile
from apps.riders.models import RiderProfile, RiderProfileReview

User = get_user_model()


@override_settings(SECURE_SSL_REDIRECT=False)
class RiderCustomerFieldAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = User.objects.create_user(
            username='field_customer',
            password='testpass123',
            role='USER',
            phone='0511111111',
            first_name='Existing',
            last_name='Customer',
        )
        self.customer_profile = CustomerProfile.objects.create(
            user=self.customer,
            measurements={'chest': 40, 'length': 55, 'unit': 'cm'},
        )

        self.category = CustomStyleCategory.objects.create(
            name='collar',
            display_name='Collar Styles',
            display_order=1,
            is_active=True,
        )
        self.style = CustomStyle.objects.create(
            category=self.category,
            name='Classic Collar',
            code='classic_collar',
            image='custom_styles/classic_collar.png',
            display_order=1,
            is_active=True,
        )
        UserStylePreset.objects.create(
            user=self.customer,
            name='Existing Style',
            styles=[{'category': 'collar', 'style_id': self.style.id}],
            is_default=True,
        )

        self.approved_rider = self._create_approved_rider('approved_rider')
        self.pending_rider = User.objects.create_user(
            username='pending_rider',
            password='testpass123',
            role='RIDER',
        )
        RiderProfile.objects.create(user=self.pending_rider, full_name='Pending Rider')

        self.lookup_url = '/api/riders/customers/lookup-or-create/'

    def _create_approved_rider(self, username):
        rider = User.objects.create_user(
            username=username,
            password='testpass123',
            role='RIDER',
        )
        profile, _ = RiderProfile.objects.get_or_create(user=rider)
        profile.full_name = username
        profile.save(update_fields=['full_name'])
        review, _ = RiderProfileReview.objects.get_or_create(profile=profile)
        review.review_status = 'approved'
        review.save(update_fields=['review_status'])
        return rider

    def test_non_rider_cannot_access_lookup(self):
        self.client.force_authenticate(user=self.customer)
        response = self.client.post(
            self.lookup_url,
            {'phone': '0522222222', 'name': 'New Customer'},
            format='json',
        )
        self.assertEqual(response.status_code, 403)

    def test_unapproved_rider_cannot_access_lookup(self):
        self.client.force_authenticate(user=self.pending_rider)
        response = self.client.post(
            self.lookup_url,
            {'phone': '0522222222', 'name': 'New Customer'},
            format='json',
        )
        self.assertEqual(response.status_code, 403)

    @patch('apps.customers.services.customer_provisioning.queue_customer_welcome_sms')
    def test_lookup_or_create_new_customer(self, mock_welcome_sms):
        self.client.force_authenticate(user=self.approved_rider)
        response = self.client.post(
            self.lookup_url,
            {'phone': '0522222222', 'name': 'New Customer'},
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.data['data']['customer']['is_existing'])
        self.assertIsNone(response.data['data']['measurements'])
        self.assertEqual(response.data['data']['style_presets'], [])
        mock_welcome_sms.assert_called_once()

        audit = CustomerDataAuditLog.objects.filter(source='rider_app', action='create').first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.actor_user, self.approved_rider)

    def test_lookup_or_create_existing_customer_returns_data(self):
        self.client.force_authenticate(user=self.approved_rider)
        response = self.client.post(
            self.lookup_url,
            {'phone': '0511111111', 'name': 'Updated Name'},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['data']['customer']['is_existing'])
        self.assertEqual(response.data['data']['customer']['id'], self.customer.id)
        self.assertEqual(response.data['data']['measurements']['chest'], 40)
        self.assertEqual(len(response.data['data']['style_presets']), 1)

        self.customer.refresh_from_db()
        self.assertEqual(self.customer.first_name, 'Updated')

    def test_lookup_or_create_invalid_phone(self):
        self.client.force_authenticate(user=self.approved_rider)
        response = self.client.post(
            self.lookup_url,
            {'phone': 'invalid', 'name': 'Bad Phone'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_get_customer_detail(self):
        self.client.force_authenticate(user=self.approved_rider)
        response = self.client.get(f'/api/riders/customers/{self.customer.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['data']['customer']['id'], self.customer.id)
        self.assertEqual(response.data['data']['measurements']['chest'], 40)

    def test_save_measurements_blocked_without_replace(self):
        self.client.force_authenticate(user=self.approved_rider)
        response = self.client.post(
            f'/api/riders/customers/{self.customer.id}/measurements/',
            {
                'measurements': {'chest': 44, 'length': 60},
                'unit': 'cm',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data['data']['existing_measurements']['chest'], 40)

    def test_save_measurements_with_replace_existing(self):
        self.client.force_authenticate(user=self.approved_rider)
        response = self.client.post(
            f'/api/riders/customers/{self.customer.id}/measurements/',
            {
                'measurements': {'chest': 44, 'length': 60},
                'unit': 'cm',
                'replace_existing': True,
            },
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['data']['profile_updated'])
        self.customer_profile.refresh_from_db()
        self.assertEqual(self.customer_profile.measurements['chest'], 44)

        audit = CustomerDataAuditLog.objects.filter(
            source='rider_app',
            action='replace_measurements',
        ).first()
        self.assertIsNotNone(audit)

    def test_save_measurements_on_empty_profile(self):
        new_customer = User.objects.create_user(
            username='empty_customer',
            password='testpass123',
            role='USER',
        )
        CustomerProfile.objects.create(user=new_customer)

        self.client.force_authenticate(user=self.approved_rider)
        response = self.client.post(
            f'/api/riders/customers/{new_customer.id}/measurements/',
            {
                'measurements': {'chest': 41, 'length': 57},
                'unit': 'cm',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        new_customer.customer_profile.refresh_from_db()
        self.assertEqual(new_customer.customer_profile.measurements['chest'], 41)

    def test_save_style_preset_for_customer(self):
        self.client.force_authenticate(user=self.approved_rider)
        response = self.client.post(
            f'/api/riders/customers/{self.customer.id}/styles/',
            {
                'preset_name': 'Rider Added Style',
                'styles': [
                    {'category': 'collar', 'style_id': self.style.id},
                ],
                'set_as_default': True,
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['data']['style_preset']['name'], 'Rider Added Style')
        self.assertEqual(len(response.data['data']['all_style_presets']), 2)

        preset = UserStylePreset.objects.get(user=self.customer, name='Rider Added Style')
        self.assertTrue(preset.is_default)
        self.assertEqual(preset.user_id, self.customer.id)

        audit = CustomerDataAuditLog.objects.filter(source='rider_app', action='create').last()
        self.assertIsNotNone(audit)

    def test_save_style_preset_invalid_style_id(self):
        self.client.force_authenticate(user=self.approved_rider)
        response = self.client.post(
            f'/api/riders/customers/{self.customer.id}/styles/',
            {
                'preset_name': 'Bad Style',
                'styles': [{'category': 'collar', 'style_id': 99999}],
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_customer_app_sees_rider_saved_data(self):
        self.client.force_authenticate(user=self.approved_rider)
        self.client.post(
            f'/api/riders/customers/{self.customer.id}/measurements/',
            {
                'measurements': {'chest': 45, 'length': 61},
                'unit': 'cm',
                'replace_existing': True,
            },
            format='json',
        )
        self.client.post(
            f'/api/riders/customers/{self.customer.id}/styles/',
            {
                'preset_name': 'Customer Visible Style',
                'styles': [{'category': 'collar', 'style_id': self.style.id}],
                'set_as_default': True,
            },
            format='json',
        )

        self.client.force_authenticate(user=User.objects.get(pk=self.customer.pk))
        measurements_response = self.client.get('/api/customers/measurements/')
        self.assertEqual(measurements_response.status_code, 200)
        customer_entry = next(
            item for item in measurements_response.data['data']['recipients']
            if item['recipient_type'] == 'customer'
        )
        self.assertEqual(customer_entry['current_measurements']['chest'], 45)

        presets_response = self.client.get('/api/customization/presets/')
        self.assertEqual(presets_response.status_code, 200)
        preset_names = [item['name'] for item in presets_response.data]
        self.assertIn('Customer Visible Style', preset_names)
