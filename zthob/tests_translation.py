"""
Comprehensive test cases for the translation system.
Tests language detection, message translation, error translation, and API response integration.
"""
from django.test import TestCase, RequestFactory
from rest_framework.test import APIClient
from rest_framework import status
from django.http import Http404
from django.core.exceptions import PermissionDenied
from rest_framework.exceptions import AuthenticationFailed

from zthob.translations import (
    get_language_from_request,
    translate_message,
    translate_errors,
    TRANSLATIONS,
    add_translation
)
from zthob.utils import api_response
from zthob.middleware import TranslationMiddleware, get_current_request


class LanguageDetectionTests(TestCase):
    """Test language detection from request headers"""
    
    def setUp(self):
        self.factory = RequestFactory()
    
    def test_arabic_language_detection(self):
        """Test detection of Arabic language from Accept-Language header"""
        request = self.factory.get('/api/test/')
        request.META['HTTP_ACCEPT_LANGUAGE'] = 'ar'
        
        language = get_language_from_request(request)
        self.assertEqual(language, 'ar')
    
    def test_english_language_detection(self):
        """Test detection of English language from Accept-Language header"""
        request = self.factory.get('/api/test/')
        request.META['HTTP_ACCEPT_LANGUAGE'] = 'en'
        
        language = get_language_from_request(request)
        self.assertEqual(language, 'en')
    
    def test_arabic_with_region(self):
        """Test Arabic language detection with region code"""
        request = self.factory.get('/api/test/')
        request.META['HTTP_ACCEPT_LANGUAGE'] = 'ar-SA,ar;q=0.9'
        
        language = get_language_from_request(request)
        self.assertEqual(language, 'ar')
    
    def test_arabic_with_quality_value(self):
        """Test Arabic language detection with quality values"""
        request = self.factory.get('/api/test/')
        request.META['HTTP_ACCEPT_LANGUAGE'] = 'ar,en;q=0.9'
        
        language = get_language_from_request(request)
        self.assertEqual(language, 'ar')
    
    def test_no_language_header_defaults_to_english(self):
        """Test that missing Accept-Language header defaults to English"""
        request = self.factory.get('/api/test/')
        
        language = get_language_from_request(request)
        self.assertEqual(language, 'en')
    
    def test_empty_language_header_defaults_to_english(self):
        """Test that empty Accept-Language header defaults to English"""
        request = self.factory.get('/api/test/')
        request.META['HTTP_ACCEPT_LANGUAGE'] = ''
        
        language = get_language_from_request(request)
        self.assertEqual(language, 'en')
    
    def test_none_request_returns_english(self):
        """Test that None request returns English"""
        language = get_language_from_request(None)
        self.assertEqual(language, 'en')


class MessageTranslationTests(TestCase):
    """Test message translation functionality"""
    
    def test_translate_simple_message_to_arabic(self):
        """Test translation of a simple message to Arabic"""
        message = "Order created successfully"
        translated = translate_message(message, language='ar')
        
        self.assertEqual(translated, "تم إنشاء الطلب بنجاح")
        self.assertNotEqual(translated, message)
    
    def test_translate_message_with_placeholder(self):
        """Test translation of message with placeholder"""
        message = "OTP sent to {phone_number}"
        translated = translate_message(message, language='ar', phone_number='1234567890')
        
        self.assertEqual(translated, "تم إرسال رمز التحقق إلى 1234567890")
        self.assertIn('1234567890', translated)
    
    def test_translate_message_with_id_placeholder(self):
        """Test translation of message with ID placeholder"""
        message = "The requested resource with ID {id} does not exist."
        translated = translate_message(message, language='ar', id='123')
        
        self.assertEqual(translated, "الموارد المطلوبة بالمعرف 123 غير موجودة.")
        self.assertIn('123', translated)
    
    def test_english_message_returns_unchanged(self):
        """Test that English language returns original message"""
        message = "Order created successfully"
        translated = translate_message(message, language='en')
        
        self.assertEqual(translated, message)
    
    def test_unknown_message_returns_original(self):
        """Test that unknown message returns original text"""
        message = "This is a new message that doesn't exist"
        translated = translate_message(message, language='ar')
        
        self.assertEqual(translated, message)
    
    def test_empty_message_returns_empty(self):
        """Test that empty message returns empty string"""
        translated = translate_message("", language='ar')
        self.assertEqual(translated, "")
    
    def test_none_message_handles_gracefully(self):
        """Test that None message is handled gracefully"""
        translated = translate_message(None, language='ar')
        self.assertIsNone(translated)


