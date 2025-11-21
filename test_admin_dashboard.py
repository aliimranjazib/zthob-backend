"""
Comprehensive Admin Dashboard Test Suite
Tests all aspects of the Django admin dashboard for usability and functionality
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zthob.settings')
django.setup()

from django.contrib import admin
from django.contrib.admin.sites import site
from django.apps import apps
from django.urls import reverse
from django.test import Client
from django.contrib.auth import get_user_model

User = get_user_model()

def print_header(title):
    """Print formatted header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def print_success(message):
    """Print success message"""
    print(f"✓ {message}")

def print_error(message):
    """Print error message"""
    print(f"✗ {message}")

def print_warning(message):
    """Print warning message"""
    print(f"⚠ {message}")

def print_info(message):
    """Print info message"""
    print(f"ℹ {message}")

def test_model_registrations():
    """Test if all models are registered in admin"""
    print_header("TEST 1: Model Admin Registrations")
    
    issues = []
    
    # Get all models from installed apps
    all_models = {}
    for app_config in apps.get_app_configs():
        if app_config.name.startswith('apps.'):
            for model in app_config.get_models():
                all_models[model.__name__] = {
                    'model': model,
                    'app': app_config.name,
                    'app_label': app_config.label
                }
    
    # Models that should be registered
    models_to_check = [
        'CustomUser',
        'CustomerProfile',
        'Address',
        'FamilyMember',
        'TailorProfile',
        'Fabric',
        'FabricCategory',
        'FabricType',
        'FabricTag',
        'FabricImage',
        'TailorProfileReview',
        'ServiceArea',
        'Order',
        'OrderItem',
        'OrderStatusHistory',
        'RiderProfile',
        'RiderOrderAssignment',
        'RiderProfileReview',
        'RiderDocument',
        'SystemSettings',
        'Slider',
        'FCMDeviceToken',
        'NotificationLog',
    ]
    
    registered_count = 0
    unregistered_count = 0
    
    for model_name in models_to_check:
        if model_name in all_models:
            model = all_models[model_name]['model']
            if model in admin.site._registry:
                print_success(f"{model_name} is registered")
                registered_count += 1
            else:
                print_error(f"{model_name} is NOT registered in admin")
                issues.append(f"Model {model_name} is not registered in admin")
                unregistered_count += 1
        else:
            print_warning(f"{model_name} model not found in codebase")
    
    print_info(f"\nRegistered: {registered_count}/{len(models_to_check)}")
    if unregistered_count > 0:
        print_error(f"Unregistered: {unregistered_count}")
    
    return len(issues) == 0

def test_jazzmin_icons():
    """Test Jazzmin icon configuration"""
    print_header("TEST 2: Jazzmin Icon Configuration")
    
    from zthob.settings import JAZZMIN_SETTINGS
    
    issues = []
    icons = JAZZMIN_SETTINGS.get('icons', {})
    
    # Check if all registered models have icons
    registered_models = []
    for model, admin_class in admin.site._registry.items():
        app_label = model._meta.app_label
        model_name = model.__name__
        key = f"{app_label}.{model_name}"
        registered_models.append(key)
        
        if key not in icons:
            print_warning(f"Missing icon for {key}")
            issues.append(f"Missing icon for {key}")
        else:
            print_success(f"Icon configured for {key}: {icons[key]}")
    
    print_info(f"\nTotal registered models: {len(registered_models)}")
    print_info(f"Models with icons: {len([k for k in registered_models if k in icons])}")
    print_info(f"Models without icons: {len(issues)}")
    
    return len(issues) == 0

def test_admin_list_display():
    """Test admin list display configurations"""
    print_header("TEST 3: Admin List Display Configuration")
    
    issues = []
    
    for model, admin_class in admin.site._registry.items():
        model_name = model.__name__
        
        # Check if list_display is configured
        if hasattr(admin_class, 'list_display'):
            list_display = admin_class.list_display
            if list_display and len(list_display) > 0:
                print_success(f"{model_name}: list_display configured ({len(list_display)} fields)")
            else:
                print_warning(f"{model_name}: list_display is empty")
                issues.append(f"{model_name} has empty list_display")
        else:
            print_warning(f"{model_name}: No list_display attribute")
            issues.append(f"{model_name} missing list_display")
    
    return len(issues) == 0

def test_admin_search_fields():
    """Test admin search field configurations"""
    print_header("TEST 4: Admin Search Fields Configuration")
    
    issues = []
    
    for model, admin_class in admin.site._registry.items():
        model_name = model.__name__
        
        if hasattr(admin_class, 'search_fields'):
            search_fields = admin_class.search_fields
            if search_fields and len(search_fields) > 0:
                print_success(f"{model_name}: search_fields configured ({len(search_fields)} fields)")
            else:
                print_warning(f"{model_name}: No search_fields configured")
                issues.append(f"{model_name} missing search_fields")
        else:
            print_warning(f"{model_name}: No search_fields attribute")
            issues.append(f"{model_name} missing search_fields")
    
    return len(issues) == 0

def test_admin_filters():
    """Test admin filter configurations"""
    print_header("TEST 5: Admin Filter Configuration")
    
    issues = []
    
    for model, admin_class in admin.site._registry.items():
        model_name = model.__name__
        
        if hasattr(admin_class, 'list_filter'):
            list_filter = admin_class.list_filter
            if list_filter and len(list_filter) > 0:
                print_success(f"{model_name}: list_filter configured ({len(list_filter)} filters)")
            else:
                print_warning(f"{model_name}: No list_filter configured")
                # Not critical, just a warning
        else:
            print_info(f"{model_name}: No list_filter (optional)")
    
    return True

