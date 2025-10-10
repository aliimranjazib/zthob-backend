#!/usr/bin/env python3
"""
Migration Fix Script for Zthob Django App
This script helps fix migration dependency issues
"""

import os
import sys
import django
from django.core.management import execute_from_command_line

def fix_migrations():
    """Fix migration issues by applying them in the correct order"""
    print("🔧 Fixing Migration Issues...")
    print("=" * 50)
    
    # Set Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zthob.settings')
    django.setup()
    
    from django.db import connection
    
    print("📋 Current Migration Status:")
    print("-" * 30)
    execute_from_command_line(['manage.py', 'showmigrations'])
    
    print("\n🔧 Attempting to fix migrations...")
    print("-" * 40)
    
    # Try to apply migrations with fake-initial to handle dependencies
    try:
        print("Step 1: Applying migrations with fake-initial...")
        execute_from_command_line(['manage.py', 'migrate', '--fake-initial'])
        print("✅ Fake-initial migration completed")
    except Exception as e:
        print(f"❌ Fake-initial failed: {e}")
    
    # Try normal migration
    try:
        print("Step 2: Applying remaining migrations...")
        execute_from_command_line(['manage.py', 'migrate'])
        print("✅ Normal migration completed")
    except Exception as e:
        print(f"❌ Normal migration failed: {e}")
        print("Step 3: Trying to reset problematic migrations...")
        
        # Reset specific problematic migrations
        problematic_migrations = [
            'orders.0002_alter_order_created_by_alter_orderitem_created_by_and_more',
            'orders.0003_alter_order_tailor',
            'orders.0004_order_order_type',
            'orders.0005_order_family_member',
            'tailors.0007_alter_fabric_created_by',
            'tailors.0008_fabric_seasons',
            'tailors.0009_fabrictype_fabric_fabric_type',
            'tailors.0010_alter_fabric_options_alter_fabriccategory_options_and_more'
        ]
        
        for migration in problematic_migrations:
            try:
                print(f"Resetting {migration}...")
                execute_from_command_line(['manage.py', 'migrate', migration, 'zero', '--fake'])
            except Exception as e:
                print(f"Could not reset {migration}: {e}")
        
        # Try migration again
        try:
            execute_from_command_line(['manage.py', 'migrate'])
            print("✅ Migration completed after reset")
        except Exception as e:
            print(f"❌ Migration still failed: {e}")
            return False
    
    print("\n📋 Final Migration Status:")
    print("-" * 30)
    execute_from_command_line(['manage.py', 'showmigrations'])
    
    print("\n🗄️ Database Tables Check:")
    print("-" * 25)
    
    # Check if required tables exist
    with connection.cursor() as cursor:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        required_tables = [
            'tailors_fabrictype',
            'tailors_fabriccategory', 
            'tailors_fabric',
            'tailors_fabricimage',
            'tailors_tailorprofile',
            'orders_order',
            'orders_orderitem'
        ]
        
        all_good = True
        for table in required_tables:
            if table in tables:
                print(f"✅ {table}")
            else:
                print(f"❌ {table} - MISSING!")
                all_good = False
        
        if all_good:
            print("\n🎉 All required tables exist!")
            return True
        else:
            print("\n❌ Some tables are still missing!")
            return False

if __name__ == "__main__":
    success = fix_migrations()
    sys.exit(0 if success else 1)
