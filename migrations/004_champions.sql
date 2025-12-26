-- Migration: Champions
-- Description: Create table for tracking task champions

CREATE TABLE IF NOT EXISTS champions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    responsibility VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_champions_name ON champions(name);

-- Grant permissions to store_tracker user
GRANT SELECT, INSERT, UPDATE, DELETE ON champions TO store_tracker;
GRANT USAGE, SELECT ON SEQUENCE champions_id_seq TO store_tracker;
