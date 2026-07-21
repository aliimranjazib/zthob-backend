from django.conf import settings
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('orders', '0037_myfatoorah_payment_attempts'),
    ]

    operations = [
        migrations.CreateModel(
            name='StyleReferenceImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('image', models.ImageField(help_text='Customer/tailor/rider reference photo for a style selection', upload_to='style_references/%Y/%m/', validators=[django.core.validators.FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp'])])),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_created', to=settings.AUTH_USER_MODEL)),
                ('uploaded_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='style_reference_images', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Style Reference Image',
                'verbose_name_plural': 'Style Reference Images',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='stylereferenceimage',
            index=models.Index(fields=['uploaded_by', 'created_at'], name='orders_styl_upload__8f0a2d_idx'),
        ),
    ]
