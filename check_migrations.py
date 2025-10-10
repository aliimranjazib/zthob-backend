#!/usr/bin/env python3
"""
Migration Check Script for Zthob Django App
This script helps debug migration issues in production
"""

import os
import sys
import django
from django.core.management import execute_from_command_line

def check_migrations():
    """Check migration status and show any issues"""
    print("🔍 Checking Django Migration Status...")
    print("=" * 50)
    
    # Set Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zthob.settings')
    django.setup()
    
    from django.db import connection
    from django.core.management.commands import showmigrations
    
    print("📋 Current Migration Status:")
    print("-" * 30)
    
    # Show migration status
    execute_from_command_line(['manage.py', 'showmigrations'])
    
    print("\n🗄️ Database Tables:")
    print("-" * 20)
    
    # Check if required tables exist
    with connection.cursor() as cursor:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        required_tables = [
            'tailors_fabrictype',
            'tailors_fabriccategory', 
            'tailors_fabric',
            'tailors_fabricimage',
            'tailors_tailorprofile'
        ]
        
        for table in required_tables:
            if table in tables:
                print(f"✅ {table}")
            else:
                print(f"❌ {table} - MISSING!")
    
    print("\n🔧 To fix missing tables, run:")
    print("python manage.py migrate")

if __name__ == "__main__":
    check_migrations()
