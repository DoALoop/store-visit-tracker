#!/bin/bash
# Run this script on the production server as root or postgres user
# to apply the missing DB schema migrations

# Configuration
DB_NAME="store_visits"
DB_USER="postgres"
APP_USER="store_tracker"

echo "Running Store Tracker DB migrations..."

sudo -u postgres psql -d "$DB_NAME" <<'EOF'
-- Add store_number column to contacts if missing
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS store_number VARCHAR(50);

-- Create associate_insights table if it doesn't exist
CREATE TABLE IF NOT EXISTS associate_insights (
    id SERIAL PRIMARY KEY,
    contact_id INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    insight_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Grant privileges to the app user
GRANT ALL PRIVILEGES ON TABLE associate_insights TO store_tracker;
GRANT USAGE, SELECT ON SEQUENCE associate_insights_id_seq TO store_tracker;

-- Verify
SELECT column_name FROM information_schema.columns WHERE table_name = 'contacts' AND column_name = 'store_number';
SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'associate_insights') AS insights_table_exists;

\echo 'Migration complete!'
EOF

echo "Done!"
