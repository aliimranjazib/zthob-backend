"""Serializers for Tailor Plus shop measurement template overlay."""

from rest_framework import serializers


class ShopMeasurementFieldWriteSerializer(serializers.Serializer):
    """Write shape: globals by ``global_field_id``; custom fields by ``id`` + ``display_name``."""

    id = serializers.IntegerField(required=False, allow_null=True)
    name = serializers.CharField(max_length=50, required=False, allow_blank=True)
    global_field_id = serializers.IntegerField(required=False, allow_null=True)
    is_visible = serializers.BooleanField(default=True)
    display_name = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    field_type = serializers.ChoiceField(
        choices=['decimal', 'integer', 'text'],
        required=False,
    )
    min_value = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    max_value = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    is_required = serializers.BooleanField(required=False, default=True)
    display_order = serializers.IntegerField(required=False, default=0)
    pdf_grid_row = serializers.IntegerField(required=False, allow_null=True)
    pdf_grid_col = serializers.IntegerField(required=False, allow_null=True)
    help_text = serializers.CharField(max_length=200, required=False, allow_blank=True, default='')
    help_text_en = serializers.CharField(max_length=200, required=False, allow_blank=True, default='')
    help_text_ar = serializers.CharField(max_length=200, required=False, allow_blank=True, default='')
    help_text_ur = serializers.CharField(max_length=200, required=False, allow_blank=True, default='')

    def validate(self, attrs):
        global_field_id = attrs.get('global_field_id')
        if global_field_id is not None:
            return attrs
        row_id = attrs.get('id')
        if row_id is None and not (attrs.get('display_name') or '').strip():
            raise serializers.ValidationError('Custom fields require display_name.')
        return attrs


class ShopMeasurementTemplateWriteSerializer(serializers.Serializer):
    measurement_fields = ShopMeasurementFieldWriteSerializer(many=True)
