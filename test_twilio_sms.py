#!/usr/bin/env python3
"""
Test script for Twilio SMS OTP integration
Run this script to test if Twilio is properly configured and can send SMS
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zthob.settings')
django.setup()

from django.conf import settings
from apps.core.twilio_service import TwilioSMSService

def test_twilio_configuration():
    """Test if Twilio credentials are configured"""
    print("=" * 60)
    print("🔍 Testing Twilio Configuration")
    print("=" * 60)
    
    # Check settings
    account_sid = settings.TWILIO_ACCOUNT_SID
    auth_token = settings.TWILIO_AUTH_TOKEN
    phone_number = settings.TWILIO_PHONE_NUMBER
    
    print(f"\n📋 Configuration Status:")
    print(f"   TWILIO_ACCOUNT_SID: {'✅ SET' if account_sid else '❌ NOT SET'}")
    print(f"   TWILIO_AUTH_TOKEN: {'✅ SET' if auth_token else '❌ NOT SET'}")
    print(f"   TWILIO_PHONE_NUMBER: {phone_number if phone_number else '❌ NOT SET'}")
    
    if not all([account_sid, auth_token, phone_number]):
        print("\n❌ ERROR: Twilio credentials are not fully configured!")
        print("\n💡 Solution:")
        print("   1. Make sure your .env file has:")
        print("      TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
        print("      TWILIO_AUTH_TOKEN=your_auth_token_here")
        print("      TWILIO_PHONE_NUMBER=+17252553868")
        print("\n   2. Export environment variables:")
        print("      export TWILIO_ACCOUNT_SID='AC...'")
        print("      export TWILIO_AUTH_TOKEN='...'")
        print("      export TWILIO_PHONE_NUMBER='+17252553868'")
        print("\n   3. Or load .env file before running Django:")
        print("      pip install python-dotenv")
        print("      Then add to settings.py:")
        print("      from dotenv import load_dotenv")
        print("      load_dotenv()")
        return False
    
    print("\n✅ All Twilio credentials are configured!")
    return True

def test_phone_formatting():
    """Test phone number formatting"""
    print("\n" + "=" * 60)
    print("📱 Testing Phone Number Formatting")
    print("=" * 60)
    
    test_cases = [
        ("0501234567", "+966501234567"),
        ("501234567", "+966501234567"),
        ("966501234567", "+966501234567"),
        ("+966501234567", "+966501234567"),
    ]
    
    print("\n📋 Test Cases:")
    for input_phone, expected in test_cases:
        formatted = TwilioSMSService.format_phone_number(input_phone)
        status = "✅" if formatted == expected else "❌"
        print(f"   {status} {input_phone:15} → {formatted:15} (expected: {expected})")
    
    return True

def test_send_sms(phone_number: str):
    """Test sending SMS"""
    print("\n" + "=" * 60)
    print("📤 Testing SMS Sending")
    print("=" * 60)
    
    if not phone_number:
        print("❌ ERROR: Phone number is required!")
        print("   Usage: python test_twilio_sms.py <phone_number>")
        print("   Example: python test_twilio_sms.py 0501234567")
        return False
    
    # Generate test OTP
    import random
    test_otp = str(random.randint(100000, 999999))
    
    print(f"\n📋 Test Details:")
    print(f"   Phone Number: {phone_number}")
    print(f"   Test OTP Code: {test_otp}")
    print(f"   Formatted Phone: {TwilioSMSService.format_phone_number(phone_number)}")
    
    print("\n⏳ Sending SMS...")
    
    success, message = TwilioSMSService.send_otp_sms(
        phone_number=phone_number,
        otp_code=test_otp
    )
    
    if success:
        print(f"\n✅ SUCCESS: {message}")
        print(f"\n📱 Check your phone! You should receive:")
        print(f"   'Your Mgask verification code is: {test_otp}. Valid for 5 minutes.'")
        print(f"\n💡 Note: If using Twilio trial account, make sure the phone number")
        print(f"   is verified in Twilio Console → Phone Numbers → Verified Caller IDs")
    else:
        print(f"\n❌ FAILED: {message}")
        print(f"\n💡 Troubleshooting:")
        print(f"   1. Check Twilio credentials in .env file")
        print(f"   2. Verify phone number is correct")
        print(f"   3. If using trial account, verify the number in Twilio Console")
        print(f"   4. Check Twilio Console → Monitor → Logs → Messaging")
    
    return success

def main():
    """Main test function"""
    print("\n" + "🚀" * 30)
    print("Twilio SMS OTP Integration Test")
    print("🚀" * 30)
    
    # Test 1: Configuration
    if not test_twilio_configuration():
        sys.exit(1)
    
    # Test 2: Phone formatting
    test_phone_formatting()
    
    # Test 3: Send SMS (if phone number provided)
    if len(sys.argv) > 1:
        phone_number = sys.argv[1]
        test_send_sms(phone_number)
    else:
        print("\n" + "=" * 60)
        print("💡 To test SMS sending, provide a phone number:")
        print("   python test_twilio_sms.py <phone_number>")
        print("   Example: python test_twilio_sms.py 0501234567")
        print("=" * 60)
    
    print("\n" + "=" * 60)
    print("✅ Testing Complete!")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()



