# Workload Identity Federation Setup Guide for Firebase

This guide shows how to set up Workload Identity Federation to authenticate Firebase without service account keys.

## Overview

Workload Identity Federation allows external workloads (like your server) to authenticate to GCP services using OIDC tokens instead of service account keys.

## Prerequisites

- GCP Project: `mgask-2025`
- Firebase Project: `mgask-2025`
- gcloud CLI installed and authenticated

## Step 1: Enable Required APIs

```bash
# Enable IAM API
gcloud services enable iamcredentials.googleapis.com --project=mgask-2025

# Enable Firebase APIs
gcloud services enable firebase.googleapis.com --project=mgask-2025
gcloud services enable fcm.googleapis.com --project=mgask-2025
```

## Step 2: Create Workload Identity Pool

```bash
# Create workload identity pool
gcloud iam workload-identity-pools create "firebase-pool" \
    --project="mgask-2025" \
    --location="global" \
    --display-name="Firebase Authentication Pool"
```

## Step 3: Create Workload Identity Provider

### Option A: OIDC Provider (for external servers)

```bash
# Create OIDC provider
gcloud iam workload-identity-pools providers create-oidc "firebase-provider" \
    --project="mgask-2025" \
    --location="global" \
    --workload-identity-pool="firebase-pool" \
    --display-name="Firebase OIDC Provider" \
    --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.contained_in=assertion.contained_in" \
    --issuer-uri="https://accounts.google.com"
```

### Option B: AWS Provider (if server is on AWS)

```bash
gcloud iam workload-identity-pools providers create-aws "firebase-aws-provider" \
    --project="mgask-2025" \
    --location="global" \
    --workload-identity-pool="firebase-pool" \
    --account-id="YOUR_AWS_ACCOUNT_ID"
```

## Step 4: Create Service Account for Firebase

```bash
# Create service account
gcloud iam service-accounts create firebase-workload-identity \
    --project="mgask-2025" \
    --display-name="Firebase Workload Identity Service Account"

# Grant Firebase permissions
gcloud projects add-iam-policy-binding mgask-2025 \
    --member="serviceAccount:firebase-workload-identity@mgask-2025.iam.gserviceaccount.com" \
    --role="roles/firebase.admin"
```

## Step 5: Bind Workload Identity to Service Account

```bash
# Get the workload identity pool resource name
POOL_ID=$(gcloud iam workload-identity-pools describe "firebase-pool" \
    --project="mgask-2025" \
    --location="global" \
    --format="value(name)")

# Allow workload identity pool to impersonate service account
gcloud iam service-accounts add-iam-policy-binding \
    firebase-workload-identity@mgask-2025.iam.gserviceaccount.com \
    --project="mgask-2025" \
    --role="roles/iam.workloadIdentityUser" \
    --member="principalSet://iam.googleapis.com/${POOL_ID}/attribute.actor=YOUR_IDENTITY"
```

## Step 6: Generate Credentials Configuration File

For OIDC providers, you need to specify a credential source. Choose one:

### Option A: File-based credential source (if you have OIDC tokens in a file)

```bash
# Generate credentials configuration with file-based credential source
gcloud iam workload-identity-pools create-cred-config \
    projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/firebase-pool/providers/firebase-provider \
    --service-account=firebase-workload-identity@mgask-2025.iam.gserviceaccount.com \
    --credential-source-file=/path/to/oidc-token-file \
    --output-file=workload-identity-credentials.json
```

### Option B: Executable command (Recommended for external servers)

**Step 1:** Get the provider's audience/resource name:

```bash
PROJECT_NUMBER=1031684980612

# Get the full provider resource name (this is the audience)
PROVIDER_NAME=$(gcloud iam workload-identity-pools providers describe "firebase-provider" \
    --project="mgask-2025" \
    --location="global" \
    --workload-identity-pool="firebase-pool" \
    --format="value(name)")

echo "Provider Name: $PROVIDER_NAME"
```

**Step 2:** Create token generation script on your server:

