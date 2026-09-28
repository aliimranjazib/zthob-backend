"""Rate-limit policy: app APIs unrestricted; auth endpoints throttled."""

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.request import Request
from rest_framework.test import APIClient, APIRequestFactory

from apps.accounts.throttles import AuthLoginRateThrottle, OTPRateThrottle
from apps.accounts.views import PhoneLoginView, UserLoginView

User = get_user_model()

LOC_MEM_CACHE = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    },
}


@override_settings(CACHES=LOC_MEM_CACHE)
class ThrottlePolicyTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='throttle_user',
            password='testpass123',
            phone='0500000099',
        )
        self.profile_url = reverse('accounts:user-profile')
        self.phone_login_url = reverse('accounts:phone-login')

    def test_user_login_view_uses_auth_login_throttle(self):
        self.assertIn(AuthLoginRateThrottle, UserLoginView.throttle_classes)

    def test_phone_login_view_uses_otp_throttle(self):
        self.assertIn(OTPRateThrottle, PhoneLoginView.throttle_classes)

    def test_authenticated_profile_requests_are_not_throttled(self):
        self.client.force_authenticate(user=self.user)
        for _ in range(25):
            response = self.client.get(self.profile_url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertNotEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_phone_login_is_throttled_after_limit(self):
        """Production otp scope is 5/minute — 6th request from same IP should 429."""
        cache.clear()
        for _ in range(5):
            response = self.client.post(
                self.phone_login_url,
                {'phone': '0500000100'},
                format='json',
                REMOTE_ADDR='10.0.0.55',
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        throttled = self.client.post(
            self.phone_login_url,
            {'phone': '0500000101'},
            format='json',
            REMOTE_ADDR='10.0.0.55',
        )
        self.assertEqual(throttled.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_otp_throttle_class_enforces_scope_limit(self):
        cache.clear()
        factory = APIRequestFactory()
        wsgi_request = factory.post(
            '/api/accounts/phone-login/',
            {'phone': '0500000102'},
            format='json',
            REMOTE_ADDR='10.0.0.56',
        )
        request = Request(wsgi_request)
        view = PhoneLoginView()

        throttle = OTPRateThrottle()
        for _ in range(5):
            self.assertTrue(throttle.allow_request(request, view))
        self.assertFalse(throttle.allow_request(request, view))
