#!/usr/bin/env python
"""
Test script to verify all rider system implementation
Run this to check if everything is properly implemented
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zthob.settings')
django.setup()

def test_imports():
    """Test all imports work correctly"""
    print("=" * 60)
    print("TESTING IMPORTS")
    print("=" * 60)
    
    try:
        from apps.riders.models import (
            RiderProfile, 
            RiderProfileReview, 
            RiderDocument, 
            RiderOrderAssignment
        )
        print("✓ Models imported successfully")
    except Exception as e:
        print(f"✗ Model import failed: {e}")
        return False
    
    try:
        from apps.riders.serializers import (
            RiderRegisterSerializer,
            RiderProfileSerializer,
            RiderProfileUpdateSerializer,
            RiderProfileSubmissionSerializer,
            RiderProfileStatusSerializer,
            RiderDocumentSerializer,
            RiderDocumentUploadSerializer,
            RiderProfileReviewSerializer,
            RiderProfileReviewUpdateSerializer,
            RiderOrderListSerializer,
            RiderOrderDetailSerializer,
            RiderAcceptOrderSerializer,
            RiderAddMeasurementsSerializer,
            RiderUpdateOrderStatusSerializer,
        )
        print("✓ Serializers imported successfully")
    except Exception as e:
        print(f"✗ Serializer import failed: {e}")
        return False
    
    try:
        from apps.riders.views import (
            RiderRegisterView,
            RiderSendOTPView,
            RiderVerifyOTPView,
            RiderProfileView,
            RiderProfileSubmissionView,
            RiderProfileStatusView,
            RiderDocumentUploadView,
            RiderDocumentListView,
            RiderDocumentDeleteView,
            RiderAvailableOrdersView,
            RiderMyOrdersView,
            RiderOrderDetailView,
            RiderAcceptOrderView,
            RiderAddMeasurementsView,
            RiderUpdateOrderStatusView,
        )
        print("✓ Views imported successfully")
    except Exception as e:
        print(f"✗ View import failed: {e}")
        return False
    
    try:
        from apps.riders.views_review import (
            RiderProfileReviewListView,
            RiderProfileReviewDetailView,
        )
        print("✓ Review views imported successfully")
    except Exception as e:
        print(f"✗ Review view import failed: {e}")
        return False
    
    try:
        from apps.riders.admin import (
            RiderProfileAdmin,
            RiderProfileReviewAdmin,
            RiderDocumentAdmin,
            RiderOrderAssignmentAdmin,
        )
        print("✓ Admin classes imported successfully")
    except Exception as e:
        print(f"✗ Admin import failed: {e}")
        return False
    
    return True


def test_models():
    """Test model definitions"""
    print("\n" + "=" * 60)
    print("TESTING MODELS")
    print("=" * 60)
    
    from apps.riders.models import RiderProfile, RiderProfileReview, RiderDocument
    
    # Check RiderProfile fields
    required_fields = [
        'user', 'full_name', 'phone_number', 'iqama_number', 'iqama_expiry_date',
        'license_number', 'license_expiry_date', 'license_type',
        'vehicle_type', 'vehicle_plate_number_arabic', 'vehicle_plate_number_english',
        'vehicle_make', 'vehicle_model', 'vehicle_year', 'vehicle_color',
        'vehicle_registration_number', 'vehicle_registration_expiry_date',
        'insurance_provider', 'insurance_policy_number', 'insurance_expiry_date',
        'is_active', 'is_available', 'current_latitude', 'current_longitude',
        'total_deliveries', 'rating'
    ]
    
    for field in required_fields:
        if hasattr(RiderProfile, field):
            print(f"✓ RiderProfile.{field} exists")
        else:
            print(f"✗ RiderProfile.{field} MISSING")
            return False
    
    # Check properties
    if hasattr(RiderProfile, 'is_approved'):
        print("✓ RiderProfile.is_approved property exists")
    else:
        print("✗ RiderProfile.is_approved property MISSING")
        return False
    
    if hasattr(RiderProfile, 'review_status'):
        print("✓ RiderProfile.review_status property exists")
    else:
        print("✗ RiderProfile.review_status property MISSING")
        return False
    
    # Check RiderDocument
    if hasattr(RiderDocument, 'DOCUMENT_TYPE_CHOICES'):
        choices = RiderDocument.DOCUMENT_TYPE_CHOICES
        expected_types = ['iqama_front', 'iqama_back', 'license_front', 'license_back', 
                         'istimara_front', 'istimara_back', 'insurance']
        found_types = [choice[0] for choice in choices]
        for doc_type in expected_types:
            if doc_type in found_types:
                print(f"✓ Document type '{doc_type}' exists")
            else:
                print(f"✗ Document type '{doc_type}' MISSING")
                return False
    else:
        print("✗ RiderDocument.DOCUMENT_TYPE_CHOICES MISSING")
        return False
    
    return True


def test_serializers():
    """Test serializer definitions"""
    print("\n" + "=" * 60)
    print("TESTING SERIALIZERS")
    print("=" * 60)
    
    from apps.riders.serializers import (
        RiderProfileSerializer,
        RiderProfileUpdateSerializer,
        RiderProfileSubmissionSerializer,
    )
    
    # Check RiderProfileSerializer fields
    serializer = RiderProfileSerializer()
    expected_fields = [
        'id', 'username', 'email', 'is_phone_verified', 'is_approved', 'review_status',
        'full_name', 'phone_number', 'emergency_contact',
        'iqama_number', 'iqama_expiry_date',
        'license_number', 'license_expiry_date', 'license_type',
        'vehicle_type', 'vehicle_plate_number_arabic', 'vehicle_plate_number_english',
        'vehicle_make', 'vehicle_model', 'vehicle_year', 'vehicle_color',
        'vehicle_registration_number', 'vehicle_registration_expiry_date',
        'insurance_provider', 'insurance_policy_number', 'insurance_expiry_date',
        'is_active', 'is_available', 'current_latitude', 'current_longitude',
        'total_deliveries', 'rating', 'documents', 'created_at', 'updated_at'
    ]
    
    serializer_fields = set(serializer.fields.keys())
    for field in expected_fields:
        if field in serializer_fields:
            print(f"✓ RiderProfileSerializer.{field} exists")
        else:
            print(f"✗ RiderProfileSerializer.{field} MISSING")
            return False
    
    # Check is_phone_verified and review_status are included
    if 'is_phone_verified' in serializer_fields:
        print("✓ is_phone_verified field included in response")
    else:
        print("✗ is_phone_verified field MISSING")
        return False
    
    if 'review_status' in serializer_fields:
        print("✓ review_status field included in response")
    else:
        print("✗ review_status field MISSING")
        return False
    
    return True


def test_urls():
    """Test URL configuration"""
    print("\n" + "=" * 60)
    print("TESTING URLS")
    print("=" * 60)
    
    from django.urls import reverse
    from django.conf import settings
    
    # Check if riders app is in INSTALLED_APPS
    if 'apps.riders' in settings.INSTALLED_APPS:
        print("✓ apps.riders in INSTALLED_APPS")
    else:
        print("✗ apps.riders NOT in INSTALLED_APPS")
        return False
    
    # Test URL patterns
    try:
        from apps.riders import urls
        url_patterns = urls.urlpatterns
        
        expected_urls = [
            'register', 'send-otp', 'verify-otp',
            'profile', 'profile-submit', 'profile-status',
            'documents-list', 'document-upload', 'document-delete',
            'available-orders', 'my-orders', 'order-detail',
            'accept-order', 'add-measurements', 'update-status',
            'admin-reviews', 'admin-review-detail'
        ]
        
        url_names = [pattern.name for pattern in url_patterns if pattern.name]
        for url_name in expected_urls:
            if url_name in url_names:
                print(f"✓ URL '{url_name}' configured")
            else:
                print(f"✗ URL '{url_name}' MISSING")
                return False
    except Exception as e:
        print(f"✗ URL configuration error: {e}")
        return False
    
    return True


def test_admin():
    """Test admin configuration"""
    print("\n" + "=" * 60)
    print("TESTING ADMIN")
    print("=" * 60)
    
    from django.contrib import admin
    from apps.riders.models import (
        RiderProfile, 
        RiderProfileReview, 
        RiderDocument, 
        RiderOrderAssignment
    )
    
    # Check if models are registered
    if RiderProfile in admin.site._registry:
        print("✓ RiderProfile registered in admin")
    else:
        print("✗ RiderProfile NOT registered in admin")
        return False
    
    if RiderProfileReview in admin.site._registry:
        print("✓ RiderProfileReview registered in admin")
    else:
        print("✗ RiderProfileReview NOT registered in admin")
        return False
    
    if RiderDocument in admin.site._registry:
        print("✓ RiderDocument registered in admin")
    else:
        print("✗ RiderDocument NOT registered in admin")
        return False
    
    return True


def test_views():
    """Test view classes"""
    print("\n" + "=" * 60)
    print("TESTING VIEWS")
    print("=" * 60)
    
    from apps.riders.views import (
        RiderProfileView,
        RiderDocumentUploadView,
        RiderAvailableOrdersView,
    )
    
    # Check if views have required methods
    if hasattr(RiderProfileView, 'get'):
        print("✓ RiderProfileView.get() exists")
    else:
        print("✗ RiderProfileView.get() MISSING")
        return False
    
    if hasattr(RiderProfileView, 'put'):
        print("✓ RiderProfileView.put() exists")
    else:
        print("✗ RiderProfileView.put() MISSING")
        return False
    
    if hasattr(RiderDocumentUploadView, 'post'):
        print("✓ RiderDocumentUploadView.post() exists")
    else:
        print("✗ RiderDocumentUploadView.post() MISSING")
        return False
    
    # Check approval check in RiderAvailableOrdersView
    import inspect
    source = inspect.getsource(RiderAvailableOrdersView.get)
    if 'is_approved' in source:
        print("✓ RiderAvailableOrdersView checks is_approved")
    else:
        print("✗ RiderAvailableOrdersView does NOT check is_approved")
        return False
    
    return True


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("RIDER SYSTEM IMPLEMENTATION TEST")
    print("=" * 60)
    print("\nTesting all components implemented in this session...\n")
    
    tests = [
        ("Imports", test_imports),
        ("Models", test_models),
        ("Serializers", test_serializers),
        ("URLs", test_urls),
        ("Admin", test_admin),
        ("Views", test_views),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ {test_name} test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{test_name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Implementation is complete.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review the errors above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())

