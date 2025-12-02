#!/usr/bin/env python3
"""
Database Reset Script for Zthob Django App
This script creates a fresh database state for production
"""

import os
import sys
import django
from django.core.management import execute_from_command_line

def reset_database():
    """Reset database to a clean state"""
    print("🔄 Resetting Database to Clean State...")
    print("=" * 50)
    
    # Set Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zthob.settings')
    django.setup()
    
    # CRITICAL SAFETY CHECK: Prevent running in production
    from django.conf import settings
    environment = os.getenv('DJANGO_ENVIRONMENT', 'development')
    
    if environment == 'production':
        print("=" * 50)
        print("🚨 CRITICAL ERROR: Database reset is BLOCKED in production!")
        print("=" * 50)
        print("This script will DELETE ALL PRODUCTION DATA!")
        print("If you need to reset production database:")
        print("1. Create a full backup first")
        print("2. Manually set DJANGO_ENVIRONMENT=development (temporarily)")
        print("3. Or use database-specific tools (pg_dump, etc.)")
        print("=" * 50)
        sys.exit(1)
    
    print("⚠️  WARNING: This will reset your database!")
    print("Make sure you have backups before proceeding.")
    print(f"Environment: {environment}")
    
    # Backup current database
    import shutil
    from datetime import datetime
    
    backup_name = f"db_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sqlite3"
    if os.path.exists('db.sqlite3'):
        shutil.copy('db.sqlite3', backup_name)
        print(f"✅ Database backed up as {backup_name}")
    
    # Remove current database
    if os.path.exists('db.sqlite3'):
        os.remove('db.sqlite3')
        print("🗑️  Removed old database")
    
    # Create fresh database
    print("🆕 Creating fresh database...")
    execute_from_command_line(['manage.py', 'migrate'])
    
    print("✅ Fresh database created successfully!")
    
    # Create superuser if needed
    print("\n👤 You may want to create a superuser:")
    print("python manage.py createsuperuser")

if __name__ == "__main__":
    reset_database()
