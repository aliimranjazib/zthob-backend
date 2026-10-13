"""Resolve measurement forms: global platform template vs Tailor Plus shop overlay."""

from __future__ import annotations

import re
import secrets

from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.customization.models import (
    MeasurementField,
    MeasurementTemplate,
    ShopMeasurementField,
    ShopMeasurementSchema,
)
from apps.documents.measurement_config import get_pdf_measurement_template
from apps.orders.measurement_utils import measurement_field_values
from apps.tailors.models import TailorProfile
from apps.tailors.services.shop_plus import is_shop_plus_active

FIELD_NAME_PATTERN = re.compile(r'^[a-z][a-z0-9_]{0,47}$')
MAX_SHOP_MEASUREMENT_FIELDS = 50
CUSTOM_FIELD_NAME_PREFIX = 'sf_'


def get_default_measurement_template() -> MeasurementTemplate | None:
    return get_pdf_measurement_template()


def shop_has_custom_measurement_schema(shop: TailorProfile | int | None) -> bool:
    if shop is None:
        return False
    shop_id = shop if isinstance(shop, int) else shop.id
    if not is_shop_plus_active(shop_id):
        return False
    schema = (
        ShopMeasurementSchema.objects.filter(shop_id=shop_id)
        .prefetch_related('fields')
        .first()
    )
    if schema is None:
        return False
    return schema.fields.exists()


def _pick_label(global_field: MeasurementField | None, shop_row: ShopMeasurementField | None, attr: str, fallback: str):
    if shop_row is not None:
        value = getattr(shop_row, attr, '') or ''
        if value.strip():
            return value
    if global_field is not None:
        return getattr(global_field, attr, '') or fallback
    return fallback


def _resolved_field_dict(*, global_field: MeasurementField | None, shop_row: ShopMeasurementField | None, request):
    from apps.customization.serializers import MeasurementFieldSerializer

    if shop_row is not None and not shop_row.is_visible:
        return None

    if global_field is not None and shop_row is None:
        return MeasurementFieldSerializer(global_field, context={'request': request}).data

    if global_field is not None and shop_row is not None:
        payload = MeasurementFieldSerializer(global_field, context={'request': request}).data
        payload['id'] = shop_row.id
        payload['name'] = global_field.name
        payload['global_field_id'] = global_field.id
        payload['is_custom'] = False
        payload['display_name'] = _pick_label(
            global_field, shop_row, 'display_name', payload.get('display_name') or global_field.display_name
        )
        payload['display_name_ar'] = _pick_label(
            global_field, shop_row, 'display_name_ar', payload.get('display_name_ar') or global_field.display_name_ar
        )
        payload['display_name_ur'] = _pick_label(
            global_field, shop_row, 'display_name_ur', payload.get('display_name_ur') or global_field.display_name_ur
        )
        if shop_row.field_type:
            payload['field_type'] = shop_row.field_type
        if shop_row.min_value is not None:
            payload['min_value'] = str(shop_row.min_value)
        if shop_row.max_value is not None:
            payload['max_value'] = str(shop_row.max_value)
        payload['is_required'] = shop_row.is_required
        payload['display_order'] = shop_row.display_order
        from zthob.translations import get_language_from_request

        language = get_language_from_request(request)
        if language == 'ur' and (shop_row.help_text_ur or global_field.help_text_ur):
            payload['help_text'] = shop_row.help_text_ur or global_field.help_text_ur
        elif language == 'ar' and (shop_row.help_text_ar or global_field.help_text_ar):
            payload['help_text'] = shop_row.help_text_ar or global_field.help_text_ar
        elif shop_row.help_text_en.strip():
            payload['help_text'] = shop_row.help_text_en
        return payload

    if shop_row is not None and shop_row.is_visible:
        from zthob.translations import get_language_from_request

        language = get_language_from_request(request)
        display_en = shop_row.display_name or shop_row.name.replace('_', ' ').title()
        display = display_en
        if language == 'ur' and shop_row.display_name_ur:
            display = shop_row.display_name_ur
        elif language == 'ar' and shop_row.display_name_ar:
            display = shop_row.display_name_ar
        help_text = shop_row.help_text_en
        if language == 'ur' and shop_row.help_text_ur:
            help_text = shop_row.help_text_ur
        elif language == 'ar' and shop_row.help_text_ar:
            help_text = shop_row.help_text_ar
        return {
            'id': shop_row.id,
            'name': shop_row.name,
            'global_field_id': None,
            'is_custom': True,
            'display_name': display,
            'display_name_ar': shop_row.display_name_ar or '',
            'display_name_ur': shop_row.display_name_ur or '',
            'field_type': shop_row.field_type,
            'min_value': str(shop_row.min_value) if shop_row.min_value is not None else None,
            'max_value': str(shop_row.max_value) if shop_row.max_value is not None else None,
            'is_required': shop_row.is_required,
            'display_order': shop_row.display_order,
            'help_text': help_text or '',
        }
    return None


