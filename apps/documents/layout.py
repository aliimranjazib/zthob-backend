"""Resolve the active document layout from the database, with a safe catalog fallback."""

from apps.documents.catalog import (
    DEFAULT_SECTION_SETTINGS,
    DEFAULT_TEMPLATE_NAME,
    DEFAULT_TEMPLATE_SLUG,
    default_sections,
)


class ResolvedSection:
    __slots__ = ('key', 'display_order', 'is_visible', 'settings')

    def __init__(self, key, display_order, is_visible=True, settings=None):
        merged = dict(DEFAULT_SECTION_SETTINGS.get(key, {}))
        if isinstance(settings, dict):
            merged.update(settings)
        self.key = key
        self.display_order = display_order
        self.is_visible = is_visible
        self.settings = merged


class ResolvedLayout:
    __slots__ = ('slug', 'name', 'version', 'engine', 'sections')

    def __init__(self, slug, name, version, engine, sections):
        self.slug = slug
        self.name = name
        self.version = version
        self.engine = engine
        ordered = sorted(sections, key=lambda section: (section.display_order, section.key))
        self.sections = [section for section in ordered if section.is_visible]


def _catalog_layout(engine='auto'):
    return ResolvedLayout(
        slug=DEFAULT_TEMPLATE_SLUG,
        name=DEFAULT_TEMPLATE_NAME,
        version=1,
        engine=engine,
        sections=[
            ResolvedSection(
                key=item['key'],
                display_order=item['display_order'],
                is_visible=item['is_visible'],
                settings=item['settings'],
            )
            for item in default_sections()
        ],
    )


def resolve_layout(template=None):
    """Return a ResolvedLayout from a PdfDocumentTemplate, or catalog defaults."""
    if template is None:
        try:
            from apps.documents.models import PdfDocumentTemplate
            template = (
                PdfDocumentTemplate.objects.filter(is_active=True, is_default=True)
                .prefetch_related('sections')
                .first()
            )
            if template is None:
                template = (
                    PdfDocumentTemplate.objects.filter(is_active=True)
                    .prefetch_related('sections')
                    .order_by('-version', 'id')
                    .first()
                )
        except Exception:
            return _catalog_layout()

    if template is None:
        return _catalog_layout()

    db_sections = list(template.sections.all())
    if not db_sections:
        return _catalog_layout(engine=template.engine)

    sections = [
        ResolvedSection(
            key=section.key,
            display_order=section.display_order,
            is_visible=section.is_visible,
            settings=section.settings or {},
        )
        for section in sorted(db_sections, key=lambda item: (item.display_order, item.id))
    ]
    return ResolvedLayout(
        slug=template.slug,
        name=template.name,
        version=template.version,
        engine=template.engine,
        sections=sections,
    )


def resolve_layout_from_draft(template_meta, sections_data):
    """
    Build a ResolvedLayout from studio draft data without saving.

    sections_data: list of dicts with key, display_order, is_visible, settings
    template_meta: dict with slug, name, version, engine (optional)
    """
    ordered_data = sorted(
        sections_data,
        key=lambda item: (int(item.get('display_order', 0)), item.get('key', '')),
    )
    sections = [
        ResolvedSection(
            key=item['key'],
            display_order=int(item.get('display_order', index)),
            is_visible=bool(item.get('is_visible', True)),
            settings=item.get('settings') or {},
        )
        for index, item in enumerate(ordered_data, start=1)
    ]
    meta = template_meta or {}
    return ResolvedLayout(
        slug=meta.get('slug', DEFAULT_TEMPLATE_SLUG),
        name=meta.get('name', DEFAULT_TEMPLATE_NAME),
        version=int(meta.get('version', 1)),
        engine=meta.get('engine', 'auto'),
        sections=sections,
    )
