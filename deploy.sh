#!/bin/bash

# Deployment script for Google Cloud Run
# This script deploys the store-visit-tracker application

set -e  # Exit on any error

# Configuration
PROJECT_ID="store-visit-tracker"
SERVICE_NAME="store-visit-tracker"
REGION="us-central1"

echo "🚀 Deploying to Google Cloud Run..."
echo "Project: $PROJECT_ID"
echo "Service: $SERVICE_NAME"
echo "Region: $REGION"
echo ""

# Optional: Commit changes to git before deploying
read -p "Do you want to commit changes to git first? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "📝 Committing changes..."
    git add .
    read -p "Enter commit message: " commit_msg
    git commit -m "$commit_msg" || echo "No changes to commit"
    echo ""
fi

# Deploy to Cloud Run
echo "☁️  Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --source . \
  --project $PROJECT_ID \
  --region $REGION \
  --allow-unauthenticated \
  --platform managed

echo ""
echo "✅ Deployment complete!"
echo ""

# Get and display the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
  --project $PROJECT_ID \
  --region $REGION \
  --format="value(status.url)")

echo "🌐 Your application is live at:"
echo "$SERVICE_URL"
echo ""
