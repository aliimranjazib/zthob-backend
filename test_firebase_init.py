#!/usr/bin/env python
"""Test Firebase initialization locally"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zthob.settings')
django.setup()

from apps.notifications.services import get_firebase_app
import traceback

print("=" * 60)
print("Testing Firebase Initialization")
print("=" * 60)

try:
    app = get_firebase_app()
    if app:
        print(f"✅ Firebase initialized successfully!")
        print(f"   Project ID: {app.project_id}")
        print("\n" + "=" * 60)
        print("✅ Firebase is ready to send notifications!")
        print("=" * 60)
    else:
        print("❌ Firebase not initialized")
        print("\nTroubleshooting:")
        print("1. Run: gcloud auth application-default login")
        print("2. Run: gcloud config set project mgask-2025")
        print("3. Check Django logs for detailed error messages")
except Exception as e:
    print(f"❌ Error initializing Firebase: {str(e)}")
    print("\nFull error details:")
    traceback.print_exc()
    print("\nTroubleshooting:")
    print("1. Run: gcloud auth application-default login")
    print("2. Run: gcloud config set project mgask-2025")
    print("3. Verify FIREBASE_PROJECT_ID in settings.py")

