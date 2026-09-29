"""Tests for V2 staff roster and shop assignment APIs."""

from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import CustomUser
from apps.core.services import PhoneVerificationService
from apps.tailors.models import (
    ServiceArea,
    ShopStaffAssignment,
    TailorEmployee,
    TailorProfile,
    TailorStaffMember,
)

TEST_REST_FRAMEWORK = {
    **settings.REST_FRAMEWORK,
    'DEFAULT_THROTTLE_CLASSES': [],
}


@override_settings(REST_FRAMEWORK=TEST_REST_FRAMEWORK)
class V2StaffAPITestCase(TestCase):
    def setUp(self):
        from apps.accounts import views as account_views

        self._saved_throttles = (
            account_views.PhoneLoginView.throttle_classes,
            account_views.PhoneVerifyView.throttle_classes,
        )
        account_views.PhoneLoginView.throttle_classes = []
        account_views.PhoneVerifyView.throttle_classes = []

        self.client = APIClient()
        self.service_area = ServiceArea.objects.create(
            name='V2 Staff Area',
            city='Riyadh',
            is_active=True,
        )
        self.test_otp = PhoneVerificationService.TEST_OTP
        self.owner_phone = '0522222225'

    def tearDown(self):
        from apps.accounts import views as account_views

        (
            account_views.PhoneLoginView.throttle_classes,
            account_views.PhoneVerifyView.throttle_classes,
        ) = self._saved_throttles

    def _url(self, name, **kwargs):
        if ':' in name and not name.startswith('v2:'):
            name = f'v2:{name}'
        return reverse(name, kwargs=kwargs)

    def _login_owner(self):
        self.client.post(self._url('accounts_v2:v2-phone-login'), {'phone': self.owner_phone})
        response = self.client.post(self._url('accounts_v2:v2-phone-verify'), {
            'phone': self.owner_phone,
            'otp_code': self.test_otp,
            'name': 'V2 Owner',
            'role': 'TAILOR',
            'app_entry': 'owner',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        token = response.data['data']['tokens']['access_token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        self.client.post(
            self._url('tailors_v2:v2-business'),
            {'name': 'V2 Staff Business', 'contact_phone': self.owner_phone},
            format='json',
        )
        return response

    def _create_shop(self, name):
        response = self.client.post(self._url('tailors_v2:v2-shops'), {
            'name': name,
            'contact_number': self.owner_phone,
            'address': 'Riyadh',
            'service_area_id': self.service_area.id,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        return response.data['data']

    def _create_staff(self, phone='0522222226', shop_id=None):
        payload = {
            'name': 'V2 Staff',
            'phone': phone,
            'roles': ['stitcher'],
            'permissions': ['can_stitch_orders'],
        }
        if shop_id is not None:
            payload['shop_id'] = shop_id
        response = self.client.post(self._url('tailors_v2:v2-staff'), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return response.data['data']

    def test_v2_delete_staff_method_allowed(self):
        self._login_owner()
        staff = self._create_staff()
        detail_url = self._url('tailors_v2:v2-staff-detail', staff_id=staff['id'])
        response = self.client.delete(detail_url)
        self.assertNotEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_v2_delete_staff_removes_roster_member(self):
        self._login_owner()
        staff = self._create_staff()
        detail_url = self._url('tailors_v2:v2-staff-detail', staff_id=staff['id'])
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(TailorStaffMember.objects.filter(id=staff['id']).exists())

    def test_v2_patch_assignment_updates_roles(self):
        self._login_owner()
        shop = self._create_shop('V2 Patch Shop')
        staff = self._create_staff(shop_id=shop['id'])
        assignment = ShopStaffAssignment.objects.get(staff_member_id=staff['id'])
        detail_url = self._url(
            'tailors_v2:v2-staff-assignment-detail',
            staff_id=staff['id'],
            assignment_id=assignment.id,
        )
        response = self.client.patch(detail_url, {
            'roles': ['manager'],
            'permissions': ['can_manage_orders'],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        assignment.refresh_from_db()
        self.assertEqual(assignment.roles, ['manager'])
        self.assertTrue(assignment.can_manage_orders)

    def test_v2_delete_assignment_removes_row(self):
        self._login_owner()
        shop = self._create_shop('V2 Delete Assign Shop')
        staff = self._create_staff(shop_id=shop['id'])
        assignment = ShopStaffAssignment.objects.get(staff_member_id=staff['id'])
        staff_user = CustomUser.objects.get(phone='0522222226')
        employee = TailorEmployee.objects.get(tailor_id=shop['id'], user=staff_user)
        self.assertTrue(employee.is_active)

        detail_url = self._url(
            'tailors_v2:v2-staff-assignment-detail',
            staff_id=staff['id'],
            assignment_id=assignment.id,
        )
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(ShopStaffAssignment.objects.filter(id=assignment.id).exists())
        employee.refresh_from_db()
        self.assertFalse(employee.is_active)

    def test_v2_foreign_owner_cannot_delete_staff(self):
        self._login_owner()
        staff = self._create_staff()
        detail_url = self._url('tailors_v2:v2-staff-detail', staff_id=staff['id'])

        other = CustomUser.objects.create_user(
            username='v2_other_owner',
            phone='0522222227',
            role='TAILOR',
        )
        TailorProfile.objects.filter(owner=other, user=other).update(
            shop_name='Other V2 Shop',
        )
        self.client.force_authenticate(user=other)
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(TailorStaffMember.objects.filter(id=staff['id']).exists())

    def test_v2_assignment_not_found_returns_404(self):
        self._login_owner()
        staff = self._create_staff()
        detail_url = self._url(
            'tailors_v2:v2-staff-assignment-detail',
            staff_id=staff['id'],
            assignment_id=99999,
        )
        patch_response = self.client.patch(detail_url, {'roles': ['manager']}, format='json')
        delete_response = self.client.delete(detail_url)
        self.assertEqual(patch_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(delete_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_v2_list_assignments(self):
        self._login_owner()
        shop = self._create_shop('V2 List Assign Shop')
        staff = self._create_staff(shop_id=shop['id'])
        list_url = self._url('tailors_v2:v2-staff-assignments', staff_id=staff['id'])
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['data']), 1)
