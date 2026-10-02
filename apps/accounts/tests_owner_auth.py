"""Tests for owner-side authentication endpoints."""

from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import CustomUser
from apps.accounts.services.tailor_auth import build_legacy_tailor_context
from apps.core.services import PhoneVerificationService
from apps.tailors.models import Business, TailorEmployee, TailorProfile, TailorStaffMember
from apps.tailors.services.owner_staff import (
    create_or_update_shop_assignment,
    find_or_create_staff_user,
)

TEST_REST_FRAMEWORK = {
    **settings.REST_FRAMEWORK,
    'DEFAULT_THROTTLE_CLASSES': [],
}


@override_settings(REST_FRAMEWORK=TEST_REST_FRAMEWORK)
class OwnerAuthenticationTestCase(TestCase):
    def setUp(self):
        from apps.accounts import views as account_views

        self._saved_throttles = (
            account_views.PhoneLoginView.throttle_classes,
            account_views.PhoneVerifyView.throttle_classes,
            account_views.PhoneResendOTPView.throttle_classes,
        )
        account_views.PhoneLoginView.throttle_classes = []
        account_views.PhoneVerifyView.throttle_classes = []
        account_views.PhoneResendOTPView.throttle_classes = []

        self.client = APIClient()
        self.phone_login_url = reverse('accounts:phone-login')
        self.phone_verify_url = reverse('accounts:phone-verify')
        self.owner_switch_url = reverse('accounts:owner-switch-shop')
        self.owner_context_url = reverse('accounts:owner-auth-context')
        self.owner_profile_url = reverse('accounts:owner-profile')
        self.test_phone = '0500000001'
        self.test_otp = PhoneVerificationService.TEST_OTP

    def tearDown(self):
        from apps.accounts import views as account_views

        (
            account_views.PhoneLoginView.throttle_classes,
            account_views.PhoneVerifyView.throttle_classes,
            account_views.PhoneResendOTPView.throttle_classes,
        ) = self._saved_throttles

    def _owner_login(self, *, name='Owner User', app_entry='owner'):
        self.client.post(self.phone_login_url, {'phone': self.test_phone})
        return self.client.post(self.phone_verify_url, {
            'phone': self.test_phone,
            'otp_code': self.test_otp,
            'name': name,
            'role': 'TAILOR',
            'app_entry': app_entry,
        })

    def test_legacy_phone_verify_unchanged_without_app_entry(self):
        self.client.post(self.phone_login_url, {'phone': self.test_phone})
        response = self.client.post(self.phone_verify_url, {
            'phone': self.test_phone,
            'otp_code': self.test_otp,
            'name': 'Legacy User',
            'role': 'USER',
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        tailor_context = response.data['data']['tailor_context']
        self.assertEqual(
            set(tailor_context.keys()),
            {'is_owner', 'is_employee', 'shop_id', 'roles', 'permissions'},
        )
        access_token = response.data['data']['tokens']['access_token']
        self.assertNotIn('shop_id', self._decode_jwt_payload(access_token))

    def test_owner_phone_verify_returns_owner_context(self):
        response = self._owner_login()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.data['data']
        context = data['tailor_context']

        self.assertEqual(context['app_entry'], 'owner')
        self.assertEqual(context['mode'], 'owner')
        self.assertEqual(context['access_mode'], 'owner')
        self.assertEqual(context['routing']['initial_screen'], 'owner_dashboard')
        self.assertIn('owned_shops', context)
        self.assertIn('assigned_shops', context)
        self.assertFalse(context['can_enter_shop_work'])

    def test_owner_with_shop_can_switch_shop(self):
        response = self._owner_login()
        user = CustomUser.objects.get(phone=self.test_phone)
        profile = user.tailor_profile
        profile.shop_name = 'Owner Shop'
        profile.save(update_fields=['shop_name'])

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {response.data['data']['tokens']['access_token']}"
        )
        switch_response = self.client.post(self.owner_switch_url, {'shop_id': profile.id})

        self.assertEqual(switch_response.status_code, status.HTTP_200_OK)
        context = switch_response.data['data']['tailor_context']
        self.assertEqual(context['active_shop_id'], profile.id)
        self.assertEqual(context['routing']['initial_screen'], 'shop_work')

        payload = self._decode_jwt_payload(
            switch_response.data['data']['tokens']['access_token']
        )
        self.assertEqual(payload['shop_id'], profile.id)
        self.assertEqual(payload['access_mode'], 'owner')
        self.assertEqual(payload['app_entry'], 'owner')

    def test_owner_context_endpoint(self):
        response = self._owner_login()
        token = response.data['data']['tokens']['access_token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        context_response = self.client.get(self.owner_context_url)
        self.assertEqual(context_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            context_response.data['data']['tailor_context']['app_entry'],
            'owner',
        )

    def test_switch_shop_denied_for_unrelated_user(self):
        owner_response = self._owner_login()
        owner = CustomUser.objects.get(phone=self.test_phone)
        owner_profile = owner.tailor_profile
        owner_profile.shop_name = 'Owner Shop'
        owner_profile.save(update_fields=['shop_name'])

        other = CustomUser.objects.create_user(
            username='other_owner',
            phone='0500000002',
            role='TAILOR',
        )
        other_profile = other.tailor_profile
        other_profile.shop_name = 'Other Shop'
        other_profile.save(update_fields=['shop_name'])

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {owner_response.data['data']['tokens']['access_token']}"
        )
        denied = self.client.post(self.owner_switch_url, {'shop_id': other_profile.id})
        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)

    def test_employee_can_switch_assigned_shop(self):
        owner = CustomUser.objects.create_user(
            username='shop_owner',
            phone='0522222220',
            role='TAILOR',
        )
        shop = owner.tailor_profile
        shop.shop_name = 'Assigned Shop'
        shop.save(update_fields=['shop_name'])

        employee_user = CustomUser.objects.create_user(
            username='employee_user',
            phone='0522222221',
            role='TAILOR',
        )
        TailorEmployee.objects.create(
            tailor=shop,
            user=employee_user,
            roles=['stitcher'],
            can_stitch_orders=True,
        )

        self.client.post(self.phone_login_url, {'phone': employee_user.phone})
        login = self.client.post(self.phone_verify_url, {
            'phone': employee_user.phone,
            'otp_code': self.test_otp,
            'role': 'TAILOR',
            'app_entry': 'staff',
        })
        self.assertIn(login.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED))

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login.data['data']['tokens']['access_token']}"
        )
        switch_response = self.client.post(self.owner_switch_url, {'shop_id': shop.id})
        self.assertEqual(switch_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            switch_response.data['data']['tailor_context']['access_mode'],
            'employee',
        )

    def test_user_profile_owner_app_entry_and_jwt_shop_id(self):
        response = self._owner_login()
        user = CustomUser.objects.get(phone=self.test_phone)
        profile = user.tailor_profile
        profile.shop_name = 'Owner Shop'
        profile.save(update_fields=['shop_name'])

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {response.data['data']['tokens']['access_token']}"
        )
        switch_response = self.client.post(self.owner_switch_url, {'shop_id': profile.id})
        token = switch_response.data['data']['tokens']['access_token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        account_profile_url = reverse('accounts:user-profile')
        profile_response = self.client.get(
            account_profile_url,
            HTTP_X_APP_ENTRY='owner',
        )
        self.assertEqual(profile_response.status_code, status.HTTP_200_OK)
        context = profile_response.data['data']['tailor_context']
        self.assertTrue(context['is_owner'])
        self.assertEqual(context['shop_id'], profile.id)
        self.assertEqual(context['active_shop_id'], profile.id)
        self.assertEqual(context['app_entry'], 'owner')

    def test_owner_profile_get_and_patch(self):
        response = self._owner_login(name='Owner Profile User')
        token = response.data['data']['tokens']['access_token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        profile_response = self.client.get(self.owner_profile_url)
        self.assertEqual(profile_response.status_code, status.HTTP_200_OK)
        profile = profile_response.data['data']
        self.assertEqual(profile['first_name'], 'Owner')
        self.assertEqual(profile['last_name'], 'Profile User')
        self.assertIn('full_name', profile)
        self.assertIn('phone', profile)

        update_response = self.client.patch(
            self.owner_profile_url,
            {'language': 'ar', 'name': 'Ahmed Ali'},
            format='json',
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        updated = update_response.data['data']
        self.assertEqual(updated['first_name'], 'Ahmed')
        self.assertEqual(updated['last_name'], 'Ali')
        self.assertEqual(updated['language'], 'ar')

    def test_legacy_tailor_context_v2_staff_assignment(self):
        owner = CustomUser.objects.create_user(
            username='owner_ctx',
            phone='0500000006',
            role='TAILOR',
        )
        shop, _ = TailorProfile.objects.get_or_create(
            owner=owner,
            user=owner,
            defaults={},
        )
        shop.shop_name = 'Staff Shop'
        shop.contact_number = '0500000006'
        shop.save(update_fields=['shop_name', 'contact_number'])
        staff_user, _ = find_or_create_staff_user(
            phone='0500000007',
            name='Assigned Staff',
        )
        staff_member, _ = TailorStaffMember.objects.get_or_create(
            owner=owner,
            user=staff_user,
            defaults={'is_active': True},
        )
        create_or_update_shop_assignment(
            staff_member=staff_member,
            shop=shop,
            roles=['manager'],
            permissions=['can_manage_orders'],
            is_active=True,
        )

        context = build_legacy_tailor_context(staff_user)
        self.assertTrue(context['is_employee'])
        self.assertFalse(context['is_owner'])
        self.assertEqual(context['shop_id'], shop.id)
        self.assertIn('can_manage_orders', context['permissions'])

    def test_v1_staff_phone_verify_without_app_entry_infers_staff(self):
        owner = CustomUser.objects.create_user(
            username='owner_verify',
            phone='0500000008',
            role='TAILOR',
        )
        Business.objects.create(
            owner=owner,
            name='Owner Biz',
            contact_phone='0500000008',
            city='Riyadh',
            is_active=True,
        )
        shop, _ = TailorProfile.objects.get_or_create(
            owner=owner,
            user=owner,
            defaults={},
        )
        shop.shop_name = 'Verify Staff Shop'
        shop.contact_number = '0500000008'
        shop.save(update_fields=['shop_name', 'contact_number'])
        staff_phone = '0500000009'
        staff_user, _ = find_or_create_staff_user(
            phone=staff_phone,
            name='Verify Staff',
        )
        staff_member, _ = TailorStaffMember.objects.get_or_create(
            owner=owner,
            user=staff_user,
            defaults={'is_active': True},
        )
        create_or_update_shop_assignment(
            staff_member=staff_member,
            shop=shop,
            roles=['manager'],
            permissions=['can_manage_orders'],
            is_active=True,
        )

        self.client.post(self.phone_login_url, {'phone': staff_phone})
        response = self.client.post(self.phone_verify_url, {
            'phone': staff_phone,
            'otp_code': self.test_otp,
            'name': 'Verify Staff',
            'role': 'TAILOR',
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data['data']
        self.assertEqual(data['app_entry'], 'staff')
        self.assertEqual(data['app_entry_source'], 'inferred')
        context = data['tailor_context']
        self.assertTrue(context['is_employee'])
        self.assertFalse(context.get('is_owner'))
        self.assertEqual(context['app_entry'], 'staff')

    def test_customer_cannot_access_owner_profile(self):
        customer_phone = '0500000005'
        self.client.post(self.phone_login_url, {'phone': customer_phone})
        response = self.client.post(self.phone_verify_url, {
            'phone': customer_phone,
            'otp_code': self.test_otp,
            'name': 'Customer User',
            'role': 'USER',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        token = response.data['data']['tokens']['access_token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        profile_response = self.client.get(self.owner_profile_url)
        self.assertEqual(profile_response.status_code, status.HTTP_403_FORBIDDEN)

    @staticmethod
    def _decode_jwt_payload(access_token):
        import base64
        import json

        payload_segment = access_token.split('.')[1]
        padding = '=' * (-len(payload_segment) % 4)
        decoded = base64.urlsafe_b64decode(payload_segment + padding)
        return json.loads(decoded)
