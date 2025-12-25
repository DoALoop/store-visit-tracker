# Store Visit Tracker 🐕

**A powerful web and mobile application for digitizing and analyzing store visit notes using AI.**

---

## Quick Deploy Cheat Sheet

### Step 1: Push from your Mac (test machine)

```bash
cd ~/Desktop/Coding/store-visit-tracker

# Add all changes, commit, and push
git add .
git commit -m "your message here"
git push origin main
```

Or use the deploy script:
```bash
./deploy.sh
```

### Step 2: SSH into your Proxmox server

```bash
ssh storeapp@192.168.0.9
```

### Step 3: Pull and restart on the server

```bash
cd /home/storeapp/store-visit-tracker
git pull origin main
sudo systemctl restart store-visit-tracker
```

Or use the update script (does pull + restart):
```bash
/home/storeapp/store-visit-tracker/update.sh
```

### Useful server commands

```bash
# Check if service is running
sudo systemctl status store-visit-tracker

# View live logs
sudo journalctl -u store-visit-tracker -f

# Restart service only (no pull)
sudo systemctl restart store-visit-tracker

# Stop service
sudo systemctl stop store-visit-tracker
```

---

## 📍 GitHub Project

**Repository:** https://github.com/DoALoop/store-visit-tracker
**Owner:** DoALoop

---

## 🎯 Project Overview

Store Visit Tracker is a full-stack application designed to help District Managers digitize handwritten store visit notes and analyze them using AI. The system includes:

### Core Features

✅ **Upload & AI Analysis**
- Take a photo of handwritten notes with your camera or upload from gallery
- Vertex AI (Gemini Vision) automatically transcribes and categorizes the notes
- Extract structured data: store number, date, rating, notes, metrics
- Intelligent duplicate detection before saving

✅ **Visit Management**
- Browse all store visits in a clean table view
- Search prior tours by store number
- Click any visit brief to see full details
- View comprehensive metrics and observations

✅ **Metrics Tracking**
- 17 operational & sales metrics automatically extracted:
  - Sales Comp (Yesterday, WTD, MTD)
  - Sales Index (Yesterday, WTD, MTD)
  - Vizpick, Overstock, Picks, Viz Fashion
  - Modflex, Tag Errors, Mods, PCS
  - Pinpoint, FTPR, Presub

✅ **Market Intelligence**
- Track market notes and competitive insights
- Mark market items as completed/incomplete
- Dashboard view of store health summaries

✅ **Mobile Android App**
- Native Android application for field use
- Search prior visits by store number
- View visit briefs with quick stats
- Click to see full visit details
- Synchronized with web backend

---

## 🏗️ Architecture

### Stack

| Component | Technology | Details |
|-----------|-----------|----------|
| **Backend** | Python 3.10 | Flask web framework |
| **Frontend** | HTML/CSS/JS | Tailwind CSS, Responsive design |
| **Database** | PostgreSQL | store_visits table with 30+ columns |
| **AI/ML** | Google Vertex AI | Gemini 2.5 Flash for vision analysis |
| **Deployment** | Docker/Gunicorn | Container-ready, systemd service |
| **Version Control** | Git | GitHub |

### Deployment Targets

- **Web Frontend:** http://your-server/
- **API Backend:** http://your-server/api/*
- **Execution:** Proxmox VM (storeapp user)
- **Service:** systemd (store-visit-tracker)

---

## 📁 Project Structure

```
store-visit-tracker/
├── main.py                    # Flask app with 8 API endpoints
├── index.html                 # Web frontend (55KB, fully responsive)
├── requirements.txt           # Python dependencies
├── schema.sql                 # PostgreSQL table schema
├── Dockerfile                 # Docker container configuration
├── Procfile                   # Heroku/Cloud Run deployment
├── API_ENDPOINTS.md           # Complete API documentation
├── README.md                  # This file
│
├── Deployment Scripts
├── deploy.sh                  # Local: commit & push to GitHub
├── update.sh                  # Server: pull & restart service
├── start_app.sh               # Server: start the app
├── migrate_database.sh        # Setup: run database migrations
│
├── Database Schemas
├── create_market_notes_table.sql  # Market notes tracking table
├── add_metrics_columns.sql        # Add new metric columns
├── show_columns.sql               # Inspect table structure
│
└── Utility Scripts
    ├── verify_setup.py        # Verify environment & connections
    ├── check_models.py        # Validate data models
    ├── test_gemini.py         # Test Vertex AI connection
    └── scaffold_android.py    # Android client scaffolding
```

