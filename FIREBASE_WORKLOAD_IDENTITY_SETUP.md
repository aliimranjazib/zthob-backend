# Firebase Workload Identity Federation Setup

## 🎯 Overview

Workload Identity Federation allows GitHub Actions to authenticate to Google Cloud without storing service account keys. This is the **modern, secure approach** recommended by Google.

## ✅ Benefits

- ✅ **No service account keys** - eliminates security risk
- ✅ **Works with organization policies** - bypasses key creation restrictions
- ✅ **Short-lived credentials** - automatically rotated
- ✅ **GitHub Actions native** - built-in support

## 📋 Prerequisites

- Google Cloud Project: `mgask-2025`
- GitHub repository: `aliimranjazib/zthob-backend`
- Organization Policy Administrator access (to create Workload Identity Pool)

## 🚀 Step-by-Step Setup

### Step 1: Enable Required APIs

```bash
# Enable Identity and Access Management API
gcloud services enable iamcredentials.googleapis.com

# Enable Firebase Cloud Messaging API (V1)
gcloud services enable fcm.googleapis.com
```

### Step 2: Create Workload Identity Pool

```bash
# Set your project
gcloud config set project mgask-2025

# Create Workload Identity Pool
gcloud iam workload-identity-pools create github-pool \
    --project=mgask-2025 \
    --location="global" \
    --display-name="GitHub Actions Pool"

# Create Workload Identity Provider (GitHub)
gcloud iam workload-identity-pools providers create-oidc github-provider \
    --project=mgask-2025 \
    --location="global" \
    --workload-identity-pool="github-pool" \
    --display-name="GitHub Provider" \
    --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
    --issuer-uri="https://token.actions.githubusercontent.com"
```

### Step 3: Create Service Account

```bash
# Create service account for Firebase
gcloud iam service-accounts create github-actions-firebase \
    --project=mgask-2025 \
    --display-name="GitHub Actions Firebase Service Account"

# Grant Firebase Cloud Messaging permissions
gcloud projects add-iam-policy-binding mgask-2025 \
    --member="serviceAccount:github-actions-firebase@mgask-2025.iam.gserviceaccount.com" \
    --role="roles/firebase.admin"

# Grant Service Account Token Creator role (for impersonation)
gcloud iam service-accounts add-iam-policy-binding \
    github-actions-firebase@mgask-2025.iam.gserviceaccount.com \
    --project=mgask-2025 \
    --role="roles/iam.serviceAccountTokenCreator" \
    --member="principalSet://iam.googleapis.com/projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/*"
```

**⚠️ Important:** Replace `PROJECT_NUMBER` with your actual project number. Get it with:
```bash
gcloud projects describe mgask-2025 --format="value(projectNumber)"
```

### Step 4: Allow GitHub Repository to Impersonate Service Account

```bash
# Get your project number first
PROJECT_NUMBER=$(gcloud projects describe mgask-2025 --format="value(projectNumber)")

# Allow specific GitHub repository to use the service account
gcloud iam service-accounts add-iam-policy-binding \
    github-actions-firebase@mgask-2025.iam.gserviceaccount.com \
    --project=mgask-2025 \
    --role="roles/iam.workloadIdentityUser" \
    --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-pool/attribute.repository/aliimranjazib/zthob-backend"
```

### Step 5: Get Workload Identity Pool Resource Name

```bash
# Get the full resource name
gcloud iam workload-identity-pools describe github-pool \
    --project=mgask-2025 \
    --location="global" \
    --format="value(name)"
```

This will output something like:
```
projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool
```

### Step 6: Add GitHub Secrets

Go to your GitHub repository → Settings → Secrets and variables → Actions

Add these secrets:

1. **`WORKLOAD_IDENTITY_PROVIDER`**
   - Value: `projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/providers/github-provider`
   - Get PROJECT_NUMBER: `gcloud projects describe mgask-2025 --format="value(projectNumber)"`

2. **`SERVICE_ACCOUNT`**
   - Value: `github-actions-firebase@mgask-2025.iam.gserviceaccount.com`

3. **`GOOGLE_CLOUD_PROJECT`** (optional, for convenience)
   - Value: `mgask-2025`

## 🔧 Server Setup (One-Time)

Since service account key creation is restricted, we'll use **Application Default Credentials (ADC)** on the server. This is the same method that works locally.

### Option A: Manual Server Setup (Recommended)

SSH into your server and run:

```bash
# Install Google Cloud SDK
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Authenticate
gcloud auth application-default login

# Set project
gcloud config set project mgask-2025

# Verify
gcloud auth application-default print-access-token
```

### Option B: Automated Server Setup via GitHub Actions

The GitHub Actions workflow can set up gcloud on the server automatically. See the workflow file for details.

## 🔧 GitHub Actions Workflow

The workflow is already updated to use Workload Identity Federation. It will:
1. Authenticate using Workload Identity
2. Deploy code to your server
3. Server uses ADC (set up manually or via script)

## 📝 Quick Setup Script

Save this as `setup-workload-identity.sh` and run it:

