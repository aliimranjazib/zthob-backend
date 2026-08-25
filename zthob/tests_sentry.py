from django.test import RequestFactory, SimpleTestCase, override_settings

from zthob.monitoring.sentry import (
    _sentry_level_for_status,
    init_sentry,
    is_sentry_enabled,
    journey_for_path,
    report_api_error,
    report_api_server_error,
)
from zthob.utils import api_response


class SentryConfigTest(SimpleTestCase):
    def test_disabled_without_dsn(self):
        with self.settings(SENTRY_DSN=''):
            self.assertFalse(is_sentry_enabled())

    @override_settings(APP_ENV='staging', SENTRY_DSN='https://example@o0.ingest.sentry.io/0')
    def test_enabled_on_staging_with_dsn(self):
        self.assertTrue(is_sentry_enabled())

    def test_journey_mapping(self):
        self.assertEqual(journey_for_path('/api/orders/checkout/myfatoorah/prepare/'), 'checkout')
        self.assertEqual(journey_for_path('/api/tailors/pos/customers/create/'), 'walk_in_create_customer')
        self.assertEqual(journey_for_path('/api/tailors/pos/customers/'), 'walk_in')
        self.assertEqual(journey_for_path('/api/accounts/phone-verify/'), 'auth')

    def test_sentry_level_for_status(self):
        self.assertEqual(_sentry_level_for_status(500), 'error')
        self.assertEqual(_sentry_level_for_status(502), 'error')
        self.assertEqual(_sentry_level_for_status(400), 'warning')
        self.assertEqual(_sentry_level_for_status(404), 'warning')
        self.assertEqual(_sentry_level_for_status(429), 'warning')

    @override_settings(APP_ENV='development', SENTRY_DSN='')
    def test_init_sentry_noop_when_disabled(self):
        self.assertFalse(init_sentry())


class ApiResponseSentryHookTest(SimpleTestCase):
    @override_settings(APP_ENV='development', SENTRY_DSN='')
    def test_api_response_500_does_not_crash_without_sentry(self):
        factory = RequestFactory()
        request = factory.get('/api/orders/create/')
        response = api_response(
            success=False,
            message='Server blew up',
            status_code=500,
            request=request,
        )
        self.assertEqual(response.status_code, 500)

    @override_settings(APP_ENV='development', SENTRY_DSN='')
    def test_api_response_400_does_not_crash_without_sentry(self):
        factory = RequestFactory()
        request = factory.post('/api/accounts/phone-login/')
        response = api_response(
            success=False,
            message='Invalid phone number',
            status_code=400,
            request=request,
        )
        self.assertEqual(response.status_code, 400)

    @override_settings(APP_ENV='staging', SENTRY_DSN='https://example@o0.ingest.sentry.io/0')
    def test_report_api_error_noop_without_init(self):
        report_api_error(message='validation failed', status_code=400)
        report_api_server_error(message='test', status_code=500)

    @override_settings(APP_ENV='development', SENTRY_DSN='')
    def test_custom_exception_handler_returns_500(self):
        from zthob.utils import custom_exception_handler

        factory = RequestFactory()
        request = factory.get('/api/orders/create/')
        response = custom_exception_handler(RuntimeError('boom'), {'request': request})
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 500)
        self.assertFalse(response.data['success'])
