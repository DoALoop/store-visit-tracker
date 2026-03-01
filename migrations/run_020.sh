#!/bin/bash
# Run migration 020: Add priority column to issues table
# Usage: Copy to Proxmox server and run: chmod +x run_020.sh && ./run_020.sh

sudo -u postgres psql -d store_visits <<'SQL'
BEGIN;

ALTER TABLE issues ADD COLUMN IF NOT EXISTS priority VARCHAR(10)
    NOT NULL DEFAULT 'medium';

ALTER TABLE issues ADD CONSTRAINT issues_priority_check
    CHECK (priority IN ('high', 'medium', 'low'));

CREATE INDEX IF NOT EXISTS idx_issues_priority ON issues(priority);

COMMIT;
SQL

echo "Migration 020 complete!"
