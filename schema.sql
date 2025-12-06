-- PostgreSQL Schema for Store Visit Tracker
-- Run this file to create the database schema

-- Create the store_visits table
CREATE TABLE IF NOT EXISTS store_visits (
    id SERIAL PRIMARY KEY,
    "storeNbr" VARCHAR(50) NOT NULL,
    calendar_date DATE NOT NULL,
    rating VARCHAR(20),
    store_notes TEXT,
    mkt_notes TEXT,
    good TEXT,
    top_3 TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_store_date ON store_visits("storeNbr", calendar_date);
CREATE INDEX IF NOT EXISTS idx_calendar_date ON store_visits(calendar_date DESC);
CREATE INDEX IF NOT EXISTS idx_store_nbr ON store_visits("storeNbr");

-- Display table info
\d store_visits