```bash
#!/bin/bash

PROJECT_ID="mgask-2025"
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
GITHUB_REPO="aliimranjazib/zthob-backend"
SERVICE_ACCOUNT="github-actions-firebase@${PROJECT_ID}.iam.gserviceaccount.com"

echo "Setting up Workload Identity Federation..."
echo "Project: $PROJECT_ID"
echo "Project Number: $PROJECT_NUMBER"
echo "GitHub Repo: $GITHUB_REPO"

# Enable APIs
echo "Enabling APIs..."
gcloud services enable iamcredentials.googleapis.com --project=$PROJECT_ID
gcloud services enable fcm.googleapis.com --project=$PROJECT_ID

# Create Workload Identity Pool
echo "Creating Workload Identity Pool..."
gcloud iam workload-identity-pools create github-pool \
    --project=$PROJECT_ID \
    --location="global" \
    --display-name="GitHub Actions Pool" || echo "Pool may already exist"

# Create Provider
echo "Creating Workload Identity Provider..."
gcloud iam workload-identity-pools providers create-oidc github-provider \
    --project=$PROJECT_ID \
    --location="global" \
    --workload-identity-pool="github-pool" \
    --display-name="GitHub Provider" \
    --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
    --issuer-uri="https://token.actions.githubusercontent.com" || echo "Provider may already exist"

# Create Service Account
echo "Creating Service Account..."
gcloud iam service-accounts create github-actions-firebase \
    --project=$PROJECT_ID \
    --display-name="GitHub Actions Firebase Service Account" || echo "Service account may already exist"

# Grant permissions
echo "Granting permissions..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/firebase.admin"

# Allow Workload Identity Pool to impersonate
echo "Configuring Workload Identity binding..."
gcloud iam service-accounts add-iam-policy-binding \
    ${SERVICE_ACCOUNT} \
    --project=$PROJECT_ID \
    --role="roles/iam.serviceAccountTokenCreator" \
    --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-pool/*"

# Allow GitHub repository to use service account
echo "Allowing GitHub repository access..."
gcloud iam service-accounts add-iam-policy-binding \
    ${SERVICE_ACCOUNT} \
    --project=$PROJECT_ID \
    --role="roles/iam.workloadIdentityUser" \
    --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-pool/attribute.repository/${GITHUB_REPO}"

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Add these to GitHub Secrets:"
echo ""
echo "WORKLOAD_IDENTITY_PROVIDER:"
echo "projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-pool/providers/github-provider"
echo ""
echo "SERVICE_ACCOUNT:"
echo "${SERVICE_ACCOUNT}"
echo ""
echo "GOOGLE_CLOUD_PROJECT:"
echo "${PROJECT_ID}"
```

## 🧪 Testing

After setup, test the authentication:

```bash
# In GitHub Actions, add a test step:
- name: Test Firebase Authentication
  uses: google-github-actions/auth@v2
  with:
    workload_identity_provider: ${{ secrets.WORKLOAD_IDENTITY_PROVIDER }}
    service_account: ${{ secrets.SERVICE_ACCOUNT }}
  
- name: Test Firebase
  run: |
    gcloud auth print-access-token
    # Should output a valid access token
```

## 🔍 Troubleshooting

### Error: "Permission denied"
- Check that the service account has `roles/firebase.admin`
- Verify Workload Identity Pool binding

### Error: "Principal not found"
- Check PROJECT_NUMBER is correct
- Verify repository name matches exactly: `aliimranjazib/zthob-backend`

### Error: "Workload Identity Pool not found"
- Run: `gcloud iam workload-identity-pools list --project=mgask-2025`
- Verify pool was created successfully

## 🖥️ Server Setup Script

Create this script on your server (`/home/zthob-backend/setup-firebase-adc.sh`):

```bash
#!/bin/bash

echo "Setting up Firebase Application Default Credentials..."

# Install Google Cloud SDK if not installed
if ! command -v gcloud &> /dev/null; then
    echo "Installing Google Cloud SDK..."
    curl https://sdk.cloud.google.com | bash
    exec -l $SHELL
fi

# Authenticate
echo "Authenticating with Google Cloud..."
gcloud auth application-default login

# Set project
echo "Setting project to mgask-2025..."
gcloud config set project mgask-2025

# Verify
echo "Verifying authentication..."
if gcloud auth application-default print-access-token &> /dev/null; then
    echo "✅ Firebase ADC setup complete!"
    echo "✅ Django can now use Firebase for push notifications"
else
    echo "❌ Authentication failed. Please check your setup."
    exit 1
fi
```

Make it executable and run:
```bash
chmod +x /home/zthob-backend/setup-firebase-adc.sh
/home/zthob-backend/setup-firebase-adc.sh
```

## 📚 References

- [Workload Identity Federation](https://cloud.google.com/iam/docs/workload-identity-federation)
- [GitHub Actions Authentication](https://github.com/google-github-actions/auth)
- [Firebase Admin SDK](https://firebase.google.com/docs/admin/setup)
- [Application Default Credentials](https://cloud.google.com/docs/authentication/application-default-credentials)

