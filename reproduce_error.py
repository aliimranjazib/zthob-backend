import os
import django
import json
from decimal import Decimal

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zthob.settings')
django.setup()

from apps.orders.serializers import OrderCreateSerializer
from django.contrib.auth import get_user_model
from apps.tailors.models import TailorProfile, Fabric, FabricCategory
from apps.customers.models import Address

User = get_user_model()

def reproduce():
    # Get or create test data
    customer = User.objects.filter(role='USER').first()
    if not customer:
        customer = User.objects.create_user(username='test_customer', email='c@e.com', password='p', role='USER')
    
    tailor = User.objects.filter(role='TAILOR').first()
    if not tailor:
        tailor = User.objects.create_user(username='test_tailor', email='t@e.com', password='p', role='TAILOR')
        TailorProfile.objects.get_or_create(user=tailor, shop_name='Test Shop', shop_status=True)

    # Ensure we use a fabric that belongs to THIS tailor
    fabric = Fabric.objects.filter(tailor=tailor.tailor_profile).first()
    if not fabric:
        cat = FabricCategory.objects.first() or FabricCategory.objects.create(name='Cat', slug='cat')
        fabric = Fabric.objects.create(tailor=tailor.tailor_profile, name='Fabric', price=Decimal('100.0'), stock=10, is_active=True, category=cat)

    # Create dummy CustomStyle
    from apps.customization.models import CustomStyle, CustomStyleCategory
    style_cat, _ = CustomStyleCategory.objects.get_or_create(name='collar', defaults={'display_name': 'Collar'})
    style_obj, _ = CustomStyle.objects.get_or_create(
        category=style_cat, 
        name='Mandarin', 
        code='collar_mandarin',
        defaults={'display_order': 1, 'is_active': True}
    )

    payload = {
      "order_type": "fabric_with_stitching", 
      "tailor": tailor.id,
      "payment_method": "credit_card",
      "appointment_date": "2024-12-20",
      "appointment_time": "14:30:00",
      "delivery_address": {
        "latitude": 24.7136,
        "longitude": 46.6753,
        "formatted_address": "King Fahd Rd, Riyadh",
        "street": "King Fahd Rd",
        "city": "Riyadh"
      },
      "special_instructions": "Family order for upcoming event",
      "custom_styles": [
        {
          "category": "collar",
          "style_id": style_obj.id
        }
      ],
      "items": [
        {
          "fabric": fabric.id,
          "quantity": 1,
          "family_member": None, 
          "custom_instructions": "My thob - make sleeves longer"
        }
      ]
    }

    print("Payload to validate:")
    print(json.dumps(payload, indent=2))
    
    # Simulate the view logic
    data = payload.copy()
    data['customer'] = customer.id
    
    mock_request = type('obj', (object,), {'user': customer})()
    serializer = OrderCreateSerializer(data=data, context={'request': mock_request})
    
    if serializer.is_valid():
        print("Success: Serializer is valid")
        print("Enriched custom_styles:")
        print(json.dumps(serializer.validated_data['custom_styles'], indent=2))
    else:
        print("Error: Serializer is invalid")
        print(json.dumps(serializer.errors, indent=2))

if __name__ == "__main__":
    reproduce()
