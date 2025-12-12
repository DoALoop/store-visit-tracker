#!/bin/bash

# Deployment script - Push to GitHub
# This script commits and pushes changes to GitHub
# The server will pull updates separately

set -e  # Exit on any error

# Configuration
BRANCH="main"

echo "🚀 Deploying to GitHub..."
echo "Branch: $BRANCH"
echo ""

# Check git status
if [[ -n $(git status -s) ]]; then
    echo "📝 You have uncommitted changes:"
    git status -s
    echo ""

    read -p "Do you want to commit these changes? (y/n): " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git add .
        read -p "Enter commit message: " commit_msg
        git commit -m "$commit_msg"
    else
        echo "❌ Deployment cancelled. Please commit your changes first."
        exit 1
    fi
fi

# Push to GitHub
echo "⬆️  Pushing to GitHub ($BRANCH)..."
git push origin $BRANCH

echo ""
echo "✅ Code pushed to GitHub successfully!"
echo ""
echo "📋 Next steps:"
echo "   1. SSH into your Proxmox server"
echo "   2. Run: sudo -u storeapp /home/storeapp/store-visit-tracker/update.sh"
echo ""
