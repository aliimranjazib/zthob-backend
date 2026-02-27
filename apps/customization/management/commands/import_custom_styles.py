from django.core.management.base import BaseCommand
from django.core.files import File
from apps.customization.models import CustomStyleCategory, CustomStyle
import os


class Command(BaseCommand):
    help = 'Import custom style images from Flutter assets directory'

    def handle(self, *args, **options):
        # Base path to Flutter assets
        base_path = '/Users/jazib/Documents/GitHub/Mgask/assets/thobs'
        
        if not os.path.exists(base_path):
            self.stdout.write(self.style.ERROR(f'Flutter assets directory not found: {base_path}'))
            return
        
        # Define categories with their folder paths
        categories_data = [
            {'name': 'collar', 'display_name': 'Collar Styles', 'folder': 'collar', 'order': 1},
            {'name': 'cuff', 'display_name': 'Cuff Styles', 'folder': 'cuff', 'order': 2},
            {'name': 'placket', 'display_name': 'Placket Styles', 'folder': 'placket', 'order': 3},
            {'name': 'front_single_pocket', 'display_name': 'Front Single Pocket', 'folder': 'pockets/front_single_pocket', 'order': 4},
            {'name': 'front_double_pocket', 'display_name': 'Front Double Pocket', 'folder': 'pockets/front_double_pocket', 'order': 5},
            {'name': 'side_pocket', 'display_name': 'Side Pocket', 'folder': 'pockets/side_pocket', 'order': 6},
            {'name': 'buttons', 'display_name': 'Button Colors', 'folder': 'buttons', 'order': 7},
            {'name': 'yoke', 'display_name': 'Yoke Styles', 'folder': 'yoke', 'order': 8},
        ]
        
        total_imported = 0
        total_skipped = 0
        
        for cat_data in categories_data:
            self.stdout.write(f"\n{'='*60}")
            self.stdout.write(self.style.WARNING(f"Processing category: {cat_data['display_name']}"))
            self.stdout.write(f"{'='*60}")
            
            # Create or get category
            category, created = CustomStyleCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults={
                    'display_name': cat_data['display_name'],
                    'display_order': cat_data['order']
                }
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f"✓ Created category: {category.display_name}"))
            else:
                self.stdout.write(f"  Found existing category: {category.display_name}")
            
            # Import images for this category
            imported, skipped = self.import_category_images(category, base_path, cat_data['folder'])
            total_imported += imported
            total_skipped += skipped
        
        # Final summary
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(self.style.SUCCESS(f"IMPORT COMPLETE!"))
        self.stdout.write(f"{'='*60}")
        self.stdout.write(self.style.SUCCESS(f"✓ Total images imported: {total_imported}"))
        self.stdout.write(f"  Total images skipped: {total_skipped}")
        self.stdout.write(f"{'='*60}\n")
    
    def import_category_images(self, category, base_path, folder):
        """Import all images for a specific category"""
        folder_path = os.path.join(base_path, folder)
        
        if not os.path.exists(folder_path):
            self.stdout.write(self.style.WARNING(f"  ⚠ Folder not found: {folder_path}"))
            return 0, 0
        
        # Get all image files
        image_files = sorted([
            f for f in os.listdir(folder_path) 
            if f.lower().endswith(('.png', '.jpg', '.jpeg'))
        ])
        
        if not image_files:
            self.stdout.write(self.style.WARNING(f"  ⚠ No images found in: {folder_path}"))
            return 0, 0
        
        imported = 0
        skipped = 0
        
        for idx, filename in enumerate(image_files):
            # Extract style name from filename
            # e.g., "collar_1_Standard.png" -> "Standard"
            name_parts = filename.replace('.png', '').replace('.jpg', '').replace('.jpeg', '').split('_')
            
            if len(name_parts) >= 3:
                # Format: prefix_number_Name
                style_name = '_'.join(name_parts[2:])
            elif len(name_parts) == 2:
                # Format: prefix_Name
                style_name = name_parts[1]
            else:
                # Just use filename without extension
                style_name = filename.rsplit('.', 1)[0]
            
            # Clean up style name
            style_name = style_name.replace('_', ' ').title()
            
            # Generate code
            code = filename.rsplit('.', 1)[0]  # Remove extension
            
            # Check if already exists
            if CustomStyle.objects.filter(category=category, code=code).exists():
                self.stdout.write(f"  - Skipping (exists): {style_name}")
                skipped += 1
                continue
            
            # Create style entry
            file_path = os.path.join(folder_path, filename)
            
            try:
                with open(file_path, 'rb') as f:
                    style = CustomStyle.objects.create(
                        category=category,
                        name=style_name,
                        code=code,
                        display_order=idx,
                    )
                    style.image.save(filename, File(f), save=True)
                    self.stdout.write(self.style.SUCCESS(f"  ✓ Imported: {style_name} ({filename})"))
                    imported += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ Error importing {filename}: {str(e)}"))
        
        return imported, skipped