def resolve_measurement_template_for_shop(shop: TailorProfile | int | None, *, request=None):
    """
    Return template payload for forms. Free shops and Plus without overlay → global only.
    """
    from apps.customization.serializers import MeasurementTemplateSerializer

    base_template = get_default_measurement_template()
    if base_template is None:
        return None

    global_payload = MeasurementTemplateSerializer(base_template, context={'request': request}).data
    global_payload['source'] = 'global'
    global_payload['shop_id'] = None
    global_payload['is_editable'] = False

    if shop is None:
        return global_payload

    shop_id = shop if isinstance(shop, int) else shop.id
    global_payload['shop_id'] = shop_id

    if not is_shop_plus_active(shop_id):
        return global_payload

    schema = (
        ShopMeasurementSchema.objects.filter(shop_id=shop_id)
        .select_related('base_template')
        .prefetch_related('fields')
        .first()
    )
    if schema is None or not schema.fields.exists():
        global_payload['is_editable'] = True
        return global_payload

    base_template = schema.base_template
    global_fields = list(
        MeasurementField.objects.filter(template=base_template, is_active=True).order_by(
            'display_order', 'name'
        )
    )
    overlay_by_global = {
        row.global_field_id: row
        for row in schema.fields.all()
        if row.global_field_id
    }
    custom_rows = [
        row for row in schema.fields.all() if row.global_field_id is None and row.is_visible
    ]

    merged = []
    for global_field in global_fields:
        shop_row = overlay_by_global.get(global_field.id)
        if shop_row is not None and not shop_row.is_visible:
            continue
        field_payload = _resolved_field_dict(
            global_field=global_field,
            shop_row=shop_row,
            request=request,
        )
        if field_payload:
            merged.append(field_payload)

    for row in sorted(custom_rows, key=lambda r: (r.display_order, r.name)):
        field_payload = _resolved_field_dict(global_field=None, shop_row=row, request=request)
        if field_payload:
            merged.append(field_payload)

    merged.sort(key=lambda item: (item.get('display_order') or 0, item.get('name') or ''))

    return {
        'source': 'shop_custom',
        'shop_id': shop_id,
        'is_editable': True,
        'id': base_template.id,
        'name': base_template.name,
        'display_name': MeasurementTemplateSerializer(base_template, context={'request': request}).data[
            'display_name'
        ],
        'description': base_template.description,
        'default_unit': base_template.default_unit,
        'measurement_fields': merged,
    }


def _generate_custom_field_name(*, shop_id: int, reserved: set[str]) -> str:
    """Opaque storage key for a new shop-only field (not derived from labels)."""
    for _ in range(32):
        candidate = f'{CUSTOM_FIELD_NAME_PREFIX}{shop_id}_{secrets.token_hex(4)}'
        if len(candidate) > 50:
            candidate = candidate[:50]
        if FIELD_NAME_PATTERN.match(candidate) and candidate not in reserved:
            return candidate
    raise ValidationError({'measurement_fields': 'Could not allocate a unique field key.'})