---

## 🚀 Deployment Guide

### Local Development Setup

#### 1. Clone Repository

```bash
git clone https://github.com/DoALoop/store-visit-tracker.git
cd store-visit-tracker
```

#### 2. Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install packages
pip install -r requirements.txt
```

#### 3. Configure Environment

Create a `.env` file in the project root:

```bash
# Google Cloud / Vertex AI
GOOGLE_PROJECT_ID=your-gcp-project-id
GOOGLE_LOCATION=us-central1

# PostgreSQL Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=store_visits
DB_USER=store_tracker
DB_PASSWORD=your-secure-password
```

#### 4. Setup Database

```bash
# Connect to your PostgreSQL instance
psql -h localhost -U postgres -d store_visits

# Run schema
\i schema.sql

# Verify table created
\d store_visits
```

#### 5. Run Locally

```bash
python main.py
```

Visit: http://127.0.0.1:5000

---

### Production Deployment (Proxmox Server)

#### Prerequisites

- Proxmox VM with Ubuntu 20.04+
- Python 3.10+
- PostgreSQL 12+
- Git installed
- Systemd for service management

#### One-Time Setup

```bash
# SSH into your Proxmox server
ssh your-proxmox-ip

# Create app user and directory
sudo useradd -m -d /home/storeapp storeapp
sudo mkdir -p /home/storeapp/store-visit-tracker
sudo chown storeapp:storeapp /home/storeapp/store-visit-tracker

# Clone the repository
sudo -u storeapp git clone https://github.com/DoALoop/store-visit-tracker.git /home/storeapp/store-visit-tracker
cd /home/storeapp/store-visit-tracker

# Create virtual environment
sudo -u storeapp python3 -m venv /home/storeapp/store-visit-tracker/venv

# Create .env file
sudo -u storeapp nano /home/storeapp/store-visit-tracker/.env
# Add your configuration here

# Install dependencies
sudo -u storeapp /home/storeapp/store-visit-tracker/venv/bin/pip install -r requirements.txt

# Setup database
sudo -u storeapp /home/storeapp/store-visit-tracker/migrate_database.sh
```

#### Create Systemd Service

Create `/etc/systemd/system/store-visit-tracker.service`:

```ini
[Unit]
Description=Store Visit Tracker Application
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=notify
User=storeapp
Group=storeapp
WorkingDirectory=/home/storeapp/store-visit-tracker
Environment="PATH=/home/storeapp/store-visit-tracker/venv/bin"
Environment="FLASK_APP=main.py"
Environment="PORT=8080"
ExecStart=/home/storeapp/store-visit-tracker/venv/bin/gunicorn --bind 0.0.0.0:8080 --workers 4 --threads 8 --timeout 120 main:app
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
KillSignal=SIGQUIT
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable store-visit-tracker
sudo systemctl start store-visit-tracker
```

#### Deploy Updates to Production

**Step 1: Commit & Push to GitHub (Your Local Machine)**

```bash
cd /path/to/store-visit-tracker
./deploy.sh
# or manually:
git add .
git commit -m "Your commit message"
git push origin main
```

**Step 2: Pull & Restart on Server**

```bash
# SSH into your server
ssh your-proxmox-ip

# Run the update script
sudo -u storeapp /home/storeapp/store-visit-tracker/update.sh
```

This will:
- Pull latest code from GitHub
- Install/update Python dependencies
- Restart the systemd service
- Verify it's running

#### Verify Deployment

```bash
# Check service status
sudo systemctl status store-visit-tracker

