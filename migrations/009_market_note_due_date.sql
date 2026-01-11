-- Migration: Add due_date to market notes and update status options
-- Description: Add due_date column and change 'on_hold' to 'stalled'

-- Add due_date column
ALTER TABLE market_note_completions
ADD COLUMN IF NOT EXISTS due_date DATE;

-- Update status constraint to include 'stalled' and remove 'on_hold'
-- First drop the old constraint, then add new one
ALTER TABLE market_note_completions DROP CONSTRAINT IF EXISTS market_note_completions_status_check;
ALTER TABLE market_note_completions ADD CONSTRAINT market_note_completions_status_check
    CHECK (status IN ('new', 'in_progress', 'completed', 'stalled'));

-- Update any existing 'on_hold' to 'stalled'
UPDATE market_note_completions SET status = 'stalled' WHERE status = 'on_hold';

-- Index for due_date
CREATE INDEX IF NOT EXISTS idx_market_note_completions_due_date ON market_note_completions(due_date);
