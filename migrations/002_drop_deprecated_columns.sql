-- Migration: Drop deprecated note columns from store_visits table
-- These columns have been replaced by normalized note tables:
--   store_notes    -> store_visit_notes
--   mkt_notes      -> store_market_notes
--   good           -> store_good_notes
--   top_3          -> store_improvement_notes
--
-- IMPORTANT: Only run this after confirming all data has been migrated
-- to the normalized tables using migration 001_normalize_notes.sql

-- Drop the deprecated columns
ALTER TABLE store_visits DROP COLUMN IF EXISTS store_notes;
ALTER TABLE store_visits DROP COLUMN IF EXISTS mkt_notes;
ALTER TABLE store_visits DROP COLUMN IF EXISTS good;
ALTER TABLE store_visits DROP COLUMN IF EXISTS top_3;

\echo 'Deprecated columns dropped successfully'
\echo ''
\d store_visits
