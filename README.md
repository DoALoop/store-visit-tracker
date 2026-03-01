# Store Visit Tracker 🐕

**A full-stack web application for digitizing and analyzing store visit notes using AI, with an integrated AI assistant (JaxAI) for conversational data access.**

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
- Take multiple photos of handwritten notes or upload a batch from the gallery
- Vertex AI (Gemini 2.5 Flash) analyzes all images together to transcribe and categorize the notes
- Extract structured data: store number, date, rating, notes, metrics
- Manual visit entry option for direct data input
- Intelligent duplicate detection before saving
- Photo uploads attached to visits

✅ **JaxAI Assistant**
- Conversational AI chatbot powered by Gemini for querying all app data
- Natural language access to visits, market notes, gold stars, contacts, and more
- Can take actions: mark gold stars complete, create tasks, manage contacts, etc.
- ADK-ready architecture with manual regex-based fallback routing
- Smart Brevity formatting for summaries and insights

✅ **Visit Management**
- Browse all store visits in a clean table view
- Search prior tours by store number
- Click any visit brief to see full details
- View comprehensive metrics and observations
- Edit visit details and individual notes inline
- Delete visits or individual notes
- Market selector for filtering by Market 399 or 451

✅ **Metrics Tracking**
- 21 operational & sales metrics automatically extracted:
  - Sales Comp (Yesterday, WTD, MTD)
  - Sales Index (Yesterday, WTD, MTD)
  - Vizpick, Overstock, Picks, Viz Fashion
  - Modflex, Tag Errors, Mods, PCS
  - Pinpoint, FTPR, Presub
  - Topstock Grocery, Vizpick Health, Cases, Locations

✅ **Market Intelligence**
- Track market notes with assignments, status tracking, and threaded updates
- Filter notes by status (Outstanding / Completed)
- Assign notes to stores or individuals with due dates
- Editable note content and inline update management
- Dashboard view of store health summaries

✅ **Gold Star Notes**
- Weekly store tracking with fiscal week alignment (Saturday start)
- Toggle gold star completion per store
- Week navigation to review historical gold star data
- Market filtering support

✅ **Champions**
- Task ownership tracking for team members
- CRUD management of champion assignments

✅ **Issues & Feedback Tracker**
- Log and track issues with status (Open, In Progress, Stalled, Completed)
- Group issues by status for quick triage
- Clickable cards with edit modals

✅ **Mentee Circle**
- Track mentees with notes and development progress
- CRUD management with minimal required fields

✅ **Contacts**
- Searchable contact directory with smart search (plural/alias handling)
- CSV import utility for bulk loading
- AI-powered smart-add via natural language

✅ **Enablers**
- Track tips, tricks, and ways of working
- Walmart fiscal week assignment
- Toggle completion and status management

✅ **Notes Module**
- Obsidian-style note management with wiki-link support
- Tag-based organization and backlink tracking
- AI-powered insights on note content
- Task extraction from notes with status tracking
- Photo attachments on notes
- Natural language note processing