class ErrorTranslationTests(TestCase):
    """Test error translation functionality"""
    
    def test_translate_string_error(self):
        """Test translation of string error"""
        error = "Validation failed"
        translated = translate_errors(error, language='ar')
        
        self.assertEqual(translated, "فشل التحقق")
    
    def test_translate_dict_error_with_list_values(self):
        """Test translation of dict error with list values"""
        error = {
            "field_name": ["This field is required."]
        }
        translated = translate_errors(error, language='ar')
        
        self.assertIsInstance(translated, dict)
        self.assertEqual(translated["field_name"][0], "هذا الحقل مطلوب.")
    
    def test_translate_dict_error_with_string_values(self):
        """Test translation of dict error with string values"""
        error = {
            "error": "Invalid credentials"
        }
        translated = translate_errors(error, language='ar')
        
        self.assertEqual(translated["error"], "بيانات الاعتماد غير صحيحة")
    
    def test_translate_list_error(self):
        """Test translation of list error"""
        error = ["This field is required.", "Invalid format"]
        translated = translate_errors(error, language='ar')
        
        self.assertIsInstance(translated, list)
        self.assertEqual(translated[0], "هذا الحقل مطلوب.")
    
    def test_translate_nested_dict_error(self):
        """Test translation of nested dict error"""
        error = {
            "field1": {
                "nested": "Invalid value"
            }
        }
        translated = translate_errors(error, language='ar')
        
        self.assertIsInstance(translated, dict)
        self.assertIsInstance(translated["field1"], dict)
    
    def test_english_error_returns_unchanged(self):
        """Test that English language returns original error"""
        error = "Validation failed"
        translated = translate_errors(error, language='en')
        
        self.assertEqual(translated, error)
    
    def test_none_error_returns_none(self):
        """Test that None error returns None"""
        translated = translate_errors(None, language='ar')
        self.assertIsNone(translated)


