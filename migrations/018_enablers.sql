-- Migration: 018_enablers.sql
-- Create tables for Enablers feature (tips/tricks/ways of working shared with stores)

-- Table 1: enablers - the main enabler definitions
CREATE TABLE IF NOT EXISTS enablers (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    source VARCHAR(100),           -- Where idea came from (e.g., "Store 123", "Self")
    status VARCHAR(20) DEFAULT 'idea' CHECK (status IN ('idea', 'slide_made', 'presented')),
    week_date DATE,                -- Week this enabler is assigned to (Monday of that week)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table 2: enabler_completions - track which stores have completed/implemented each enabler
CREATE TABLE IF NOT EXISTS enabler_completions (
    id SERIAL PRIMARY KEY,
    enabler_id INTEGER REFERENCES enablers(id) ON DELETE CASCADE,
    store_nbr VARCHAR(10) NOT NULL,
    completed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMP,
    UNIQUE(enabler_id, store_nbr)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_enablers_status ON enablers(status);
CREATE INDEX IF NOT EXISTS idx_enablers_week_date ON enablers(week_date);
CREATE INDEX IF NOT EXISTS idx_enabler_completions_enabler_id ON enabler_completions(enabler_id);
CREATE INDEX IF NOT EXISTS idx_enabler_completions_store ON enabler_completions(store_nbr);

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_enablers_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS enablers_updated_at_trigger ON enablers;
CREATE TRIGGER enablers_updated_at_trigger
    BEFORE UPDATE ON enablers
    FOR EACH ROW
    EXECUTE FUNCTION update_enablers_updated_at();
