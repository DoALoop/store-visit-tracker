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

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_store_date ON store_visits("storeNbr", calendar_date);
CREATE INDEX IF NOT EXISTS idx_calendar_date ON store_visits(calendar_date DESC);
CREATE INDEX IF NOT EXISTS idx_store_nbr ON store_visits("storeNbr");

-- Display table info
\d store_visits
