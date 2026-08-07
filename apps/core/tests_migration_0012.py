"""Regression tests for core.0012_phoneverification_otp_session migration."""

import importlib.util
import uuid
from datetime import timedelta
from pathlib import Path

from django.apps import apps as django_apps
from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone

from apps.core.models import PhoneVerification

MIGRATE_FROM = '0011_alter_phoneverification_otp_fields'
MIGRATE_TO = '0012_phoneverification_otp_session'


def _load_migration_module():
    path = Path(__file__).resolve().parent / 'migrations' / f'{MIGRATE_TO}.py'
    spec = importlib.util.spec_from_file_location('core_migration_0012', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PhoneVerificationMigration0012Tests(TransactionTestCase):
    def _executor(self):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        return executor

    def test_migration_assigns_unique_session_ids_for_existing_rows(self):
        executor = self._executor()
        executor.migrate([('core', MIGRATE_FROM)])

        apps = executor.loader.project_state().apps
        HistoricalPhoneVerification = apps.get_model('core', 'PhoneVerification')
        User = apps.get_model('accounts', 'User')

        user = User.objects.create_user(
            username='migration_otp_user',
            phone='0500999888',
            email=None,
        )
        expires = timezone.now() + timedelta(minutes=5)
        for index in range(5):
            HistoricalPhoneVerification.objects.create(
                user=user,
                phone_number=f'+96650000000{index}',
                expires_at=expires,
            )

        executor.migrate([('core', MIGRATE_TO)])

        apps = executor.loader.project_state().apps
        HistoricalPhoneVerification = apps.get_model('core', 'PhoneVerification')
        session_ids = list(
            HistoricalPhoneVerification.objects.values_list('session_id', flat=True)
        )

        self.assertEqual(len(session_ids), 5)
        self.assertEqual(len(set(session_ids)), 5)
        self.assertTrue(all(session_id is not None for session_id in session_ids))

    def test_assign_session_ids_fixes_duplicate_prefill(self):
        user = get_user_model().objects.create_user(
            username='migration_otp_dupe_user',
            phone='0500888777',
            email=None,
        )
        expires = timezone.now() + timedelta(minutes=5)
        rows = [
            PhoneVerification.objects.create(
                user=user,
                phone_number=f'+9665000000{index}',
                expires_at=expires,
            )
            for index in range(3)
        ]

        duplicate_session_id = uuid.uuid4()
        PhoneVerification.objects.filter(pk__in=[row.pk for row in rows]).update(
            session_id=duplicate_session_id,
        )

        migration_module = _load_migration_module()
        migration_module.assign_session_ids(django_apps, connection.schema_editor())

        session_ids = list(PhoneVerification.objects.values_list('session_id', flat=True))
        self.assertEqual(len(session_ids), 3)
        self.assertEqual(len(set(session_ids)), 3)
