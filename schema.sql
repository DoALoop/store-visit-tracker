-- PostgreSQL Schema for Store Visit Tracker
-- Normalized Note Structure (v2.0)
-- Run this file to create the database schema
--
-- IMPORTANT: If you have an existing installation with data, run:
--   psql -U [user] -d [database] -f migrations/001_normalize_notes.sql
-- to migrate to the new normalized structure.

-- ============================================================================
-- Main store_visits table (metrics and visit overview)
-- ============================================================================

CREATE TABLE IF NOT EXISTS store_visits (
    id SERIAL PRIMARY KEY,
    "storeNbr" VARCHAR(50) NOT NULL,
    calendar_date DATE NOT NULL,
    rating VARCHAR(20),
    -- Sales metrics
    sales_comp_yest DECIMAL(10,2),
    sales_index_yest DECIMAL(10,2),
    sales_comp_wtd DECIMAL(10,2),
    sales_index_wtd DECIMAL(10,2),
    sales_comp_mtd DECIMAL(10,2),
    sales_index_mtd DECIMAL(10,2),
    -- Operational metrics
    vizpick DECIMAL(10,2),
    overstock INTEGER,
    picks INTEGER,
    vizfashion DECIMAL(10,2),
    modflex DECIMAL(10,2),
    tag_errors INTEGER,
    mods INTEGER,
    pcs INTEGER,
    pinpoint DECIMAL(10,2),
    ftpr DECIMAL(10,2),
    presub DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- Normalized Note Tables (NEW STRUCTURE v2.0)
-- Each note type has its own table for proper normalization
-- ============================================================================

-- Store observations and general notes
CREATE TABLE IF NOT EXISTS store_visit_notes (
    id SERIAL PRIMARY KEY,
    visit_id INTEGER NOT NULL REFERENCES store_visits(id) ON DELETE CASCADE,
    note_text TEXT NOT NULL,
    sequence INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Market and competitive notes
CREATE TABLE IF NOT EXISTS store_market_notes (
    id SERIAL PRIMARY KEY,
    visit_id INTEGER NOT NULL REFERENCES store_visits(id) ON DELETE CASCADE,
    note_text TEXT NOT NULL,
    sequence INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- What's working well / positive observations
CREATE TABLE IF NOT EXISTS store_good_notes (
    id SERIAL PRIMARY KEY,
    visit_id INTEGER NOT NULL REFERENCES store_visits(id) ON DELETE CASCADE,
    note_text TEXT NOT NULL,
    sequence INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Top 3 opportunities and areas for improvement
CREATE TABLE IF NOT EXISTS store_improvement_notes (
    id SERIAL PRIMARY KEY,
    visit_id INTEGER NOT NULL REFERENCES store_visits(id) ON DELETE CASCADE,
    note_text TEXT NOT NULL,
    sequence INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- DEPRECATED COLUMNS (v1.0 - kept for backward compatibility)
-- These will be removed in a future version
-- Use the normalized note tables above instead
-- ============================================================================

ALTER TABLE store_visits ADD COLUMN IF NOT EXISTS store_notes TEXT;
ALTER TABLE store_visits ADD COLUMN IF NOT EXISTS mkt_notes TEXT;
ALTER TABLE store_visits ADD COLUMN IF NOT EXISTS good TEXT;
ALTER TABLE store_visits ADD COLUMN IF NOT EXISTS top_3 TEXT;

-- ============================================================================
-- Indexes for common queries
-- ============================================================================

-- Main visit lookups
CREATE INDEX IF NOT EXISTS idx_store_date ON store_visits("storeNbr", calendar_date);
CREATE INDEX IF NOT EXISTS idx_calendar_date ON store_visits(calendar_date DESC);
CREATE INDEX IF NOT EXISTS idx_store_nbr ON store_visits("storeNbr");

-- Note lookups by visit
CREATE INDEX IF NOT EXISTS idx_visit_notes_visit_id ON store_visit_notes(visit_id);
CREATE INDEX IF NOT EXISTS idx_market_notes_visit_id ON store_market_notes(visit_id);
CREATE INDEX IF NOT EXISTS idx_good_notes_visit_id ON store_good_notes(visit_id);
CREATE INDEX IF NOT EXISTS idx_improvement_notes_visit_id ON store_improvement_notes(visit_id);

-- Full-text search on note content (requires PostgreSQL with FTS support)
CREATE INDEX IF NOT EXISTS idx_visit_notes_text ON store_visit_notes USING GIN(to_tsvector('english', note_text));
CREATE INDEX IF NOT EXISTS idx_market_notes_text ON store_market_notes USING GIN(to_tsvector('english', note_text));
CREATE INDEX IF NOT EXISTS idx_good_notes_text ON store_good_notes USING GIN(to_tsvector('english', note_text));
CREATE INDEX IF NOT EXISTS idx_improvement_notes_text ON store_improvement_notes USING GIN(to_tsvector('english', note_text));

-- ============================================================================
-- Display schema info
-- ============================================================================
\echo 'Store Visit Tracker Schema Created Successfully (v2.0 - Normalized)'
\echo ''
\echo 'Main table:'
\d store_visits
\echo ''
\echo 'Note tables:'
\d store_visit_notes
\d store_market_notes
\d store_good_notes
\d store_improvement_notes
