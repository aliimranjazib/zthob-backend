#!/bin/bash
# Script to check GCP service account details

echo "=========================================="
echo "Checking GCP Service Account"
echo "=========================================="
echo ""

# Check if on GCP
if curl -s -f -H "Metadata-Flavor: Google" http://169.254.169.254/computeMetadata/v1/instance/id > /dev/null 2>&1; then
    echo "✅ Running on GCP"
    echo ""
    
    # Get service account email
    SERVICE_ACCOUNT=$(curl -s -H "Metadata-Flavor: Google" http://169.254.169.254/computeMetadata/v1/instance/service-accounts/default/email)
    echo "Service Account Email: $SERVICE_ACCOUNT"
    
    # Get project ID
    PROJECT_ID=$(curl -s -H "Metadata-Flavor: Google" http://169.254.169.254/computeMetadata/v1/project/project-id)
    echo "Project ID: $PROJECT_ID"
    
    # Get scopes
    echo ""
    echo "Service Account Scopes:"
    curl -s -H "Metadata-Flavor: Google" http://169.254.169.254/computeMetadata/v1/instance/service-accounts/default/scopes | while read scope; do
        echo "  - $scope"
    done
    
    echo ""
    echo "=========================================="
    echo "Next Steps:"
    echo "1. Go to: https://console.cloud.google.com/iam-admin/serviceaccounts?project=$PROJECT_ID"
    echo "2. Find service account: $SERVICE_ACCOUNT"
    echo "3. Grant Firebase Admin SDK Administrator Service Agent role"
    echo "=========================================="
else
    echo "❌ Not running on GCP"
fi