# View live logs
sudo journalctl -u store-visit-tracker -f

# View last 50 log lines
sudo journalctl -u store-visit-tracker -n 50

# Test API endpoint
curl http://your-proxmox-ip:8080/api/visits
```

---

## 📡 API Endpoints

All endpoints are documented in [API_ENDPOINTS.md](./API_ENDPOINTS.md).

### Quick Reference

| Method | Endpoint | Purpose |
|--------|----------|----------|
| GET | `/` | Web frontend |
| GET | `/api/visits?storeNbr=1234` | List visit briefs |
| **GET** | **`/api/visit/<id>`** | **Full visit details** ⭐ NEW |
| POST | `/api/analyze-visit` | AI analyze image |
| POST | `/api/save-visit` | Save visit to DB |
| GET | `/api/check-duplicate` | Check for duplicates |
| GET | `/api/summary` | Store health summary |
| GET | `/api/market-notes` | Get all market notes |
| POST | `/api/market-notes/toggle` | Mark note complete |

**See [API_ENDPOINTS.md](./API_ENDPOINTS.md) for full documentation with examples.**

---

## 🔄 Workflow

### Web/Desktop User Flow

1. **Upload Notes**
   - User clicks "Home" tab
   - Takes photo or uploads image of handwritten notes
   - Clicks "Analyze Notes"
   - Vertex AI transcribes and structures the data

2. **Review & Save**
   - System checks for duplicates
   - Shows detected data (store, date, rating, metrics, notes)
   - User confirms and saves

3. **Browse Visits**
   - Click "Visits" tab to see all recent visits
   - Click "Prior Tours" to search by store
   - Click any visit brief to see full details
   - View all metrics and notes in detail modal

4. **Market Intelligence**
   - Click "Summary" to see store health
   - Check market notes from all visits
   - Mark completed items as done

### Mobile (Android) User Flow

1. Search for store number
2. View list of prior visit briefs
3. Click to view full visit details
4. See all information with proper formatting

---

## 🗄️ Database Schema

### store_visits Table

Main table storing visit metadata and metrics:

```sql
CREATE TABLE store_visits (
    id SERIAL PRIMARY KEY,
    "storeNbr" VARCHAR(50) NOT NULL,
    calendar_date DATE NOT NULL,
    rating VARCHAR(20),                -- Green, Yellow, Red

    -- Sales Metrics
    sales_comp_yest DECIMAL(10,2),     -- Sales comp vs yesterday (%)
    sales_index_yest DECIMAL(10,2),    -- Sales index vs yesterday
    sales_comp_wtd DECIMAL(10,2),      -- Sales comp WTD (%)
    sales_index_wtd DECIMAL(10,2),     -- Sales index WTD
    sales_comp_mtd DECIMAL(10,2),      -- Sales comp MTD (%)
    sales_index_mtd DECIMAL(10,2),     -- Sales index MTD

    -- Operational Metrics
    vizpick DECIMAL(10,2),             -- Vizpick score (%)
    overstock INTEGER,                 -- Overstock count
    picks INTEGER,                     -- Picks count
    vizfashion DECIMAL(10,2),          -- Viz Fashion score (%)
    modflex DECIMAL(10,2),             -- Modflex score (%)
    tag_errors INTEGER,                -- Tag errors count
    mods INTEGER,                      -- Mods count
    pcs INTEGER,                       -- PCS count
    pinpoint DECIMAL(10,2),            -- Pinpoint score (%)
    ftpr DECIMAL(10,2),                -- FTPR score (%)
    presub DECIMAL(10,2),              -- Presub score (%)

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Normalized Note Tables

Notes are stored in separate tables (one row per note):

| Table | Purpose |
|-------|---------|
| `store_visit_notes` | Store observations |
| `store_market_notes` | Market/competitive notes |
| `store_good_notes` | What's working well |
| `store_improvement_notes` | Top 3 opportunities |

```sql
-- Example: store_visit_notes (same structure for all note tables)
CREATE TABLE store_visit_notes (
    id SERIAL PRIMARY KEY,
    visit_id INTEGER REFERENCES store_visits(id) ON DELETE CASCADE,
    note_text TEXT NOT NULL,
    sequence INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### market_note_completions Table

Tracks completion status of market notes:

```sql
CREATE TABLE market_note_completions (
    id SERIAL PRIMARY KEY,
    visit_id INTEGER NOT NULL REFERENCES store_visits(id),
    note_text TEXT NOT NULL,
    completed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(visit_id, note_text)
);
```

---

## 🛠️ Configuration

### Environment Variables

```bash
# Google Cloud / Vertex AI
GOOGLE_PROJECT_ID=your-gcp-project-id
GOOGLE_LOCATION=us-central1

# PostgreSQL
DB_HOST=localhost          # or your remote DB host
DB_PORT=5432
DB_NAME=store_visits
DB_USER=store_tracker
DB_PASSWORD=secure-password

# Flask
FLASK_ENV=production
PORT=8080
```

### Performance Settings

**Gunicorn Configuration** (in update.sh):

```bash
gunicorn --bind 0.0.0.0:8080 --workers 4 --threads 8 --timeout 120 main:app
```

- **workers**: Process count (increase for high load)
- **threads**: Threads per worker
- **timeout**: Request timeout in seconds

---

## 📊 Recent Updates

### Latest Features (December 2024)

#### ✨ Full Visit Details Modal

**Commit:** e4c460c  
**Date:** December 18, 2024

- Added clickable visit briefs on Prior Tours page
- New modal displays complete visit information
- Includes all 17 metrics with color-coded cards
- Responsive design (mobile/desktop)
- Loading states and error handling
- Click X or outside to close

#### 🆕 API Endpoint for Full Visit Data

**Commit:** 1611242  
**Date:** December 18, 2024

- New `GET /api/visit/<visit_id>` endpoint
- Returns complete visit record with all fields
- Enables Android app to show full details
- Proper error handling (404, 500)

---

## 🐛 Troubleshooting

### Service Won't Start

```bash
# Check logs
sudo journalctl -u store-visit-tracker -n 100

# Verify Python environment
sudo -u storeapp /home/storeapp/store-visit-tracker/venv/bin/python --version

# Test import
sudo -u storeapp /home/storeapp/store-visit-tracker/venv/bin/python -c "import flask; print(flask.__version__)"
```

### Database Connection Issues

```bash
# Test PostgreSQL connection
sudo -u storeapp psql -h DB_HOST -U DB_USER -d DB_NAME -c "SELECT 1"

# Check credentials in .env
sudo -u storeapp cat /home/storeapp/store-visit-tracker/.env
```

### AI Analysis Not Working

```bash
# Test Vertex AI connection
sudo -u storeapp python /home/storeapp/store-visit-tracker/test_gemini.py

# Verify GCP credentials
sudo -u storeapp cat $GOOGLE_APPLICATION_CREDENTIALS
```

### Port Already in Use

```bash
# Change PORT in .env or systemd service
# Find process using port 8080
sudo lsof -i :8080

# Kill if needed
sudo kill -9 <PID>
```

---

## 📚 Additional Resources

- **API Documentation:** [API_ENDPOINTS.md](./API_ENDPOINTS.md)
- **Database Schema:** [schema.sql](./schema.sql)
- **Google Cloud Setup:** [Google Cloud Console](https://console.cloud.google.com)
- **Vertex AI Docs:** [Vertex AI Documentation](https://cloud.google.com/vertex-ai/docs)
- **Flask Documentation:** [Flask Docs](https://flask.palletsprojects.com)
- **PostgreSQL Documentation:** [PostgreSQL Docs](https://www.postgresql.org/docs)

---

## 👤 Project Owner

**Tim Barnhill** (DoALoop)

---

## 📄 License

Personal Project - All Rights Reserved

---

## 🐕 Made with ❤️ by Radar

*Code Puppy - Making software development fun, one woof at a time!*

---

**Last Updated:** December 25, 2024  
**Version:** 1.2.0  
**Status:** ✅ Production Ready
