-- Migration: Add status and assigned_to to note_tasks
-- Description: Add status workflow and assignee tracking for tasks

-- Add status column with constraint
ALTER TABLE note_tasks
ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'new';

ALTER TABLE note_tasks DROP CONSTRAINT IF EXISTS note_tasks_status_check;
ALTER TABLE note_tasks ADD CONSTRAINT note_tasks_status_check
    CHECK (status IN ('new', 'in_progress', 'stalled', 'completed'));

-- Add assigned_to column
ALTER TABLE note_tasks
ADD COLUMN IF NOT EXISTS assigned_to VARCHAR(200);

-- Index for status filtering
CREATE INDEX IF NOT EXISTS idx_note_tasks_status ON note_tasks(status);

-- Index for assigned_to filtering
CREATE INDEX IF NOT EXISTS idx_note_tasks_assigned_to ON note_tasks(assigned_to) WHERE assigned_to IS NOT NULL;

-- Update existing completed tasks to have 'completed' status
UPDATE note_tasks SET status = 'completed' WHERE is_completed = TRUE AND status = 'new';
