"""
Django management command to migrate existing hardcoded measurements to the database

This creates a default measurement template and migrates existing order measurements
to use the new template system.

Usage: python manage.py migrate_measurements
"""
from django.core.management.base import BaseCommand
from apps.measurements.models import MeasurementTemplate, MeasurementField
from apps.orders.models import Order, OrderItem


class Command(BaseCommand):
    help = 'Migrate existing hardcoded measurements to measurement template system'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run migration without making changes to database'
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        # Check if default template already exists
        existing_template = MeasurementTemplate.objects.filter(
            name_en='Standard Thobe',
            is_default=True
        ).first()
        
        if existing_template:
            self.stdout.write(self.style.WARNING(
                f'Default template already exists: {existing_template.name_en}'
            ))
            template = existing_template
        else:
            if dry_run:
                self.stdout.write(self.style.SUCCESS(
                    'Would create: Standard Thobe measurement template'
                ))
                return
            
            # Create default measurement template
            template = MeasurementTemplate.objects.create(
                name_en='Standard Thobe',
                name_ar='ثوب قياسي',
                description_en='Standard measurement template for traditional Saudi thobe',
                description_ar='قالب قياس قياسي للثوب السعودي التقليدي',
                garment_type='thobe',
                is_default=True,
                is_active=True
            )
            
            self.stdout.write(self.style.SUCCESS(
                f'Created default template: {template.name_en}'
            ))
        
        # Define standard measurement fields based on existing hardcoded values
        standard_fields = [
            {
                'field_key': 'neck',
                'display_name_en': 'Neck',
                'display_name_ar': 'الرقبة',
                'unit': 'cm',
                'min_value': 30,
                'max_value': 50,
                'is_required': True,
                'order': 10,
                'category': 'upper_body',
            },
            {
                'field_key': 'shoulder',
                'display_name_en': 'Shoulder',
                'display_name_ar': 'الكتف',
                'unit': 'cm',
                'min_value': 40,
                'max_value': 60,
                'is_required': True,
                'order': 20,
                'category': 'upper_body',
            },
            {
                'field_key': 'chest',
                'display_name_en': 'Chest',
                'display_name_ar': 'الصدر',
                'unit': 'cm',
                'min_value': 80,
                'max_value': 150,
                'is_required': True,
                'order': 30,
                'category': 'upper_body',
            },
            {
                'field_key': 'waist',
                'display_name_en': 'Waist',
                'display_name_ar': 'الخصر',
                'unit': 'cm',
                'min_value': 70,
                'max_value': 140,
                'is_required': False,
                'order': 40,
                'category': 'upper_body',
            },
            {
                'field_key': 'hip',
                'display_name_en': 'Hip',
                'display_name_ar': 'الورك',
                'unit': 'cm',
                'min_value': 80,
                'max_value': 150,
                'is_required': False,
                'order': 50,
                'category': 'lower_body',
            },
            {
                'field_key': 'sleeve_length',
                'display_name_en': 'Sleeve Length',
                'display_name_ar': 'طول الكم',
                'unit': 'cm',
                'min_value': 55,
                'max_value': 75,
                'is_required': True,
                'order': 60,
                'category': 'length',
            },
            {
                'field_key': 'arm_hole',
                'display_name_en': 'Arm Hole',
                'display_name_ar': 'فتحة الذراع',
                'unit': 'cm',
                'min_value': 40,
                'max_value': 60,
                'is_required': False,
                'order': 70,
                'category': 'width',
            },
            {
                'field_key': 'body_length',
                'display_name_en': 'Body Length',
                'display_name_ar': 'طول الجسم',
                'unit': 'cm',
                'min_value': 70,
                'max_value': 100,
                'is_required': False,
                'order': 80,
                'category': 'length',
            },
            {
                'field_key': 'thobe_length',
                'display_name_en': 'Thobe Length',
                'display_name_ar': 'طول الثوب',
                'unit': 'cm',
                'min_value': 140,
                'max_value': 180,
                'is_required': True,
                'order': 90,
                'category': 'length',
            },
        ]
        
        # Create measurement fields
        fields_created = 0
        for field_data in standard_fields:
            existing_field = MeasurementField.objects.filter(
                template=template,
                field_key=field_data['field_key']
            ).first()
            
            if existing_field:
                self.stdout.write(
                    f'  Field already exists: {field_data["display_name_en"]}'
                )
                continue
            
            if dry_run:
                self.stdout.write(self.style.SUCCESS(
                    f'  Would create field: {field_data["display_name_en"]}'
                ))
                continue
            
            MeasurementField.objects.create(
                template=template,
                **field_data
            )
            fields_created += 1
            self.stdout.write(self.style.SUCCESS(
                f'  Created field: {field_data["display_name_en"]}'
            ))
        
        if not dry_run:
            self.stdout.write(self.style.SUCCESS(
                f'\nSuccessfully created {fields_created} measurement fields'
            ))
        
        # Count orders that need migration
        # Note: This assumes you'll add measurement_template field to OrderItem model
        self.stdout.write(self.style.WARNING(
            '\nNote: To complete migration, add "measurement_template" ForeignKey field '
            'to OrderItem model and update existing OrderItems to reference the default template.'
        ))
        
        self.stdout.write(self.style.SUCCESS('\nMigration script completed successfully!'))
