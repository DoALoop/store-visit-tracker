#!/bin/bash

# Server-side update script
# This script pulls latest code from GitHub and restarts the application

set -e  # Exit on any error

# Configuration
APP_DIR="/home/storeapp/store-visit-tracker"
SERVICE_NAME="store-visit-tracker"
VENV_DIR="$APP_DIR/venv"

echo "🔄 Updating Store Visit Tracker application..."
echo ""

cd $APP_DIR

# Pull latest changes from GitHub
echo "⬇️  Pulling latest code from GitHub..."
git pull origin main

# Activate virtual environment
source $VENV_DIR/bin/activate

# Update dependencies
echo "📦 Installing/updating dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Stop the service first
echo "🛑 Stopping service..."
sudo systemctl stop $SERVICE_NAME 2>/dev/null || true
sleep 1

# Kill any orphaned gunicorn processes
echo "🧹 Cleaning up orphaned processes..."
sudo pkill -9 -f gunicorn 2>/dev/null || true
sudo kill -9 $(sudo lsof -t -i :8080) 2>/dev/null || true
sleep 2

# Start the service
echo "🔄 Starting application service..."
sudo systemctl start $SERVICE_NAME

# Check status
sleep 2
if sudo systemctl is-active --quiet $SERVICE_NAME; then
    echo ""
    echo "✅ Application updated and restarted successfully!"
    echo ""
    sudo systemctl status $SERVICE_NAME --no-pager -l
else
    echo ""
    echo "❌ Service failed to start. Check logs:"
    echo "   sudo journalctl -u $SERVICE_NAME -n 50"
    exit 1
fi

echo ""
echo "📊 Application logs:"
echo "   sudo journalctl -u $SERVICE_NAME -f"
echo ""
