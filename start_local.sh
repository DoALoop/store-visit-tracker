#!/bin/bash
# Start local development server

cd "$(dirname "$0")"
source venv/bin/activate
echo "Starting Flask dev server on http://127.0.0.1:5000"
echo "Press Ctrl+C to stop"
echo ""
python main.py
