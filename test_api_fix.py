#!/usr/bin/env python3
"""
Test script to verify the API fix works correctly.
This script tests the endpoints that were failing due to multiple addresses.
"""

import requests
import json

# Configuration
BASE_URL = "http://69.62.126.95"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzYxMTU4OTg0LCJpYXQiOjE3NjA1NTQxODQsImp0aSI6ImZjMjA5YzIxZWIzYTQ4YjM4NDM1NjQwNTcxZGI3OWVkIiwidXNlcl9pZCI6IjIifQ.1wObhbrK_bLFd0ntVLMSXMm5gGbU60rH833FuqSvcdE"

def test_customer_profile():
    """Test the customer profile endpoint."""
    print("Testing customer profile endpoint...")
    url = f"{BASE_URL}/api/customers/customerprofile/"
    headers = {
        'accept': 'application/json',
        'Authorization': f'Bearer {TOKEN}'
    }
    
    try:
        response = requests.get(url, headers=headers)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Customer profile endpoint working correctly")
            print(f"Addresses count: {len(data.get('data', {}).get('addresses', []))}")
        else:
            print(f"❌ Customer profile endpoint failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Error testing customer profile: {e}")

def test_all_fabrics():
    """Test the all fabrics endpoint that was failing."""
    print("\nTesting all fabrics endpoint...")
    url = f"{BASE_URL}/api/customers/allfabrics/"
    headers = {
        'accept': 'application/json',
        'Authorization': f'Bearer {TOKEN}'
    }
    
    try:
        response = requests.get(url, headers=headers)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ All fabrics endpoint working correctly")
            print(f"Fabrics count: {len(data.get('data', []))}")
        else:
            print(f"❌ All fabrics endpoint failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Error testing all fabrics: {e}")

if __name__ == "__main__":
    print("Testing API endpoints after fix...")
    print("=" * 50)
    
    test_customer_profile()
    test_all_fabrics()
    
    print("\n" + "=" * 50)
    print("Test completed!")
