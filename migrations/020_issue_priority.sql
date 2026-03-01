-- Migration 020: Add priority levels to issues
-- Adds priority column (high/medium/low) with default 'medium'

BEGIN;

ALTER TABLE issues ADD COLUMN IF NOT EXISTS priority VARCHAR(10)
    NOT NULL DEFAULT 'medium';

ALTER TABLE issues ADD CONSTRAINT issues_priority_check
    CHECK (priority IN ('high', 'medium', 'low'));

CREATE INDEX IF NOT EXISTS idx_issues_priority ON issues(priority);

COMMIT;
