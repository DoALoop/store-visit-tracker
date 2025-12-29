#!/bin/bash
# Start local development server (uses Python 3.12 venv for grpcio compatibility)

cd "$(dirname "$0")"
source venv312/bin/activate
echo "Starting Flask dev server on http://127.0.0.1:8080"
echo "Press Ctrl+C to stop"
echo ""
python main.py
