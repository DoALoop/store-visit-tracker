-- Migration: Gold Star Notes
-- Description: Create tables for weekly gold star notes and store completions

-- Table for weekly gold star definitions
CREATE TABLE IF NOT EXISTS gold_star_weeks (
    id SERIAL PRIMARY KEY,
    week_start_date DATE NOT NULL UNIQUE,  -- Monday of the week
    note_1 TEXT NOT NULL,
    note_2 TEXT NOT NULL,
    note_3 TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table for tracking store completions of gold stars
CREATE TABLE IF NOT EXISTS gold_star_completions (
    id SERIAL PRIMARY KEY,
    week_id INTEGER NOT NULL REFERENCES gold_star_weeks(id) ON DELETE CASCADE,
    store_nbr VARCHAR(10) NOT NULL,
    note_number INTEGER NOT NULL CHECK (note_number IN (1, 2, 3)),
    completed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(week_id, store_nbr, note_number)
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_gold_star_completions_week ON gold_star_completions(week_id);
CREATE INDEX IF NOT EXISTS idx_gold_star_completions_store ON gold_star_completions(store_nbr);
CREATE INDEX IF NOT EXISTS idx_gold_star_weeks_date ON gold_star_weeks(week_start_date);
