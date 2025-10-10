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
    
    print("⚠️  WARNING: This will reset your database!")
    print("Make sure you have backups before proceeding.")
    
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