class APIResponseTranslationTests(TestCase):
    """Test API response translation integration"""
    
    def setUp(self):
        self.factory = RequestFactory()
    
    def test_api_response_translates_message_to_arabic(self):
        """Test that api_response translates message to Arabic"""
        request = self.factory.get('/api/test/')
        request.META['HTTP_ACCEPT_LANGUAGE'] = 'ar'
        
        response = api_response(
            success=True,
            message="Order created successfully",
            data={"order_id": 123},
            request=request
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = response.data
        self.assertEqual(response_data['message'], "تم إنشاء الطلب بنجاح")
        self.assertEqual(response_data['success'], True)
    
    def test_api_response_keeps_english_when_no_header(self):
        """Test that api_response keeps English when no header"""
        request = self.factory.get('/api/test/')
        
        response = api_response(
            success=True,
            message="Order created successfully",
            data={"order_id": 123},
            request=request
        )
        
        response_data = response.data
        self.assertEqual(response_data['message'], "Order created successfully")
    
    def test_api_response_translates_errors_to_arabic(self):
        """Test that api_response translates errors to Arabic"""
        request = self.factory.get('/api/test/')
        request.META['HTTP_ACCEPT_LANGUAGE'] = 'ar'
        
        response = api_response(
            success=False,
            message="Validation failed",
            errors="Invalid credentials",
            request=request
        )
        
        response_data = response.data
        self.assertEqual(response_data['message'], "فشل التحقق")
        self.assertEqual(response_data['errors'], "بيانات الاعتماد غير صحيحة")
    
    def test_api_response_translates_dict_errors(self):
        """Test that api_response translates dict errors"""
        request = self.factory.get('/api/test/')
        request.META['HTTP_ACCEPT_LANGUAGE'] = 'ar'
        
        errors = {
            "email": ["This field is required."]
        }
        
        response = api_response(
            success=False,
            message="Validation failed",
            errors=errors,
            request=request
        )
        
        response_data = response.data
        # Note: api_response extracts first error as string for field errors
        # So errors will be a translated string, not a dict
        self.assertIsInstance(response_data['errors'], str)
        self.assertEqual(response_data['errors'], "هذا الحقل مطلوب.")
    
    def test_api_response_with_placeholder_in_message(self):
        """Test api_response with placeholder in message"""
        request = self.factory.get('/api/test/')
        request.META['HTTP_ACCEPT_LANGUAGE'] = 'ar'
        
        response = api_response(
            success=True,
            message="OTP sent to {phone_number}",
            data={"otp": "123456"},
            request=request
        )
        
        # Note: Placeholder messages are translated but not formatted
        # The translation exists, so it returns Arabic with placeholder
        response_data = response.data
        # Should return Arabic translation with placeholder still present
        self.assertIn("تم", response_data['message'])
        self.assertIn("{phone_number}", response_data['message'])
    
    def test_api_response_without_request_uses_context(self):
        """Test that api_response can work without explicit request"""
        # This tests the middleware integration
        request = self.factory.get('/api/test/')
        request.META['HTTP_ACCEPT_LANGUAGE'] = 'ar'
        
        # Simulate middleware setting context
        from zthob.middleware import _request_context
        _request_context.set(request)
        
        try:
            response = api_response(
                success=True,
                message="Order created successfully",
                data={"order_id": 123}
            )
            
            response_data = response.data
            self.assertEqual(response_data['message'], "تم إنشاء الطلب بنجاح")
        finally:
            _request_context.set(None)


class MiddlewareTests(TestCase):
    """Test middleware functionality"""
    
    def setUp(self):
        self.factory = RequestFactory()
    
    def test_middleware_stores_request_in_context(self):
        """Test that middleware stores request in context"""
        request = self.factory.get('/api/test/')
        request.META['HTTP_ACCEPT_LANGUAGE'] = 'ar'
        
        middleware = TranslationMiddleware(lambda req: None)
        
        # Call middleware
        middleware(request)
        
        # Check that context was cleared after request
        current_request = get_current_request()
        self.assertIsNone(current_request)
    
    def test_get_current_request_returns_none_when_not_set(self):
        """Test that get_current_request returns None when not set"""
        request = get_current_request()
        self.assertIsNone(request)


class TranslationDictionaryTests(TestCase):
    """Test translation dictionary functionality"""
    
    def test_translation_dictionary_has_entries(self):
        """Test that translation dictionary has entries"""
        self.assertGreater(len(TRANSLATIONS), 0)
        self.assertIsInstance(TRANSLATIONS, dict)
    
    def test_add_translation_dynamically(self):
        """Test adding translation dynamically"""
        original_count = len(TRANSLATIONS)
        
        add_translation("Test message", "رسالة اختبار")
        
        self.assertEqual(len(TRANSLATIONS), original_count + 1)
        self.assertEqual(TRANSLATIONS["Test message"], "رسالة اختبار")
        
        # Clean up
        del TRANSLATIONS["Test message"]
    
    def test_translation_keys_are_strings(self):
        """Test that all translation keys are strings"""
        for key in TRANSLATIONS.keys():
            self.assertIsInstance(key, str)
    
    def test_translation_values_are_strings(self):
        """Test that all translation values are strings"""
        for value in TRANSLATIONS.values():
            self.assertIsInstance(value, str)


class IntegrationTests(TestCase):
    """Integration tests for complete translation flow"""
    
    def setUp(self):
        self.factory = RequestFactory()
    
    def test_complete_flow_arabic_request(self):
        """Test complete flow with Arabic request"""
        request = self.factory.get('/api/test/')
        request.META['HTTP_ACCEPT_LANGUAGE'] = 'ar'
        
        # Simulate complete API response
        response = api_response(
            success=True,
            message="Order created successfully",
            data={
                "order_id": 123,
                "status": "pending"
            },
            request=request
        )
        
        # Verify response structure
        self.assertEqual(response.status_code, 200)
        response_data = response.data
        
        # Verify translation
        self.assertEqual(response_data['message'], "تم إنشاء الطلب بنجاح")
        self.assertEqual(response_data['success'], True)
        self.assertIsNotNone(response_data['data'])
        self.assertEqual(response_data['data']['order_id'], 123)
    
    def test_complete_flow_english_request(self):
        """Test complete flow with English request"""
        request = self.factory.get('/api/test/')
        request.META['HTTP_ACCEPT_LANGUAGE'] = 'en'
        
        response = api_response(
            success=True,
            message="Order created successfully",
            data={"order_id": 123},
            request=request
        )
        
        response_data = response.data
        self.assertEqual(response_data['message'], "Order created successfully")
    
    def test_error_response_translation(self):
        """Test error response translation"""
        request = self.factory.get('/api/test/')
        request.META['HTTP_ACCEPT_LANGUAGE'] = 'ar'
        
        response = api_response(
            success=False,
            message="Authentication failed. Please provide a valid token.",
            errors="Invalid or expired token",
            status_code=401,
            request=request
        )
        
        response_data = response.data
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response_data['success'], False)
        self.assertEqual(response_data['message'], "فشل المصادقة. يرجى تقديم رمز صحيح.")
        self.assertEqual(response_data['errors'], "رمز غير صحيح أو منتهي الصلاحية")
    
    def test_validation_error_translation(self):
        """Test validation error translation"""
        request = self.factory.get('/api/test/')
        request.META['HTTP_ACCEPT_LANGUAGE'] = 'ar'
        
        errors = {
            "email": ["This field is required."],
            "password": ["This field may not be blank."]
        }
        
        response = api_response(
            success=False,
            message="Validation failed",
            errors=errors,
            status_code=400,
            request=request
        )
        
        response_data = response.data
        self.assertEqual(response_data['message'], "فشل التحقق")
        # Note: api_response extracts first error as string for field errors
        # So errors will be the first translated error message
        self.assertIsInstance(response_data['errors'], str)
        self.assertEqual(response_data['errors'], "هذا الحقل مطلوب.")


