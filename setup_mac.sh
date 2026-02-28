#!/bin/bash

# setup_mac.sh
# Automates the setup of the Store Visit Tracker development environment on a new Mac.

set -e  # Exit immediately if a command exits with a non-zero status

echo "🚀 Starting Store Visit Tracker Development Environment Setup..."

# --- Step 1: Check for Homebrew ---
if ! command -v brew &> /dev/null; then
    echo "🍺 Homebrew not found. Installing..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    # Add Homebrew to PATH for Apple Silicon Macs if needed
    if [[ $(uname -m) == 'arm64' ]]; then
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> /Users/$USER/.zprofile
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
else
    echo "✅ Homebrew is already installed."
fi

# --- Step 2: Install System Dependencies ---
echo "📦 Installing System Dependencies (Python, PostgreSQL, Git, GCloud SDK)..."
brew update
brew install python@3.10 postgresql@14 git google-cloud-sdk

# --- Step 3: Start PostgreSQL Service ---
echo "🐘 Starting PostgreSQL service..."
brew services start postgresql@14
# Wait a moment for Postgres to start
sleep 5

# --- Step 4: Clone Repository ---
PROJECT_DIR="$HOME/Desktop/Coding/store-visit-tracker"

if [ -d "$PROJECT_DIR" ]; then
    echo "📂 Project directory already exists at $PROJECT_DIR. Using existing code."
else
    echo "📂 Cloning repository to $PROJECT_DIR..."
    mkdir -p "$HOME/Desktop/Coding"
    git clone https://github.com/DoALoop/store-visit-tracker.git "$PROJECT_DIR"
fi

cd "$PROJECT_DIR"

# --- Step 5: Python Virtual Environment ---
if [ ! -d "venv" ]; then
    echo "🐍 Creating Python virtual environment..."
    python3.10 -m venv venv
fi

echo "🔌 Activating virtual environment and installing requirements..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# --- Step 6: Database Setup ---
echo "🗄️  Setting up Local Database..."

# Create user if not exists
if ! psql postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='store_tracker'" | grep -q 1; then
    echo "   Creating user 'store_tracker'..."
    createuser -s store_tracker
else
    echo "   User 'store_tracker' already exists."
fi

# Create database if not exists
if ! psql -lqt | cut -d \| -f 1 | grep -qw store_visits; then
    echo "   Creating database 'store_visits'..."
    createdb store_visits
    
    # Apply Schema
    echo "   Applying base schema..."
    psql -d store_visits -f schema.sql
    
    # Apply Migrations
    echo "   Applying migrations..."
    for file in migrations/*.sql; do
        if [ -f "$file" ]; then
            echo "   -> $file"
            psql -d store_visits -f "$file"
        fi
    done
else
    echo "✅ Database 'store_visits' already exists."
fi

# --- Step 7: Environment Variables ---
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found!"
    echo "   Creating a template .env file..."
    cat > .env << EOL
# Google Cloud / Vertex AI
GOOGLE_PROJECT_ID=your-project-id-here
GOOGLE_LOCATION=us-central1

# PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_NAME=store_visits
DB_USER=store_tracker
DB_PASSWORD=

# Storage
GCS_BUCKET_NAME=store-visit-photos
EOL
    echo "❗ ACTION REQUIRED: Please open '$PROJECT_DIR/.env' and fill in your GOOGLE_PROJECT_ID and other secrets."
else
    echo "✅ .env file found."
fi

# --- Step 8: Google Cloud Auth ---
echo ""
echo "☁️  Checking Google Cloud Authentication..."
if ! gcloud auth application-default print-access-token &> /dev/null; then
    echo "   Please log in to Google Cloud in the browser window that opens..."
    gcloud auth application-default login
else
    echo "✅ Already authenticated with Google Cloud."
fi

echo ""
echo "🎉 Setup Complete!"
echo "-----------------------------------------------------"
echo "To start working:"
echo "1. cd $PROJECT_DIR"
echo "2. source venv/bin/activate"
echo "3. Update .env with your real secrets if you haven't yet."
echo "4. python main.py"
echo "-----------------------------------------------------"
