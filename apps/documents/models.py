from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import BaseModel
from apps.documents.catalog import (
    DEFAULT_TEMPLATE_NAME,
    DEFAULT_TEMPLATE_SLUG,
    SECTION_CHOICES,
    SECTION_KEYS,
)


class PdfDocumentTemplate(BaseModel):
    """Versioned layout for a complete printable order document."""

    ENGINE_CHOICES = (
        ('auto', 'Auto (HTML, fall back to ReportLab)'),
        ('html', 'HTML template'),
        ('reportlab', 'Legacy ReportLab'),
    )

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=80, default=DEFAULT_TEMPLATE_SLUG, db_index=True)
    version = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(
        default=False,
        help_text='Used when no template slug is requested.',
    )
    engine = models.CharField(max_length=20, choices=ENGINE_CHOICES, default='auto')
    notes = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-is_default', 'name', '-version']
        verbose_name = 'PDF document template'
        verbose_name_plural = 'PDF document templates'
        constraints = [
            models.UniqueConstraint(
                fields=['slug', 'version'],
                name='documents_template_slug_version_uniq',
            ),
        ]

    def __str__(self):
        return f'{self.name} v{self.version}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_default:
            type(self).objects.exclude(pk=self.pk).filter(is_default=True).update(is_default=False)

    def visible_sections(self):
        return self.sections.filter(is_visible=True).order_by('display_order', 'id')


class PdfDocumentSection(BaseModel):
    """One block in an order PDF. Reorder or hide from admin without a deploy."""

    template = models.ForeignKey(
        PdfDocumentTemplate,
        on_delete=models.CASCADE,
        related_name='sections',
    )
    key = models.CharField(max_length=40, choices=SECTION_CHOICES)
    display_order = models.PositiveIntegerField(default=0)
    is_visible = models.BooleanField(default=True)
    settings = models.JSONField(
        default=dict,
        blank=True,
        help_text='Optional JSON, e.g. {"hide_if_empty": true, "measurement_cols": 5}.',
    )

    class Meta:
        ordering = ['display_order', 'id']
        verbose_name = 'PDF document section'
        verbose_name_plural = 'PDF document sections'
        constraints = [
            models.UniqueConstraint(
                fields=['template', 'key'],
                name='documents_section_template_key_uniq',
            ),
        ]

    def __str__(self):
        return f'{self.template.slug}:{self.key}'

    def clean(self):
        if self.key not in SECTION_KEYS:
            raise ValidationError({'key': 'Unknown document section.'})
        if self.settings is not None and not isinstance(self.settings, dict):
            raise ValidationError({'settings': 'Settings must be a JSON object.'})
