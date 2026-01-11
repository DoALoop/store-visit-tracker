-- Migration: Create mentees table
-- Description: Track Mentee Circle associates

CREATE TABLE IF NOT EXISTS mentees (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    store_nbr VARCHAR(50),
    position VARCHAR(100),
    cell_number VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_mentees_store ON mentees(store_nbr);
CREATE INDEX IF NOT EXISTS idx_mentees_name ON mentees(name);

-- Grant permissions (adjust user if different in your setup)
GRANT SELECT, INSERT, UPDATE, DELETE ON mentees TO store_tracker;
GRANT USAGE, SELECT ON SEQUENCE mentees_id_seq TO store_tracker;
