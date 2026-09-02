"""Tests for owner staff roster and shop assignment APIs."""

from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import CustomUser
from apps.core.services import PhoneVerificationService
from apps.tailors.models import ShopStaffAssignment, TailorProfile, TailorStaffMember

TEST_REST_FRAMEWORK = {
    **settings.REST_FRAMEWORK,
    'DEFAULT_THROTTLE_CLASSES': [],
}


@override_settings(REST_FRAMEWORK=TEST_REST_FRAMEWORK)
class OwnerStaffAPITestCase(TestCase):
    def setUp(self):
        from apps.accounts import views as account_views
        from apps.accounts import views_owner as owner_views

        account_views.PhoneLoginView.throttle_classes = []
        account_views.PhoneVerifyView.throttle_classes = []
        owner_views.OwnerPhoneVerifyView.throttle_classes = []

        self.client = APIClient()
        self.phone_login_url = reverse('accounts:phone-login')
        self.owner_verify_url = reverse('accounts:owner-phone-verify')
        self.owner_switch_url = reverse('accounts:owner-switch-shop')
        self.staff_url = reverse('owner-staff')
        self.shops_url = reverse('owner-shops')
        self.test_otp = PhoneVerificationService.TEST_OTP
        self.owner_phone = '0500000006'

    def _login_owner(self):
        self.client.post(self.phone_login_url, {'phone': self.owner_phone})
        response = self.client.post(self.owner_verify_url, {
            'phone': self.owner_phone,
            'otp_code': self.test_otp,
            'name': 'Owner User',
        })
        token = response.data['data']['tokens']['access_token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        return response

    def _create_shop(self, name):
        response = self.client.post(self.shops_url, {
            'shop_name': name,
            'address': 'Riyadh',
        }, format='json')
        return response.data['data']

    def test_owner_can_add_staff_and_assign_to_two_shops(self):
        self._login_owner()
        shop_a = self._create_shop('Shop A')
        shop_b = self._create_shop('Shop B')

        create_staff = self.client.post(self.staff_url, {
            'name': 'Ahmed Ali',
            'phone': '0500000007',
            'roles': ['stitcher'],
            'permissions': ['can_stitch_orders'],
            'shop_id': shop_a['id'],
        }, format='json')
        self.assertEqual(create_staff.status_code, status.HTTP_201_CREATED)
        staff_id = create_staff.data['data']['id']

        assign_url = reverse('owner-staff-assignments', kwargs={'staff_id': staff_id})
        assign_b = self.client.post(assign_url, {
            'shop_id': shop_b['id'],
            'roles': ['stitcher'],
            'permissions': ['can_stitch_orders', 'can_manage_orders'],
        }, format='json')
        self.assertEqual(assign_b.status_code, status.HTTP_201_CREATED)

        list_response = self.client.get(self.staff_url)
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data['data']), 1)
        self.assertEqual(len(list_response.data['data'][0]['assignments']), 2)

        staff_user = CustomUser.objects.get(phone='0500000007')
        self.assertEqual(
            ShopStaffAssignment.objects.filter(staff_member__user=staff_user).count(),
            2,
        )

    def test_staff_member_can_switch_between_assigned_shops(self):
        owner_login = self._login_owner()
        shop_a = self._create_shop('Switch Shop A')
        shop_b = self._create_shop('Switch Shop B')

        create_staff = self.client.post(self.staff_url, {
            'name': 'Sara Ali',
            'phone': '0500000008',
            'roles': ['stitcher'],
            'permissions': ['can_stitch_orders'],
            'shop_id': shop_a['id'],
        }, format='json')
        staff_id = create_staff.data['data']['id']
        assign_url = reverse('owner-staff-assignments', kwargs={'staff_id': staff_id})
        self.client.post(assign_url, {
            'shop_id': shop_b['id'],
            'roles': ['manager'],
            'permissions': ['can_manage_orders'],
        }, format='json')

        self.client.post(self.phone_login_url, {'phone': '0500000008'})
        staff_login = self.client.post(self.owner_verify_url, {
            'phone': '0500000008',
            'otp_code': self.test_otp,
        })
        self.assertEqual(staff_login.status_code, status.HTTP_200_OK)
        assigned = staff_login.data['data']['tailor_context']['assigned_shops']
        self.assertEqual(len(assigned), 2)

        token = staff_login.data['data']['tokens']['access_token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        switch_a = self.client.post(self.owner_switch_url, {'shop_id': shop_a['id']})
        self.assertEqual(switch_a.status_code, status.HTTP_200_OK)
        self.assertEqual(
            switch_a.data['data']['tailor_context']['access_mode'],
            'employee',
        )

    def test_other_owner_cannot_manage_foreign_staff(self):
        self._login_owner()
        staff = self.client.post(self.staff_url, {
            'name': 'Private Staff',
            'phone': '0500000009',
            'roles': ['stitcher'],
            'permissions': ['can_stitch_orders'],
        }, format='json').data['data']

        other = CustomUser.objects.create_user(
            username='other_owner_staff',
            phone='0500000002',
            role='TAILOR',
        )
        TailorProfile.objects.filter(owner=other, user=other).update(shop_name='Other Owner Shop')

        detail_url = reverse('owner-staff-detail', kwargs={'staff_id': staff['id']})
        self.client.force_authenticate(user=other)
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_staff_removes_roster_member(self):
        self._login_owner()
        staff = self.client.post(self.staff_url, {
            'name': 'Temp Staff',
            'phone': '0500000003',
            'roles': ['stitcher'],
            'permissions': ['can_stitch_orders'],
        }, format='json').data['data']

        detail_url = reverse('owner-staff-detail', kwargs={'staff_id': staff['id']})
        delete_response = self.client.delete(detail_url)
        self.assertEqual(delete_response.status_code, status.HTTP_200_OK)
        self.assertFalse(TailorStaffMember.objects.filter(id=staff['id']).exists())
