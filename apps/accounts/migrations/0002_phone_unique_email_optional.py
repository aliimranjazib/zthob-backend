# Generated migration for phone-based authentication

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        # Make email optional (nullable)
        migrations.AlterField(
            model_name='customuser',
            name='email',
            field=models.EmailField(blank=True, max_length=100, null=True, unique=True),
        ),
        # Add unique constraint to phone (only for non-null values)
        # First, ensure all existing phone values are unique or null
        migrations.RunSQL(
            # Set duplicate phone numbers to null (keeping first occurrence)
            sql="""
                UPDATE accounts_customuser 
                SET phone = NULL 
                WHERE id NOT IN (
                    SELECT MIN(id) 
                    FROM accounts_customuser 
                    WHERE phone IS NOT NULL AND phone != ''
                    GROUP BY phone
                ) AND phone IS NOT NULL AND phone != '';
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
        # Now add unique constraint with null handling
        migrations.AlterField(
            model_name='customuser',
            name='phone',
            field=models.CharField(blank=True, db_index=True, max_length=15, null=True, unique=True),
        ),
        # Remove email from REQUIRED_FIELDS (handled in model, but migration ensures consistency)
    ]

