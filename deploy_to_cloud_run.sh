#!/bin/bash
set -e # Exit immediately if a command exits with a non-zero status

# Check if Google Cloud SDK is installed
if ! command -v gcloud &> /dev/null; then
    # Try adding common Homebrew path if not found
    if [ -d "/usr/local/share/google-cloud-sdk/bin" ]; then
        export PATH="/usr/local/share/google-cloud-sdk/bin:$PATH"
    fi
fi

if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: Google Cloud SDK (gcloud) is not installed."
    echo "Please install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if Project ID is provided
if [ -z "$1" ]; then
    echo "Usage: ./deploy_to_cloud_run.sh <PROJECT_ID>"
    echo "Example: ./deploy_to_cloud_run.sh my-gcp-project-id"
    exit 1
fi

PROJECT_ID=$1
SERVICE_NAME="shouldisignthis"
REGION="us-central1" # You can change this to your preferred region

echo "🚀 Deploying to Google Cloud Run..."
echo "Project: $PROJECT_ID"
echo "Service: $SERVICE_NAME"
echo "Region:  $REGION"

# Enable necessary services
echo "🔌 Enabling Cloud Build and Cloud Run APIs..."
gcloud services enable cloudbuild.googleapis.com run.googleapis.com --project "$PROJECT_ID"

# Submit build to Cloud Build
echo "🔨 Building container image..."
gcloud builds submit --tag "gcr.io/$PROJECT_ID/$SERVICE_NAME" --project "$PROJECT_ID"

# Deploy to Cloud Run
echo "☁️ Deploying to Cloud Run..."
gcloud run deploy "$SERVICE_NAME" \
    --image "gcr.io/$PROJECT_ID/$SERVICE_NAME" \
    --platform managed \
    --region "$REGION" \
    --allow-unauthenticated \
    --set-env-vars "GOOGLE_API_KEY=${GOOGLE_API_KEY}" \
    --project "$PROJECT_ID"

echo "✅ Deployment Complete!"
