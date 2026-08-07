"""Regression tests for core.0012_phoneverification_otp_session migration."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connection
from django.test import TransactionTestCase
from django.utils import timezone

MIGRATE_TO = '0012_phoneverification_otp_session'


def _reset_core_to_pre_0012():
    """Undo 0012 in the test DB without using the broken reverse AlterField migration."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            ALTER TABLE core_phoneverification
            DROP COLUMN IF EXISTS session_id,
            DROP COLUMN IF EXISTS attempt_count,
            DROP COLUMN IF EXISTS invalidated_at,
            DROP COLUMN IF EXISTS resend_available_at,
            DROP COLUMN IF EXISTS otp_hash
            """
        )
        cursor.execute(
            """
            DELETE FROM django_migrations
            WHERE app = 'core' AND name = %s
            """,
            [MIGRATE_TO],
        )


def _create_pre_0012_verifications(user_id, phone_numbers, expires_at):
    with connection.cursor() as cursor:
        for phone_number in phone_numbers:
            cursor.execute(
                """
                INSERT INTO core_phoneverification (
                    user_id,
                    phone_number,
                    expires_at,
                    is_verified,
                    created_at
                )
                VALUES (%s, %s, %s, FALSE, NOW())
                """,
                [user_id, phone_number, expires_at],
            )


class PhoneVerificationMigration0012Tests(TransactionTestCase):
    def test_migration_assigns_unique_session_ids_for_existing_rows(self):
        _reset_core_to_pre_0012()

        user = get_user_model().objects.create_user(
            username='migration_otp_user',
            phone='0500999888',
            email=None,
        )
        expires = timezone.now() + timedelta(minutes=5)
        _create_pre_0012_verifications(
            user.id,
            [f'+96650000000{index}' for index in range(5)],
            expires,
        )

        call_command('migrate', 'core', MIGRATE_TO, verbosity=0)

        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT session_id FROM core_phoneverification ORDER BY id'
            )
            session_ids = [row[0] for row in cursor.fetchall()]

        self.assertEqual(len(session_ids), 5)
        self.assertEqual(len(set(session_ids)), 5)
        self.assertTrue(all(session_id is not None for session_id in session_ids))
