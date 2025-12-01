#!/bin/bash
# Script to generate OIDC token for Workload Identity Federation
# This script outputs the OIDC token in the format required by Workload Identity Federation

# Get the audience (provider resource name)
# Replace PROJECT_NUMBER with your actual project number
PROJECT_NUMBER=1031684980612
AUDIENCE="https://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/firebase-pool/providers/firebase-provider"

# Method 1: Use gcloud to get OIDC token (if gcloud is installed and authenticated)
if command -v gcloud &> /dev/null; then
    TOKEN=$(gcloud auth print-identity-token --audience="$AUDIENCE" 2>/dev/null)
    if [ -n "$TOKEN" ]; then
        # Output in the format expected by Workload Identity Federation
        echo "{\"version\":1,\"success\":true,\"token_type\":\"urn:ietf:params:oauth:token-type:jwt\",\"expiration_time\":$(($(date +%s) + 3600)),\"id_token\":\"$TOKEN\"}"
        exit 0
    fi
fi

# Method 2: If gcloud is not available, you need to implement your OIDC token generation
# For example, using curl to get token from your OIDC provider:
# TOKEN=$(curl -X POST "YOUR_OIDC_TOKEN_ENDPOINT" \
#   -H "Content-Type: application/x-www-form-urlencoded" \
#   -d "grant_type=client_credentials&client_id=YOUR_CLIENT_ID&client_secret=YOUR_CLIENT_SECRET" \
#   | jq -r '.access_token')
# 
# Then output in the required format:
# echo "{\"version\":1,\"success\":true,\"token_type\":\"urn:ietf:params:oauth:token-type:jwt\",\"expiration_time\":$(($(date +%s) + 3600)),\"id_token\":\"$TOKEN\"}"

echo "{\"version\":1,\"success\":false,\"code\":\"COMMAND_NOT_FOUND\",\"message\":\"gcloud CLI not found or not authenticated\"}" >&2
exit 1

