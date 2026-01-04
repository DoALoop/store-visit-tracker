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
sleep 2

# Kill ALL gunicorn and python processes for this app
echo "🧹 Aggressively cleaning up all processes..."
sudo pkill -9 -f gunicorn 2>/dev/null || true
sudo pkill -9 -f "python.*main" 2>/dev/null || true
sleep 1

# Force kill anything on port 8080
echo "🔪 Killing anything on port 8080..."
sudo fuser -k 8080/tcp 2>/dev/null || true
sleep 2

# Double-check port is free
if sudo lsof -i :8080 > /dev/null 2>&1; then
    echo "⚠️  Port 8080 still in use, force killing..."
    sudo kill -9 $(sudo lsof -t -i :8080) 2>/dev/null || true
    sleep 3
fi

# Reset failed state if any
sudo systemctl reset-failed $SERVICE_NAME 2>/dev/null || true

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
