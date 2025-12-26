-- Migration: Market Note Enhancements
-- Description: Add assignment, status, and updates tracking for market notes

-- Add new columns to market_note_completions for assignment and status
ALTER TABLE market_note_completions
ADD COLUMN IF NOT EXISTS assigned_to VARCHAR(100),
ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'new' CHECK (status IN ('new', 'in_progress', 'completed', 'on_hold'));

-- Create table for tracking updates/comments on market notes
CREATE TABLE IF NOT EXISTS market_note_updates (
    id SERIAL PRIMARY KEY,
    visit_id INTEGER NOT NULL,
    note_text TEXT NOT NULL,
    update_text TEXT NOT NULL,
    created_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (visit_id) REFERENCES store_visits(id) ON DELETE CASCADE
);

-- Indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_market_note_updates_visit_id ON market_note_updates(visit_id);
CREATE INDEX IF NOT EXISTS idx_market_note_updates_note_text ON market_note_updates(note_text);
CREATE INDEX IF NOT EXISTS idx_market_note_completions_status ON market_note_completions(status);
CREATE INDEX IF NOT EXISTS idx_market_note_completions_assigned ON market_note_completions(assigned_to);

-- Grant permissions to store_tracker user
GRANT SELECT, INSERT, UPDATE, DELETE ON market_note_updates TO store_tracker;
GRANT USAGE, SELECT ON SEQUENCE market_note_updates_id_seq TO store_tracker;
