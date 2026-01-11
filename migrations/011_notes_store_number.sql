-- Migration: Add store_number to notes and note_tasks
-- Description: Allow notes and tasks to be associated with specific stores

-- Add store_number to notes table
ALTER TABLE notes
ADD COLUMN IF NOT EXISTS store_number VARCHAR(10);

-- Add store_number to note_tasks table
ALTER TABLE note_tasks
ADD COLUMN IF NOT EXISTS store_number VARCHAR(10);

-- Index for filtering notes by store
CREATE INDEX IF NOT EXISTS idx_notes_store_number ON notes(store_number) WHERE store_number IS NOT NULL;

-- Index for filtering tasks by store
CREATE INDEX IF NOT EXISTS idx_note_tasks_store_number ON note_tasks(store_number) WHERE store_number IS NOT NULL;