```bash
# On your server, create the script
cat > /home/zthob-backend/generate_oidc_token.sh << 'EOF'
#!/bin/bash
# Generate OIDC token for Workload Identity Federation
# Output format: JSON with version, success, token_type, expiration_time, and id_token

PROJECT_NUMBER=1031684980612
AUDIENCE="https://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/firebase-pool/providers/firebase-provider"

# Use gcloud to get OIDC token
if command -v gcloud &> /dev/null; then
    TOKEN=$(gcloud auth print-identity-token --audience="$AUDIENCE" 2>/dev/null)
    if [ -n "$TOKEN" ]; then
        # Output in the format expected by Workload Identity Federation executable command
        EXPIRY=$(($(date +%s) + 3600))
        echo "{\"version\":1,\"success\":true,\"token_type\":\"urn:ietf:params:oauth:token-type:jwt\",\"expiration_time\":${EXPIRY},\"id_token\":\"${TOKEN}\"}"
        exit 0
    fi
fi

# Error output
echo "{\"version\":1,\"success\":false,\"code\":\"COMMAND_NOT_FOUND\",\"message\":\"gcloud CLI not found or not authenticated\"}" >&2
exit 1
EOF

chmod +x /home/zthob-backend/generate_oidc_token.sh
```

**Step 3:** Generate credentials configuration:

```bash
# On your local machine (with gcloud CLI)
PROJECT_NUMBER=1031684980612

gcloud iam workload-identity-pools create-cred-config \
    projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/firebase-pool/providers/firebase-provider \
    --service-account=firebase-workload-identity@mgask-2025.iam.gserviceaccount.com \
    --executable-command="/home/zthob-backend/generate_oidc_token.sh" \
    --executable-timeout-millis=5000 \
    --output-file=workload-identity-credentials.json
```

**Important Notes:**
- The executable script must output JSON in the exact format shown above
- The script must be executable and accessible on your server
- gcloud CLI must be installed and authenticated on your server
- The script will be called by the Google Auth library to get fresh tokens

### Option C: URL-based credential source (if tokens come from a URL)

```bash
# Generate credentials configuration with URL-based credential source
gcloud iam workload-identity-pools create-cred-config \
    projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/firebase-pool/providers/firebase-provider \
    --service-account=firebase-workload-identity@mgask-2025.iam.gserviceaccount.com \
    --credential-source-url="https://your-token-endpoint.com/token" \
    --output-file=workload-identity-credentials.json
```

**Note:** For external servers, Workload Identity Federation requires setting up OIDC token generation, which can be complex. Consider using REST API with Server Key instead (simpler and works immediately).

## Step 7: Configure Application to Use Workload Identity

Set environment variable:
```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/workload-identity-credentials.json
```

Or use in code:
```python
from google.auth import load_credentials_from_file

credentials, project = load_credentials_from_file(
    'workload-identity-credentials.json',
    scopes=['https://www.googleapis.com/auth/firebase.messaging']
)
```

## Alternative: Use gcloud CLI to Generate Tokens

If you have gcloud CLI on your server:

```bash
# Generate access token using workload identity
gcloud auth print-access-token \
    --impersonate-service-account=firebase-workload-identity@mgask-2025.iam.gserviceaccount.com
```

## For GitHub Actions (Already in your workflow)

Your GitHub Actions workflow already has the setup commented out. To enable:

1. Get Workload Identity Provider:
```bash
gcloud iam workload-identity-pools providers describe "firebase-provider" \
    --project="mgask-2025" \
    --location="global" \
    --workload-identity-pool="firebase-pool" \
    --format="value(name)"
```

2. Add to GitHub Secrets:
   - `WORKLOAD_IDENTITY_PROVIDER`: The provider name from above
   - `SERVICE_ACCOUNT`: `firebase-workload-identity@mgask-2025.iam.gserviceaccount.com`

3. Uncomment the authentication steps in `.github/workflows/deploy.yml`

## Troubleshooting

### Check Workload Identity Pool
```bash
gcloud iam workload-identity-pools list --project=mgask-2025 --location=global
```

### Check Providers
```bash
gcloud iam workload-identity-pools providers list \
    --project="mgask-2025" \
    --location="global" \
    --workload-identity-pool="firebase-pool"
```

### Verify Service Account Binding
```bash
gcloud iam service-accounts get-iam-policy \
    firebase-workload-identity@mgask-2025.iam.gserviceaccount.com \
    --project="mgask-2025"
```

## Notes

- Workload Identity Federation is more secure than service account keys
- No key rotation needed
- Works for external workloads
- Requires initial setup but then works automatically

