-- Migration: Notes Received
-- Description: Add column to track if store sent their notes after visit

ALTER TABLE store_visits
ADD COLUMN IF NOT EXISTS notes_received BOOLEAN DEFAULT FALSE;

-- Index for faster filtering
CREATE INDEX IF NOT EXISTS idx_store_visits_notes_received ON store_visits(notes_received);