def test_admin_actions():
    """Test admin bulk actions"""
    print_header("TEST 6: Admin Bulk Actions")
    
    actions_found = 0
    
    for model, admin_class in admin.site._registry.items():
        model_name = model.__name__
        
        if hasattr(admin_class, 'actions'):
            actions = admin_class.actions
            if actions and len(actions) > 0:
                print_success(f"{model_name}: {len(actions)} bulk action(s) configured")
                actions_found += len(actions)
            else:
                print_info(f"{model_name}: No bulk actions (optional)")
        else:
            print_info(f"{model_name}: No actions attribute")
    
    print_info(f"\nTotal bulk actions found: {actions_found}")
    return True

def test_jazzmin_settings():
    """Test Jazzmin configuration"""
    print_header("TEST 7: Jazzmin Settings Configuration")
    
    from zthob.settings import JAZZMIN_SETTINGS
    
    issues = []
    
    # Check required settings
    required_settings = [
        'site_title',
        'site_header',
        'site_brand',
        'welcome_sign',
    ]
    
    for setting in required_settings:
        if setting in JAZZMIN_SETTINGS:
            print_success(f"{setting}: {JAZZMIN_SETTINGS[setting]}")
        else:
            print_error(f"Missing {setting}")
            issues.append(f"Missing JAZZMIN_SETTINGS['{setting}']")
    
    # Check menu order
    if 'order_with_respect_to' in JAZZMIN_SETTINGS:
        order = JAZZMIN_SETTINGS['order_with_respect_to']
        print_success(f"Menu order configured: {order}")
    else:
        print_warning("Menu order not configured")
        issues.append("Missing menu order configuration")
    
    # Check icons
    if 'icons' in JAZZMIN_SETTINGS:
        icon_count = len(JAZZMIN_SETTINGS['icons'])
        print_success(f"Icons configured: {icon_count}")
    else:
        print_warning("No icons configured")
    
    return len(issues) == 0

def test_admin_urls():
    """Test admin URL accessibility"""
    print_header("TEST 8: Admin URL Accessibility")
    
    issues = []
    
    # Test if admin URLs are accessible
    try:
        from django.urls import resolve
        from django.urls.exceptions import NoReverseMatch
        
        for model, admin_class in admin.site._registry.items():
            model_name = model.__name__
            app_label = model._meta.app_label
            
            try:
                # Test changelist URL
                changelist_url = reverse(f'admin:{app_label}_{model_name.lower()}_changelist')
                print_success(f"{model_name}: Changelist URL accessible")
            except NoReverseMatch:
                print_error(f"{model_name}: Changelist URL not accessible")
                issues.append(f"{model_name} changelist URL issue")
            except Exception as e:
                print_warning(f"{model_name}: URL check error - {str(e)}")
    
    except Exception as e:
        print_error(f"Error testing URLs: {str(e)}")
        issues.append("URL testing failed")
    
    return len(issues) == 0

def test_admin_readonly_fields():
    """Test readonly fields configuration"""
    print_header("TEST 9: Admin Readonly Fields")
    
    issues = []
    
    for model, admin_class in admin.site._registry.items():
        model_name = model.__name__
        
        if hasattr(admin_class, 'readonly_fields'):
            readonly_fields = admin_class.readonly_fields
            if readonly_fields and len(readonly_fields) > 0:
                print_success(f"{model_name}: {len(readonly_fields)} readonly field(s)")
            else:
                print_info(f"{model_name}: No readonly fields (optional)")
        else:
            print_info(f"{model_name}: No readonly_fields attribute")
    
    return True

def test_admin_fieldsets():
    """Test fieldsets configuration"""
    print_header("TEST 10: Admin Fieldsets Configuration")
    
    issues = []
    
    for model, admin_class in admin.site._registry.items():
        model_name = model.__name__
        
        if hasattr(admin_class, 'fieldsets'):
            fieldsets = admin_class.fieldsets
            if fieldsets and len(fieldsets) > 0:
                print_success(f"{model_name}: Fieldsets configured ({len(fieldsets)} sections)")
            else:
                print_warning(f"{model_name}: No fieldsets (using default)")
        else:
            print_info(f"{model_name}: No fieldsets attribute (using default)")
    
    return True

def generate_report():
    """Generate comprehensive test report"""
    print_header("ADMIN DASHBOARD TEST REPORT")
    
    results = {
        'Model Registrations': test_model_registrations(),
        'Jazzmin Icons': test_jazzmin_icons(),
        'List Display': test_admin_list_display(),
        'Search Fields': test_admin_search_fields(),
        'Filters': test_admin_filters(),
        'Bulk Actions': test_admin_actions(),
        'Jazzmin Settings': test_jazzmin_settings(),
        'Admin URLs': test_admin_urls(),
        'Readonly Fields': test_admin_readonly_fields(),
        'Fieldsets': test_admin_fieldsets(),
    }
    
    print_header("TEST SUMMARY")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        symbol = "✓" if result else "✗"
        print(f"{symbol} {test_name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print_success("All tests passed!")
    else:
        print_error(f"{total - passed} test(s) failed")
    
    return results

if __name__ == '__main__':
    try:
        results = generate_report()
        sys.exit(0 if all(results.values()) else 1)
    except Exception as e:
        print_error(f"Test execution failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

