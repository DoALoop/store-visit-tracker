-- Migration 021: Create store_info table
-- Per-store profile data for DM quick reference

BEGIN;

CREATE TABLE IF NOT EXISTS store_info (
    id SERIAL PRIMARY KEY,
    store_number VARCHAR(10) UNIQUE NOT NULL,
    store_format VARCHAR(50) DEFAULT 'Supercenter',
    city VARCHAR(100),
    state VARCHAR(2),
    sales_volume VARCHAR(50),
    operating_income VARCHAR(50),
    building_size VARCHAR(50),
    date_opened DATE,
    last_remodel DATE,
    store_manager VARCHAR(100),
    notes TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Auto-update updated_at on row change
CREATE OR REPLACE FUNCTION update_store_info_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_store_info_updated_at ON store_info;
CREATE TRIGGER trigger_store_info_updated_at
    BEFORE UPDATE ON store_info
    FOR EACH ROW
    EXECUTE FUNCTION update_store_info_updated_at();

-- Pre-seed all 19 stores with defaults
-- Market 399
INSERT INTO store_info (store_number) VALUES
    ('1951'), ('2508'), ('2617'), ('2780'), ('2781'),
    ('2861'), ('2862'), ('3093'), ('3739'), ('5841')
ON CONFLICT (store_number) DO NOTHING;

-- Market 451
INSERT INTO store_info (store_number) VALUES
    ('2002'), ('2117'), ('2280'), ('2458'), ('4488'),
    ('5435'), ('5751'), ('5766'), ('5884')
ON CONFLICT (store_number) DO NOTHING;

CREATE INDEX IF NOT EXISTS idx_store_info_store_number ON store_info(store_number);

-- Grant permissions to store_tracker user
GRANT SELECT, INSERT, UPDATE, DELETE ON store_info TO store_tracker;
GRANT USAGE, SELECT ON SEQUENCE store_info_id_seq TO store_tracker;

COMMIT;
