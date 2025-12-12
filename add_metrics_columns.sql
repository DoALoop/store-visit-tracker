-- Migration script to add metrics columns to existing store_visits table
-- Run this on your existing database to add the new metric columns

-- Sales metrics
ALTER TABLE store_visits ADD COLUMN IF NOT EXISTS sales_comp_yest DECIMAL(10,2);
ALTER TABLE store_visits ADD COLUMN IF NOT EXISTS sales_index_yest DECIMAL(10,2);
ALTER TABLE store_visits ADD COLUMN IF NOT EXISTS sales_comp_wtd DECIMAL(10,2);
ALTER TABLE store_visits ADD COLUMN IF NOT EXISTS sales_index_wtd DECIMAL(10,2);
ALTER TABLE store_visits ADD COLUMN IF NOT EXISTS sales_comp_mtd DECIMAL(10,2);
ALTER TABLE store_visits ADD COLUMN IF NOT EXISTS sales_index_mtd DECIMAL(10,2);

-- Operational metrics
ALTER TABLE store_visits ADD COLUMN IF NOT EXISTS vizpick DECIMAL(10,2);
ALTER TABLE store_visits ADD COLUMN IF NOT EXISTS overstock INTEGER;
ALTER TABLE store_visits ADD COLUMN IF NOT EXISTS picks INTEGER;
ALTER TABLE store_visits ADD COLUMN IF NOT EXISTS vizfashion DECIMAL(10,2);
ALTER TABLE store_visits ADD COLUMN IF NOT EXISTS modflex DECIMAL(10,2);
ALTER TABLE store_visits ADD COLUMN IF NOT EXISTS tag_errors INTEGER;
ALTER TABLE store_visits ADD COLUMN IF NOT EXISTS mods INTEGER;
ALTER TABLE store_visits ADD COLUMN IF NOT EXISTS pcs INTEGER;
ALTER TABLE store_visits ADD COLUMN IF NOT EXISTS pinpoint DECIMAL(10,2);
ALTER TABLE store_visits ADD COLUMN IF NOT EXISTS ftpr DECIMAL(10,2);
ALTER TABLE store_visits ADD COLUMN IF NOT EXISTS presub DECIMAL(10,2);

-- Verify the changes
\d store_visits
