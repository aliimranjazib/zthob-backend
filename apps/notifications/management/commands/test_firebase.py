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
        
        # Check environment variables
        self.stdout.write("\n2. Checking Environment Variables...")
        env_project = os.environ.get('GOOGLE_CLOUD_PROJECT') or os.environ.get('FIREBASE_PROJECT_ID')
        if env_project:
            self.stdout.write(self.style.SUCCESS(f"   ✅ GOOGLE_CLOUD_PROJECT: {env_project}"))
        else:
            self.stdout.write(self.style.WARNING("   ⚠️  GOOGLE_CLOUD_PROJECT not set (using settings.py)"))
        
        # Check credentials file
        self.stdout.write("\n3. Checking Credentials File...")
        cred_path = getattr(settings, 'FIREBASE_CREDENTIALS_PATH', None)
        if cred_path:
            if os.path.exists(cred_path):
                self.stdout.write(self.style.SUCCESS(f"   ✅ Credentials file exists: {cred_path}"))
            else:
                self.stdout.write(self.style.WARNING(f"   ⚠️  Credentials file not found: {cred_path}"))
        else:
            self.stdout.write(self.style.SUCCESS("   ✅ Using Application Default Credentials (no file needed)"))
        
        # Check gcloud authentication
        self.stdout.write("\n4. Checking gcloud Authentication...")
        try:
            import subprocess
            result = subprocess.run(['gcloud', 'auth', 'list', '--filter=status:ACTIVE', '--format=value(account)'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                accounts = result.stdout.strip().split('\n')
                self.stdout.write(self.style.SUCCESS(f"   ✅ Active gcloud accounts: {', '.join(accounts)}"))
            else:
                self.stdout.write(self.style.WARNING("   ⚠️  No active gcloud accounts found"))
        except FileNotFoundError:
            self.stdout.write(self.style.WARNING("   ⚠️  gcloud CLI not found (install: brew install google-cloud-sdk)"))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"   ⚠️  Could not check gcloud: {str(e)}"))
        
        # Check gcloud project
        self.stdout.write("\n5. Checking gcloud Project...")
        try:
            import subprocess
            result = subprocess.run(['gcloud', 'config', 'get-value', 'project'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                gcloud_project = result.stdout.strip()
                self.stdout.write(self.style.SUCCESS(f"   ✅ gcloud project: {gcloud_project}"))
                if gcloud_project != project_id:
                    self.stdout.write(self.style.WARNING(f"   ⚠️  Project mismatch! gcloud: {gcloud_project}, settings: {project_id}"))
            else:
                self.stdout.write(self.style.WARNING("   ⚠️  No gcloud project set"))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"   ⚠️  Could not check gcloud project: {str(e)}"))
        
        # Test Firebase initialization
        self.stdout.write("\n6. Testing Firebase Initialization...")
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
                self.stdout.write("   1. Run: gcloud auth application-default login")
                self.stdout.write("   2. Run: gcloud config set project mgask-2025")
                self.stdout.write("   3. Check Django logs for detailed error messages")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   ❌ Error initializing Firebase: {str(e)}"))
            self.stdout.write(self.style.WARNING("\n   Troubleshooting:"))
            self.stdout.write("   1. Run: gcloud auth application-default login")
            self.stdout.write("   2. Run: gcloud config set project mgask-2025")
            self.stdout.write("   3. Check Django logs for detailed error messages")
        
        self.stdout.write("")

