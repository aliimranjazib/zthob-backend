#!/usr/bin/env python3
"""
Script to clean up duplicate addresses for a specific user.
This script will keep only the default address and remove all others.
"""

import os
import sys
import django

# Add the project directory to Python path
sys.path.append('/Users/jazib/Documents/GitHub/zthob-backend')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zthob.settings')
django.setup()

from apps.customers.models import Address
from apps.accounts.models import CustomUser

def cleanup_user_addresses(user_id):
    """Clean up addresses for a specific user, keeping only the default one."""
    try:
        user = CustomUser.objects.get(id=user_id)
        addresses = Address.objects.filter(user=user)
        
        print(f"Found {addresses.count()} addresses for user {user.username} (ID: {user_id})")
        
        if addresses.count() <= 1:
            print("User has 1 or fewer addresses, no cleanup needed.")
            return
        
        # Find the default address
        default_address = addresses.filter(is_default=True).first()
        
        if default_address:
            print(f"Keeping default address: ID {default_address.id} - {default_address.street}, {default_address.city}")
            # Delete all other addresses
            other_addresses = addresses.exclude(id=default_address.id)
            deleted_count = other_addresses.count()
            other_addresses.delete()
            print(f"Deleted {deleted_count} non-default addresses")
        else:
            # If no default address, keep the first one and make it default
            first_address = addresses.first()
            first_address.is_default = True
            first_address.save()
            print(f"No default address found. Made first address default: ID {first_address.id} - {first_address.street}, {first_address.city}")
            
            # Delete all other addresses
            other_addresses = addresses.exclude(id=first_address.id)
            deleted_count = other_addresses.count()
            other_addresses.delete()
            print(f"Deleted {deleted_count} other addresses")
        
        # Verify the cleanup
        remaining_addresses = Address.objects.filter(user=user)
        print(f"After cleanup: {remaining_addresses.count()} address(es) remaining")
        for addr in remaining_addresses:
            print(f"  - ID: {addr.id}, Street: {addr.street}, City: {addr.city}, is_default: {addr.is_default}")
            
    except CustomUser.DoesNotExist:
        print(f"User with ID {user_id} not found")
    except Exception as e:
        print(f"Error during cleanup: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python cleanup_addresses.py <user_id>")
        sys.exit(1)
    
    user_id = int(sys.argv[1])
    cleanup_user_addresses(user_id)
