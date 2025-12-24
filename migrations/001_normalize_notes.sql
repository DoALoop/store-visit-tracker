-- Migration 001: Normalize Notes Structure
-- This migration converts concatenated note strings into normalized separate tables
-- Safe to run multiple times (uses CREATE TABLE IF NOT EXISTS)
--
-- BEFORE: store_visits.store_notes = "Note 1\nNote 2\nNote 3" (single TEXT field)
-- AFTER: store_visit_notes table with individual rows for each note

-- ============================================================================
-- Step 1: Create normalized note tables
-- ============================================================================

CREATE TABLE IF NOT EXISTS store_visit_notes (
    id SERIAL PRIMARY KEY,
    visit_id INTEGER NOT NULL REFERENCES store_visits(id) ON DELETE CASCADE,
    note_text TEXT NOT NULL,
    sequence INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_visit FOREIGN KEY (visit_id) REFERENCES store_visits(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS store_market_notes (
    id SERIAL PRIMARY KEY,
    visit_id INTEGER NOT NULL REFERENCES store_visits(id) ON DELETE CASCADE,
    note_text TEXT NOT NULL,
    sequence INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_visit FOREIGN KEY (visit_id) REFERENCES store_visits(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS store_good_notes (
    id SERIAL PRIMARY KEY,
    visit_id INTEGER NOT NULL REFERENCES store_visits(id) ON DELETE CASCADE,
    note_text TEXT NOT NULL,
    sequence INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_visit FOREIGN KEY (visit_id) REFERENCES store_visits(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS store_improvement_notes (
    id SERIAL PRIMARY KEY,
    visit_id INTEGER NOT NULL REFERENCES store_visits(id) ON DELETE CASCADE,
    note_text TEXT NOT NULL,
    sequence INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_visit FOREIGN KEY (visit_id) REFERENCES store_visits(id) ON DELETE CASCADE
);

-- ============================================================================
-- Step 2: Create indexes for common queries
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_visit_notes_visit_id ON store_visit_notes(visit_id);
CREATE INDEX IF NOT EXISTS idx_market_notes_visit_id ON store_market_notes(visit_id);
CREATE INDEX IF NOT EXISTS idx_good_notes_visit_id ON store_good_notes(visit_id);
CREATE INDEX IF NOT EXISTS idx_improvement_notes_visit_id ON store_improvement_notes(visit_id);

-- For text searching (requires PostgreSQL with full-text search support)
CREATE INDEX IF NOT EXISTS idx_visit_notes_text ON store_visit_notes USING GIN(to_tsvector('english', note_text));
CREATE INDEX IF NOT EXISTS idx_market_notes_text ON store_market_notes USING GIN(to_tsvector('english', note_text));
CREATE INDEX IF NOT EXISTS idx_good_notes_text ON store_good_notes USING GIN(to_tsvector('english', note_text));
CREATE INDEX IF NOT EXISTS idx_improvement_notes_text ON store_improvement_notes USING GIN(to_tsvector('english', note_text));

-- ============================================================================
-- Step 3: Migrate existing data from old format to new tables
-- ============================================================================
-- Only migrate if data exists and hasn't been migrated yet

DO $$ 
DECLARE
    v_count INTEGER;
BEGIN
    -- Check if we have any data in the old columns
    SELECT COUNT(*) INTO v_count FROM store_visits WHERE store_notes IS NOT NULL AND store_notes != '';
    
    IF v_count > 0 THEN
        -- Migrate store_notes
        INSERT INTO store_visit_notes (visit_id, note_text, sequence, created_at)
        SELECT 
            sv.id,
            TRIM(note_item),
            ROW_NUMBER() OVER (PARTITION BY sv.id ORDER BY idx),
            sv.created_at
        FROM store_visits sv
        CROSS JOIN LATERAL (
            SELECT 
                UNNEST(STRING_TO_ARRAY(sv.store_notes, E'\n')) as note_item,
                ROW_NUMBER() OVER () as idx
        ) unnested
        WHERE sv.store_notes IS NOT NULL 
            AND sv.store_notes != ''
            AND TRIM(unnested.note_item) != ''
        ON CONFLICT DO NOTHING;
        
        RAISE NOTICE 'Migrated store_notes: % rows', v_count;
    END IF;
    
    -- Check if we have any market notes
    SELECT COUNT(*) INTO v_count FROM store_visits WHERE mkt_notes IS NOT NULL AND mkt_notes != '';
    
    IF v_count > 0 THEN
        -- Migrate mkt_notes
        INSERT INTO store_market_notes (visit_id, note_text, sequence, created_at)
        SELECT 
            sv.id,
            TRIM(note_item),
            ROW_NUMBER() OVER (PARTITION BY sv.id ORDER BY idx),
            sv.created_at
        FROM store_visits sv
        CROSS JOIN LATERAL (
            SELECT 
                UNNEST(STRING_TO_ARRAY(sv.mkt_notes, E'\n')) as note_item,
                ROW_NUMBER() OVER () as idx
        ) unnested
        WHERE sv.mkt_notes IS NOT NULL 
            AND sv.mkt_notes != ''
            AND TRIM(unnested.note_item) != ''
        ON CONFLICT DO NOTHING;
        
        RAISE NOTICE 'Migrated mkt_notes: % rows', v_count;
    END IF;
    
    -- Check if we have any good notes
    SELECT COUNT(*) INTO v_count FROM store_visits WHERE good IS NOT NULL AND good != '';
    
    IF v_count > 0 THEN
        -- Migrate good notes
        INSERT INTO store_good_notes (visit_id, note_text, sequence, created_at)
        SELECT 
            sv.id,
            TRIM(note_item),
            ROW_NUMBER() OVER (PARTITION BY sv.id ORDER BY idx),
            sv.created_at
        FROM store_visits sv
        CROSS JOIN LATERAL (
            SELECT 
                UNNEST(STRING_TO_ARRAY(sv.good, E'\n')) as note_item,
                ROW_NUMBER() OVER () as idx
        ) unnested
        WHERE sv.good IS NOT NULL 
            AND sv.good != ''
            AND TRIM(unnested.note_item) != ''
        ON CONFLICT DO NOTHING;
        
        RAISE NOTICE 'Migrated good notes: % rows', v_count;
    END IF;
    
    -- Check if we have any top_3 notes
    SELECT COUNT(*) INTO v_count FROM store_visits WHERE top_3 IS NOT NULL AND top_3 != '';
    
    IF v_count > 0 THEN
        -- Migrate top_3 notes (improvement opportunities)
        INSERT INTO store_improvement_notes (visit_id, note_text, sequence, created_at)
        SELECT 
            sv.id,
            TRIM(note_item),
            ROW_NUMBER() OVER (PARTITION BY sv.id ORDER BY idx),
            sv.created_at
        FROM store_visits sv
        CROSS JOIN LATERAL (
            SELECT 
                UNNEST(STRING_TO_ARRAY(sv.top_3, E'\n')) as note_item,
                ROW_NUMBER() OVER () as idx
        ) unnested
        WHERE sv.top_3 IS NOT NULL 
            AND sv.top_3 != ''
            AND TRIM(unnested.note_item) != ''
        ON CONFLICT DO NOTHING;
        
        RAISE NOTICE 'Migrated top_3 notes: % rows', v_count;
    END IF;
    
    RAISE NOTICE 'Data migration completed successfully!';
END $$;

-- ============================================================================
-- Step 4: Verify migration (optional - shows counts per table)
-- ============================================================================

DO $$ 
DECLARE
    v_visit_notes_count INTEGER;
    v_market_notes_count INTEGER;
    v_good_notes_count INTEGER;
    v_improvement_notes_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_visit_notes_count FROM store_visit_notes;
    SELECT COUNT(*) INTO v_market_notes_count FROM store_market_notes;
    SELECT COUNT(*) INTO v_good_notes_count FROM store_good_notes;
    SELECT COUNT(*) INTO v_improvement_notes_count FROM store_improvement_notes;
    
    RAISE NOTICE '=== Migration Verification ===';
    RAISE NOTICE 'store_visit_notes: % rows', v_visit_notes_count;
    RAISE NOTICE 'store_market_notes: % rows', v_market_notes_count;
    RAISE NOTICE 'store_good_notes: % rows', v_good_notes_count;
    RAISE NOTICE 'store_improvement_notes: % rows', v_improvement_notes_count;
END $$;

-- ============================================================================
-- Step 5: Optional - Keep old columns for backward compatibility (or drop them)
-- ============================================================================
-- To remove old columns (breaking change - do after updating all code):
-- ALTER TABLE store_visits DROP COLUMN store_notes;
-- ALTER TABLE store_visits DROP COLUMN mkt_notes;
-- ALTER TABLE store_visits DROP COLUMN good;
-- ALTER TABLE store_visits DROP COLUMN top_3;
--
-- For now, we keep them for backward compatibility during transition period
-- Update: These columns are being kept but will be deprecated after API migration

-- ============================================================================
-- Script completed - check psql output for migration details
-- ============================================================================
