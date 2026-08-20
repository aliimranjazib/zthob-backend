from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def seed_default_template(apps, schema_editor):
    from apps.documents.catalog import DEFAULT_TEMPLATE_NAME, DEFAULT_TEMPLATE_SLUG, default_sections

    PdfDocumentTemplate = apps.get_model('documents', 'PdfDocumentTemplate')
    PdfDocumentSection = apps.get_model('documents', 'PdfDocumentSection')
    template, _created = PdfDocumentTemplate.objects.get_or_create(
        slug=DEFAULT_TEMPLATE_SLUG,
        version=1,
        defaults={
            'name': DEFAULT_TEMPLATE_NAME,
            'is_active': True,
            'is_default': True,
            'engine': 'auto',
        },
    )
    if not template.is_default:
        template.is_default = True
        template.save(update_fields=['is_default'])

    for section in default_sections():
        PdfDocumentSection.objects.update_or_create(
            template=template,
            key=section['key'],
            defaults={
                'display_order': section['display_order'],
                'is_visible': section['is_visible'],
                'settings': section['settings'],
            },
        )


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PdfDocumentTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=100)),
                ('slug', models.SlugField(default='order_receipt', max_length=80)),
                ('version', models.PositiveIntegerField(default=1)),
                ('is_active', models.BooleanField(default=True)),
                ('is_default', models.BooleanField(default=False, help_text='Used when no template slug is requested.')),
                ('engine', models.CharField(choices=[('auto', 'Auto (HTML, fall back to ReportLab)'), ('html', 'HTML template'), ('reportlab', 'Legacy ReportLab')], default='auto', max_length=20)),
                ('notes', models.TextField(blank=True, default='')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_created', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'PDF document template',
                'verbose_name_plural': 'PDF document templates',
                'ordering': ['-is_default', 'name', '-version'],
            },
        ),
        migrations.CreateModel(
            name='PdfDocumentSection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('key', models.CharField(choices=[('header', 'Header'), ('customer', 'Customer information'), ('riders', 'Riders'), ('person_items', 'Items by person (fabric, styles, measurements)'), ('order_summary', 'Order summary'), ('notes', 'Notes & instructions'), ('status_history', 'Status history'), ('comments_footer', 'Comments & footer')], max_length=40)),
                ('display_order', models.PositiveIntegerField(default=0)),
                ('is_visible', models.BooleanField(default=True)),
                ('settings', models.JSONField(blank=True, default=dict, help_text='Optional JSON, e.g. {"hide_if_empty": true, "measurement_cols": 5}.')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_created', to=settings.AUTH_USER_MODEL)),
                ('template', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sections', to='documents.pdfdocumenttemplate')),
            ],
            options={
                'verbose_name': 'PDF document section',
                'verbose_name_plural': 'PDF document sections',
                'ordering': ['display_order', 'id'],
            },
        ),
        migrations.AddConstraint(
            model_name='pdfdocumenttemplate',
            constraint=models.UniqueConstraint(fields=('slug', 'version'), name='documents_template_slug_version_uniq'),
        ),
        migrations.AddConstraint(
            model_name='pdfdocumentsection',
            constraint=models.UniqueConstraint(fields=('template', 'key'), name='documents_section_template_key_uniq'),
        ),
        migrations.RunPython(seed_default_template, migrations.RunPython.noop),
    ]