def _field_row_attributes(*, row: dict, global_field: MeasurementField | None, index: int) -> dict:
    return {
        'is_visible': bool(row.get('is_visible', True)),
        'display_name': (row.get('display_name') or '')[:100],
        'display_name_ar': (row.get('display_name_ar') or '')[:100],
        'display_name_ur': (row.get('display_name_ur') or '')[:100],
        'field_type': row.get('field_type') or (global_field.field_type if global_field else 'decimal'),
        'min_value': row.get('min_value'),
        'max_value': row.get('max_value'),
        'is_required': bool(row.get('is_required', True)),
        'display_order': int(row.get('display_order', index)),
        'pdf_grid_row': row.get('pdf_grid_row'),
        'pdf_grid_col': row.get('pdf_grid_col'),
        'help_text_en': (row.get('help_text_en') or row.get('help_text') or '')[:200],
        'help_text_ar': (row.get('help_text_ar') or '')[:200],
        'help_text_ur': (row.get('help_text_ur') or '')[:200],
    }


@transaction.atomic
def replace_shop_measurement_schema(*, shop: TailorProfile, fields_data: list[dict]) -> ShopMeasurementSchema:
    if not is_shop_plus_active(shop):
        from apps.tailors.services.shop_plus import TailorPlusLimitError

        raise TailorPlusLimitError(
            'Tailor Plus is required to customize measurement fields for this shop.',
            entitlement='measurement_template_custom',
        )

    if len(fields_data) > MAX_SHOP_MEASUREMENT_FIELDS:
        raise ValidationError({'measurement_fields': f'Maximum {MAX_SHOP_MEASUREMENT_FIELDS} fields allowed.'})

    base_template = get_default_measurement_template()
    if base_template is None:
        raise ValidationError('Platform measurement template is not configured.')

    schema, _ = ShopMeasurementSchema.objects.get_or_create(
        shop=shop,
        defaults={'base_template': base_template},
    )
    if schema.base_template_id != base_template.id:
        schema.base_template = base_template
        schema.save(update_fields=['base_template', 'updated_at'])

    global_fields = {
        field.id: field
        for field in MeasurementField.objects.filter(template=base_template, is_active=True)
    }
    global_names = {field.name for field in global_fields.values()}

    existing_rows = list(ShopMeasurementField.objects.filter(schema=schema))
    existing_by_id = {row.id: row for row in existing_rows}
    existing_by_global = {row.global_field_id: row for row in existing_rows if row.global_field_id}
    existing_custom_by_name = {
        row.name: row for row in existing_rows if row.global_field_id is None
    }

    kept_ids: set[int] = set()
    used_names: set[str] = set()
    seen_global_ids: set[int] = set()

    for index, row in enumerate(fields_data):
        global_field_id = row.get('global_field_id')
        global_field = None
        instance = None
        name = (row.get('name') or '').strip().lower()

        if global_field_id is not None:
            global_field_id = int(global_field_id)
            if global_field_id in seen_global_ids:
                raise ValidationError(
                    {'measurement_fields': f'Duplicate global_field_id {global_field_id}.'}
                )
            seen_global_ids.add(global_field_id)
            global_field = global_fields.get(global_field_id)
            if global_field is None:
                raise ValidationError({'measurement_fields': f'Unknown global_field_id {global_field_id}'})
            name = global_field.name
            instance = existing_by_global.get(global_field_id)
        else:
            row_id = row.get('id')
            if row_id is not None:
                instance = existing_by_id.get(int(row_id))
                if instance is None or instance.schema_id != schema.id:
                    raise ValidationError({'measurement_fields': f'Unknown shop field id {row_id}.'})
                if instance.global_field_id is not None:
                    raise ValidationError(
                        {'measurement_fields': f'Field id {row_id} is a platform field; use global_field_id.'}
                    )
                name = instance.name
            elif name and FIELD_NAME_PATTERN.match(name):
                instance = existing_custom_by_name.get(name)
            else:
                name = ''

            if not name:
                name = _generate_custom_field_name(shop_id=shop.id, reserved=used_names | global_names)

        if name in used_names:
            raise ValidationError({'measurement_fields': f'Duplicate field name: {name}'})
        if not FIELD_NAME_PATTERN.match(name):
            raise ValidationError(
                {'measurement_fields': f'Invalid field name at index {index}: use lowercase a-z, 0-9, underscore.'}
            )
        used_names.add(name)

        attrs = _field_row_attributes(row=row, global_field=global_field, index=index)
        if instance is not None:
            for key, value in attrs.items():
                setattr(instance, key, value)
            instance.global_field = global_field
            instance.name = name
            instance.save()
            kept_ids.add(instance.id)
        else:
            created = ShopMeasurementField.objects.create(
                schema=schema,
                global_field=global_field,
                name=name,
                **attrs,
            )
            kept_ids.add(created.id)
            if global_field is None:
                existing_custom_by_name[name] = created

    ShopMeasurementField.objects.filter(schema=schema).exclude(id__in=kept_ids).delete()

    return schema


