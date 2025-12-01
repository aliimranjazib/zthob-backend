#!/bin/bash
# Complete Workload Identity Federation Setup Script
# Run this script to set up OIDC Workload Identity Federation for Firebase

set -e

PROJECT_ID="mgask-2025"
PROJECT_NUMBER="1031684980612"
POOL_NAME="firebase-pool"
PROVIDER_NAME="firebase-provider"
SERVICE_ACCOUNT="firebase-workload-identity@mgask-2025.iam.gserviceaccount.com"

echo "=========================================="
echo "Setting up Workload Identity Federation"
echo "=========================================="
echo ""

# Step 1: Enable APIs
echo "Step 1: Enabling required APIs..."
gcloud services enable iamcredentials.googleapis.com --project=$PROJECT_ID
gcloud services enable firebase.googleapis.com --project=$PROJECT_ID
gcloud services enable fcm.googleapis.com --project=$PROJECT_ID
echo "✅ APIs enabled"
echo ""

# Step 2: Create Workload Identity Pool (if not exists)
echo "Step 2: Creating Workload Identity Pool..."
if ! gcloud iam workload-identity-pools describe "$POOL_NAME" --project=$PROJECT_ID --location=global &>/dev/null; then
    gcloud iam workload-identity-pools create "$POOL_NAME" \
        --project=$PROJECT_ID \
        --location="global" \
        --display-name="Firebase Authentication Pool"
    echo "✅ Pool created"
else
    echo "✅ Pool already exists"
fi
echo ""

# Step 3: Create OIDC Provider (if not exists)
echo "Step 3: Creating OIDC Provider..."
if ! gcloud iam workload-identity-pools providers describe "$PROVIDER_NAME" \
    --project=$PROJECT_ID \
    --location=global \
    --workload-identity-pool="$POOL_NAME" &>/dev/null; then
    
    gcloud iam workload-identity-pools providers create-oidc "$PROVIDER_NAME" \
        --project=$PROJECT_ID \
        --location="global" \
        --workload-identity-pool="$POOL_NAME" \
        --display-name="Firebase OIDC Provider" \
        --attribute-mapping="google.subject=assertion.sub" \
        --issuer-uri="https://accounts.google.com"
    echo "✅ Provider created"
else
    echo "✅ Provider already exists"
fi
echo ""

# Step 4: Create Service Account (if not exists)
echo "Step 4: Creating Service Account..."
if ! gcloud iam service-accounts describe "$SERVICE_ACCOUNT" --project=$PROJECT_ID &>/dev/null; then
    gcloud iam service-accounts create firebase-workload-identity \
        --project=$PROJECT_ID \
        --display-name="Firebase Workload Identity SA"
    echo "✅ Service account created"
else
    echo "✅ Service account already exists"
fi
echo ""

# Step 5: Grant Firebase Admin role
echo "Step 5: Granting Firebase Admin role..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/firebase.admin" \
    --condition=None 2>/dev/null || echo "✅ Role already granted"
echo ""

# Step 6: Get provider resource name
echo "Step 6: Getting provider resource name..."
PROVIDER_RESOURCE=$(gcloud iam workload-identity-pools providers describe "$PROVIDER_NAME" \
    --project=$PROJECT_ID \
    --location=global \
    --workload-identity-pool="$POOL_NAME" \
    --format="value(name)")

echo "Provider Resource: $PROVIDER_RESOURCE"
echo ""

# Step 7: Create token generation script
echo "Step 7: Creating token generation script..."
cat > generate_oidc_token.sh << EOF
#!/bin/bash
# Generate OIDC token for Workload Identity Federation

AUDIENCE="https://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_NAME}/providers/${PROVIDER_NAME}"

if command -v gcloud &> /dev/null; then
    TOKEN=\$(gcloud auth print-identity-token --audience="\$AUDIENCE" 2>/dev/null)
    if [ -n "\$TOKEN" ]; then
        EXPIRY=\$((\$(date +%s) + 3600))
        echo "{\"version\":1,\"success\":true,\"token_type\":\"urn:ietf:params:oauth:token-type:jwt\",\"expiration_time\":\${EXPIRY},\"id_token\":\"\${TOKEN}\"}"
        exit 0
    fi
fi

echo "{\"version\":1,\"success\":false,\"code\":\"COMMAND_NOT_FOUND\",\"message\":\"gcloud CLI not found or not authenticated\"}" >&2
exit 1
EOF

chmod +x generate_oidc_token.sh
echo "✅ Token generation script created"
echo ""

# Step 8: Generate credentials configuration
echo "Step 8: Generating credentials configuration..."
echo "Note: This requires the executable command path. Using relative path..."
echo ""

# Get absolute path to script
SCRIPT_PATH=$(pwd)/generate_oidc_token.sh

gcloud iam workload-identity-pools create-cred-config \
    "$PROVIDER_RESOURCE" \
    --service-account="$SERVICE_ACCOUNT" \
    --executable-command="$SCRIPT_PATH" \
    --executable-timeout-millis=5000 \
    --output-file=workload-identity-credentials.json

echo "✅ Credentials file generated: workload-identity-credentials.json"
echo ""

echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Upload generate_oidc_token.sh to your server:"
echo "   scp generate_oidc_token.sh root@69.62.126.95:/home/zthob-backend/"
echo ""
echo "2. Upload workload-identity-credentials.json to your server:"
echo "   scp workload-identity-credentials.json root@69.62.126.95:/home/zthob-backend/.secrets/"
echo ""
echo "3. On server, set permissions:"
echo "   chmod 600 /home/zthob-backend/.secrets/workload-identity-credentials.json"
echo "   chmod +x /home/zthob-backend/generate_oidc_token.sh"
echo ""
echo "4. Add to .env on server:"
echo "   FIREBASE_CREDENTIALS_PATH=/home/zthob-backend/.secrets/workload-identity-credentials.json"
echo ""
echo "5. Install gcloud CLI on server (if not already installed)"
echo "6. Authenticate gcloud on server: gcloud auth application-default login"
echo "7. Restart service: sudo systemctl restart gunicorn"
echo ""

