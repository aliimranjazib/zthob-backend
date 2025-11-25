#!/bin/bash
# Debug script to check Twilio configuration on production server
# Run this on the production server: bash DEBUG_TWILIO_SERVER.sh

echo "=========================================="
echo "🔍 Twilio Configuration Debug Script"
echo "=========================================="
echo ""

# Check 1: .env file exists and has Twilio credentials
echo "1️⃣ Checking .env file..."
if [ -f "/home/zthob-backend/.env" ]; then
    echo "   ✅ .env file exists"
    echo ""
    echo "   Twilio variables in .env:"
    grep -i "TWILIO" /home/zthob-backend/.env || echo "   ❌ No TWILIO variables found in .env"
else
    echo "   ❌ .env file NOT found at /home/zthob-backend/.env"
fi
echo ""

# Check 2: Environment variables are set
echo "2️⃣ Checking environment variables..."
if [ -n "$TWILIO_ACCOUNT_SID" ]; then
    echo "   ✅ TWILIO_ACCOUNT_SID is set"
else
    echo "   ❌ TWILIO_ACCOUNT_SID is NOT set"
fi

if [ -n "$TWILIO_AUTH_TOKEN" ]; then
    echo "   ✅ TWILIO_AUTH_TOKEN is set"
else
    echo "   ❌ TWILIO_AUTH_TOKEN is NOT set"
fi

if [ -n "$TWILIO_PHONE_NUMBER" ]; then
    echo "   ✅ TWILIO_PHONE_NUMBER is set: $TWILIO_PHONE_NUMBER"
else
    echo "   ❌ TWILIO_PHONE_NUMBER is NOT set"
fi
echo ""

# Check 3: python-dotenv is installed
echo "3️⃣ Checking python-dotenv installation..."
cd /home/zthob-backend
source magsk_venv/bin/activate
if pip3 list | grep -q "python-dotenv"; then
    echo "   ✅ python-dotenv is installed"
else
    echo "   ❌ python-dotenv is NOT installed"
    echo "   💡 Run: pip3 install python-dotenv"
fi
echo ""

# Check 4: Django can read the settings
echo "4️⃣ Testing Django settings..."
python3 << EOF
import os
import sys
import django

sys.path.insert(0, '/home/zthob-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zthob.settings')

try:
    django.setup()
    from django.conf import settings
    
    print("   Django settings loaded:")
    print(f"   TWILIO_ACCOUNT_SID: {'✅ SET' if settings.TWILIO_ACCOUNT_SID else '❌ NOT SET'}")
    print(f"   TWILIO_AUTH_TOKEN: {'✅ SET' if settings.TWILIO_AUTH_TOKEN else '❌ NOT SET'}")
    print(f"   TWILIO_PHONE_NUMBER: {settings.TWILIO_PHONE_NUMBER if settings.TWILIO_PHONE_NUMBER else '❌ NOT SET'}")
except Exception as e:
    print(f"   ❌ Error loading Django settings: {e}")
EOF

echo ""
echo "=========================================="
echo "✅ Debug complete!"
echo "=========================================="

