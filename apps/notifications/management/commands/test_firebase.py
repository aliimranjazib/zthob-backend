from django.core.management.base import BaseCommand
from django.conf import settings
import os
from apps.notifications.services import get_firebase_app


class Command(BaseCommand):
    help = 'Test Firebase initialization and configuration'

    def handle(self, *args, **options):
        self.stdout.write("=" * 60)
        self.stdout.write("Firebase Configuration Test")
        self.stdout.write("=" * 60)
        
        # Check settings
        self.stdout.write("\n1. Checking Settings...")
        project_id = getattr(settings, 'FIREBASE_PROJECT_ID', None)
        if project_id:
            self.stdout.write(self.style.SUCCESS(f"   ✅ FIREBASE_PROJECT_ID: {project_id}"))
        else:
            self.stdout.write(self.style.ERROR("   ❌ FIREBASE_PROJECT_ID not set in settings.py"))
        
        # Check credentials file
        self.stdout.write("\n2. Checking Credentials File...")
        cred_path = getattr(settings, 'FIREBASE_CREDENTIALS_PATH', None)
        if cred_path:
            if os.path.exists(cred_path):
                self.stdout.write(self.style.SUCCESS(f"   ✅ Credentials file exists: {cred_path}"))
                # Check if file is readable
                try:
                    with open(cred_path, 'r') as f:
                        import json
                        cred_data = json.load(f)
                        if cred_data.get('type') == 'service_account':
                            self.stdout.write(self.style.SUCCESS(f"   ✅ Valid service account JSON file"))
                            if cred_data.get('project_id'):
                                self.stdout.write(self.style.SUCCESS(f"   ✅ Project ID in JSON: {cred_data.get('project_id')}"))
                                if cred_data.get('project_id') != project_id:
                                    self.stdout.write(self.style.WARNING(f"   ⚠️  Project ID mismatch! JSON: {cred_data.get('project_id')}, settings: {project_id}"))
                        else:
                            self.stdout.write(self.style.WARNING(f"   ⚠️  File type: {cred_data.get('type')} (expected: service_account)"))
                except json.JSONDecodeError:
                    self.stdout.write(self.style.ERROR(f"   ❌ Invalid JSON file"))
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"   ⚠️  Could not read file: {str(e)}"))
            else:
                self.stdout.write(self.style.ERROR(f"   ❌ Credentials file not found: {cred_path}"))
        else:
            self.stdout.write(self.style.ERROR("   ❌ FIREBASE_CREDENTIALS_PATH not set in .env file"))
            self.stdout.write(self.style.WARNING("   Set FIREBASE_CREDENTIALS_PATH in .env to point to your service account JSON file"))
        
        # Test Firebase initialization
        self.stdout.write("\n3. Testing Firebase Initialization...")
        try:
            app = get_firebase_app()
            if app:
                self.stdout.write(self.style.SUCCESS(f"   ✅ Firebase initialized successfully!"))
                self.stdout.write(self.style.SUCCESS(f"   ✅ Project ID: {app.project_id}"))
                self.stdout.write("\n" + "=" * 60)
                self.stdout.write(self.style.SUCCESS("Firebase is ready to send notifications!"))
                self.stdout.write("=" * 60)
            else:
                self.stdout.write(self.style.ERROR("   ❌ Firebase not initialized"))
                self.stdout.write(self.style.WARNING("\n   Troubleshooting:"))
                self.stdout.write("   1. Set FIREBASE_CREDENTIALS_PATH in .env to point to your service account JSON file")
                self.stdout.write("   2. Verify FIREBASE_PROJECT_ID in settings.py (should be 'mgask-2025')")
                self.stdout.write("   3. Ensure the JSON file exists and is readable")
                self.stdout.write("   4. Check Django logs for detailed error messages")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   ❌ Error initializing Firebase: {str(e)}"))
            self.stdout.write(self.style.WARNING("\n   Troubleshooting:"))
            self.stdout.write("   1. Set FIREBASE_CREDENTIALS_PATH in .env to point to your service account JSON file")
            self.stdout.write("   2. Verify FIREBASE_PROJECT_ID in settings.py (should be 'mgask-2025')")
            self.stdout.write("   3. Ensure the JSON file exists and is readable")
            self.stdout.write("   4. Check Django logs for detailed error messages")
        
        self.stdout.write("")

