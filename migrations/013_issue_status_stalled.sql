-- Migration: Add 'stalled' status to issues
-- Description: Update check constraint on issues table to allow 'stalled' status

-- Drop the existing check constraint
-- Note: We need to find the constraint name. Usually it is issues_status_check or similar.
-- Since we can't easily know the exact auto-generated name without querying, 
-- we will try to drop it by name if standard, or we might need to rely on the user to run this carefully.
-- However, safe way in psql script is:

ALTER TABLE issues DROP CONSTRAINT IF EXISTS issues_status_check;

-- Re-add the constraint with 'stalled' included
ALTER TABLE issues ADD CONSTRAINT issues_status_check 
    CHECK (status IN ('new', 'in_progress', 'stalled', 'completed'));