✅ **Standalone Tasks**
- Task management with priorities, assignments, and due dates
- Task lists for organization
- Smart-add via natural language

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
| **Backend** | Python 3.12 | Flask web framework |
| **Frontend** | HTML/CSS/JS | Tailwind CSS, Everyday Sans font, Walmart blue (#0053E2) |
| **Database** | PostgreSQL | 15+ tables with 19 migrations |
| **AI/ML** | Google Vertex AI | Gemini 2.5 Flash for vision analysis & JaxAI |
| **AI Agent** | Google ADK | JaxAI chatbot with tool-use architecture |
| **LLM Abstraction** | LLMProvider | Swappable providers (Gemini, Ollama via LiteLLM) |
| **Deployment** | Gunicorn | Proxmox VM, systemd service |
| **Version Control** | Git | GitHub |

### Deployment Targets

- **Web Frontend:** http://your-server/
- **API Backend:** http://your-server/api/* (60+ endpoints)
- **Execution:** Proxmox VM (storeapp user)
- **Service:** systemd (store-visit-tracker)

---

## 📁 Project Structure

```
store-visit-tracker/
├── main.py                    # Flask app with 60+ API endpoints
├── index.html                 # Web frontend (fully responsive, Walmart-themed)
├── requirements.txt           # Python dependencies
├── schema.sql                 # PostgreSQL base table schema
├── API_ENDPOINTS.md           # API documentation
├── MIGRATION_GUIDE.md         # Database migration guide
├── README.md                  # This file
│
├── JaxAI Agent
│   ├── jax_agent.py           # JaxAI orchestrator (ADK + manual fallback)
│   ├── manual_router.py       # Regex-based fallback routing
│   ├── llm_provider.py        # LLM provider abstraction (Gemini/Ollama)
│   └── tools/                 # JaxAI tool modules
│       ├── __init__.py        # Tool registry (query + action tools)
│       ├── visits.py          # Visit search, details, trends, comparisons
│       ├── notes.py           # Market notes, insights, status queries
│       ├── team.py            # Champions, mentees, contacts
│       ├── tracking.py        # Gold stars, enablers, issues, tasks, user notes
│       ├── summary.py         # Summary statistics
│       ├── actions.py         # Write operations (create, update, delete)
│       ├── db.py              # Database connection for tools
│       └── fiscal.py          # Walmart fiscal calendar utilities
│
├── Deployment & Setup Scripts
│   ├── deploy.sh              # Local: commit & push to GitHub
│   ├── update.sh              # Server: pull & restart service
│   ├── start_local.sh         # Local: start Flask dev server
│   ├── setup_mac.sh           # Mac dev environment setup (Homebrew, Python, PostgreSQL)
│   └── migrate_database.sh    # Run database migrations
│
├── Database
│   ├── schema.sql             # Base table schema
│   ├── migrations/            # 19 incremental migration files (001-019)
│   ├── create_market_notes_table.sql
│   ├── add_metrics_columns.sql
│   └── show_columns.sql
│
├── fonts/                     # Everyday Sans font files (Bold, Medium, Regular)
│
└── Utility Scripts
    ├── verify_setup.py        # Verify environment & connections
    ├── check_models.py        # Validate data models
    ├── test_gemini.py         # Test Vertex AI connection
    ├── import_contacts.py     # CSV contact import utility
    └── scaffold_android.py    # Android client scaffolding
```

---

## 🚀 Deployment Guide

### Local Development Setup

#### Quick Setup (Mac)

```bash
# Run the automated setup script (installs Homebrew, Python, PostgreSQL, etc.)
./setup_mac.sh
```

#### Manual Setup

#### 1. Clone Repository

```bash
git clone https://github.com/DoALoop/store-visit-tracker.git
cd store-visit-tracker
```

#### 2. Install Dependencies

```bash
# Create virtual environment (Python 3.12+)
python3 -m venv venv
source venv/bin/activate

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

# Run base schema
\i schema.sql

# Run all migrations
./migrate_database.sh
```

#### 5. Run Locally

```bash
./start_local.sh
# or manually:
python main.py
```

Visit: http://127.0.0.1:8080

---

### Production Deployment (Proxmox Server)

#### Prerequisites

- Proxmox VM with Ubuntu 20.04+
- Python 3.12+
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

| Category | Key Endpoints |
|----------|--------------|
| **Visits** | `GET /api/visits`, `GET /api/visit/<id>`, `POST /api/analyze-visit`, `POST /api/save-visit`, `PUT /api/visits/<id>`, `DELETE /api/visits/<id>` |
| **Notes (Visit)** | `DELETE /api/notes/<type>/<id>`, `PUT /api/notes/<type>/<id>`, `POST /api/visits/<id>/notes` |
| **Market Notes** | `GET /api/market-notes`, `POST /api/market-notes/update`, `POST /api/market-notes/toggle`, `POST /api/market-notes/rename`, `POST /api/market-notes/assign-store`, `POST /api/market-notes/add-update` |
| **Gold Stars** | `GET /api/gold-stars/current`, `POST /api/gold-stars/week`, `POST /api/gold-stars/toggle`, `GET /api/gold-stars/stores` |
| **Champions** | `GET /api/champions`, `POST /api/champions`, `PUT /api/champions/<id>`, `DELETE /api/champions/<id>` |
| **Issues** | `GET /api/issues`, `POST /api/issues`, `PUT /api/issues/<id>`, `DELETE /api/issues/<id>` |
| **Notes Module** | `GET /api/notes`, `POST /api/notes`, `PUT /api/notes/<id>`, `GET /api/notes/search`, `GET /api/notes/graph`, `GET /api/notes/ai-insights`, `GET /api/notes/tags` |
| **Tasks** | `GET /api/tasks`, `POST /api/tasks`, `PUT /api/tasks/<id>`, `DELETE /api/tasks/<id>`, `POST /api/tasks/smart-add` |
| **Mentees** | `GET /api/mentees`, `POST /api/mentees`, `PUT /api/mentees/<id>`, `DELETE /api/mentees/<id>` |
| **Contacts** | `GET /api/contacts`, `POST /api/contacts`, `PUT /api/contacts/<id>`, `DELETE /api/contacts/<id>`, `POST /api/contacts/smart-add` |
| **Enablers** | `GET /api/enablers`, `POST /api/enablers`, `PUT /api/enablers/<id>`, `POST /api/enablers/<id>/toggle` |
| **JaxAI** | `POST /api/chat` |
| **Photos** | `GET/POST /api/visits/<id>/photos`, `GET/POST /api/notes/<id>/photos` |
| **Other** | `GET /api/summary`, `GET /api/check-duplicate`, `GET /api/status` |

**See [API_ENDPOINTS.md](./API_ENDPOINTS.md) for full documentation with examples.**

---

## 🔄 Workflow

### Web/Desktop User Flow

1. **Upload Notes**
   - User clicks "Home" tab
   - Takes photos or uploads multiple images of handwritten notes
   - Clicks "Analyze Notes" (or use Manual Entry for direct input)
   - Vertex AI analyzes all images collectively to transcribe and structure the data
   - Optionally attach photos to the saved visit

2. **Review & Save**
   - System checks for duplicates
   - Shows detected data (store, date, rating, metrics, notes)
   - User confirms and saves

3. **Browse & Manage Visits**
   - Click "Visits" tab to see all recent visits
   - Click "Prior Tours" to search by store
   - Click any visit brief to see full details
   - Edit visit details or individual notes inline
   - Delete visits or notes as needed
   - Filter by market (399/451)

4. **Market Intelligence**
   - Click "Summary" to see store health
   - Manage market notes with assignments, status, and threaded updates
   - Filter by Outstanding or Completed

5. **Weekly Tracking**
   - Gold Stars: Track weekly focus areas per store with fiscal week navigation
   - Enablers: Manage tips/tricks assigned to specific weeks

6. **Team & People**
   - Champions: Track task ownership
   - Mentee Circle: Manage mentees and development notes
   - Contacts: Searchable directory with smart search

7. **Notes & Tasks**
   - Notes module for personal/project notes with wiki-links and tags
   - Standalone task management with priorities and assignments
   - AI-powered insights on note content

8. **Ask Jax**
   - Use the JaxAI chatbot to query any data conversationally
   - "Show me last visit to store 1234"
   - "Who handles pharmacy?"
   - "Mark gold star 1 complete for store 5678"

### Mobile (Android) User Flow

1. Search for store number
2. View list of prior visit briefs
3. Click to view full visit details
4. See all information with proper formatting

---

## 🗄️ Database Schema

The database uses PostgreSQL with a base schema (`schema.sql`) and 19 incremental migrations in the `migrations/` directory. See [MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md) for details.

### Tables Overview

| Table | Purpose |
|-------|---------|
| `store_visits` | Core visit records with 21+ metric columns |
| `store_visit_notes` | Store observation notes (normalized) |
| `store_market_notes` | Market/competitive notes |
| `store_good_notes` | What's working well |
| `store_improvement_notes` | Top 3 opportunities |
| `market_note_completions` | Market note status, assignments, and updates |
| `gold_star_weeks` | Weekly gold star focus areas |
| `gold_star_stores` | Per-store gold star completion tracking |
| `champions` | Team task ownership |
| `issues` | Issue/feedback tracking (Open, In Progress, Stalled, Completed) |
| `notes` | Obsidian-style notes module |
| `note_links` | Wiki-link connections between notes |
| `note_tasks` | Tasks extracted from notes |
| `note_photos` | Photo attachments on notes |
| `standalone_tasks` | Independent task management |
| `mentees` | Mentee circle tracking |
| `contacts` | Contact directory |
| `enablers` | Tips/tricks with fiscal week assignment |
| `visit_photos` | Photos attached to store visits |

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

### February 2026

- **JaxAI ADK Refactor** - Refactored JaxAI to ADK-ready architecture with domain-organized tools package, LLM provider abstraction, and manual fallback routing
- **JaxAI Actions** - JaxAI can now take write actions (create/delete contacts, tasks, champions, mentees; mark gold stars complete; manage market notes)
- **Contacts Page** - New contacts directory with smart search (plural/alias handling) and JaxAI integration
- **Mac Setup Script** - Automated `setup_mac.sh` for new development environments
- **Market Note Editing** - Fully editable market note modal with inline content editing

### January 2026

- **Mentee Circle** - New page for tracking mentees with notes and development progress
- **Enablers Page** - Track tips/tricks/ways of working with Walmart fiscal week alignment
- **Notes Module** - Obsidian-style note management with wiki-links, tags, backlinks, AI insights, task extraction, and photo attachments
- **Standalone Tasks** - Independent task management with priorities, assignments, smart-add
- **Photo Support** - Photo uploads for both visits and notes
- **Manual Visit Entry** - Direct data entry option alongside AI analysis
- **Issues Tracker** - Full issue/feedback tracking with stalled status, grouped views, editable cards
- **Champions Page** - Task ownership tracking for team members
- **Gold Star Notes** - Weekly store tracking with fiscal week navigation and market filtering
- **Market Notes Overhaul** - Assignments, status tracking, threaded updates, due dates, store assignment
- **Multi-image AI Analysis** - Upload multiple photos for collective Gemini analysis
- **Walmart Branding** - Everyday Sans font and Walmart blue (#0053E2) theme
- **4 New Metrics** - Topstock Grocery, Vizpick Health, Cases, Locations

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
- **Migration Guide:** [MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md)
- **Database Schema:** [schema.sql](./schema.sql)
- **Google Cloud Setup:** [Google Cloud Console](https://console.cloud.google.com)
- **Vertex AI Docs:** [Vertex AI Documentation](https://cloud.google.com/vertex-ai/docs)
- **Google ADK Docs:** [Agent Development Kit](https://google.github.io/adk-docs/)
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

**Last Updated:** February 28, 2026
**Version:** 2.0.0
**Status:** ✅ Production Ready
