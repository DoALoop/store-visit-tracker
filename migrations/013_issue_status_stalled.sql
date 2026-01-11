-- Migration: Add 'stalled' status to issues
-- Description: Update check constraint on issues table to allow 'stalled' status

BEGIN;

-- Drop the existing check constraint
ALTER TABLE issues DROP CONSTRAINT IF EXISTS issues_status_check;

-- Re-add the constraint with 'stalled' included
ALTER TABLE issues ADD CONSTRAINT issues_status_check 
    CHECK (status IN ('new', 'in_progress', 'stalled', 'completed'));

COMMIT;