@transaction.atomic
def reset_shop_measurement_schema(*, shop: TailorProfile) -> None:
    if not is_shop_plus_active(shop):
        from apps.tailors.services.shop_plus import TailorPlusLimitError

        raise TailorPlusLimitError(
            'Tailor Plus is required to customize measurement fields for this shop.',
            entitlement='measurement_template_custom',
        )
    ShopMeasurementSchema.objects.filter(shop=shop).delete()


def validate_measurements_for_shop(*, shop: TailorProfile | int | None, measurements: dict) -> None:
    """Validate payload against shop schema when Plus shop has a custom overlay."""
    if not shop_has_custom_measurement_schema(shop):
        return

    shop_obj = shop
    if isinstance(shop, int):
        shop_obj = TailorProfile.objects.filter(pk=shop).first()

    resolved = resolve_measurement_template_for_shop(shop_obj)
    if not resolved or resolved.get('source') != 'shop_custom':
        return

    allowed_names = {field['name'] for field in resolved.get('measurement_fields') or []}
    values = measurement_field_values(measurements or {})
    for key in values:
        if key not in allowed_names:
            raise ValidationError(
                {'measurements': f'Field "{key}" is not allowed for this shop measurement form.'}
            )

    for field in resolved.get('measurement_fields') or []:
        if not field.get('is_required'):
            continue
        name = field.get('name')
        if name and values.get(name) in (None, ''):
            raise ValidationError({'measurements': f'Required measurement missing: {name}'})


def build_pdf_field_map_for_shop(shop_id: int | None):
    """Return PDF field map for shop custom schema, or None to use global map."""
    if shop_id is None or not shop_has_custom_measurement_schema(shop_id):
        return None

    resolved = resolve_measurement_template_for_shop(shop_id, request=None)
    if not resolved or resolved.get('source') != 'shop_custom':
        return None

    field_map = {}
    for idx, field in enumerate(resolved.get('measurement_fields') or []):
        name = field.get('name')
        if not name:
            continue
        field_map[name] = {
            'label_en': field.get('display_name') or name.replace('_', ' ').title(),
            'label_ar': field.get('display_name_ar') or field.get('display_name') or name,
            'label_ur': field.get('display_name_ur') or field.get('display_name') or name,
            'order': idx,
            'display_order': field.get('display_order') or (idx + 1),
            'pdf_grid_row': field.get('pdf_grid_row'),
            'pdf_grid_col': field.get('pdf_grid_col'),
            'unit': resolved.get('default_unit') or 'cm',
            'template': resolved.get('name'),
        }
    return field_map or None
