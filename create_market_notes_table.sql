-- Migration script to create market_note_completions table
-- This table tracks which market notes have been completed

-- Create the table
CREATE TABLE IF NOT EXISTS market_note_completions (
    id SERIAL PRIMARY KEY,
    visit_id INTEGER NOT NULL REFERENCES store_visits(id) ON DELETE CASCADE,
    note_text TEXT NOT NULL,
    completed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(visit_id, note_text)
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_market_notes_visit ON market_note_completions(visit_id);
CREATE INDEX IF NOT EXISTS idx_market_notes_completed ON market_note_completions(completed);

-- Display table info
\d market_note_completions