class EdgeCaseTests(TestCase):
    """Test edge cases and error handling"""
    
    def setUp(self):
        self.factory = RequestFactory()
    
    def test_special_characters_in_message(self):
        """Test handling of special characters in messages"""
        request = self.factory.get('/api/test/')
        request.META['HTTP_ACCEPT_LANGUAGE'] = 'ar'
        
        # Test with a message that has special characters
        message = "Order #123 created!"
        response = api_response(
            success=True,
            message=message,
            request=request
        )
        
        # Should handle gracefully (return original if not translated)
        response_data = response.data
        self.assertIsNotNone(response_data['message'])
    
    def test_unicode_characters(self):
        """Test handling of unicode characters"""
        request = self.factory.get('/api/test/')
        request.META['HTTP_ACCEPT_LANGUAGE'] = 'ar'
        
        # Arabic translations contain unicode
        response = api_response(
            success=True,
            message="Order created successfully",
            request=request
        )
        
        response_data = response.data
        # Should contain Arabic unicode characters
        self.assertIn("تم", response_data['message'])
    
    def test_malformed_accept_language_header(self):
        """Test handling of malformed Accept-Language header"""
        request = self.factory.get('/api/test/')
        request.META['HTTP_ACCEPT_LANGUAGE'] = 'invalid-header-format'
        
        language = get_language_from_request(request)
        # Should default to English
        self.assertEqual(language, 'en')
    
    def test_case_insensitive_language_detection(self):
        """Test that language detection is case insensitive"""
        request = self.factory.get('/api/test/')
        request.META['HTTP_ACCEPT_LANGUAGE'] = 'AR'
        
        language = get_language_from_request(request)
        self.assertEqual(language, 'ar')
    
    def test_empty_data_in_response(self):
        """Test response with empty data"""
        request = self.factory.get('/api/test/')
        request.META['HTTP_ACCEPT_LANGUAGE'] = 'ar'
        
        response = api_response(
            success=True,
            message="Operation completed successfully",
            data=None,
            request=request
        )
        
        response_data = response.data
        self.assertEqual(response_data['message'], "تمت العملية بنجاح")
        self.assertIsNone(response_data['data'])

