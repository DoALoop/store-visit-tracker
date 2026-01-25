-- Migration: Create standalone tasks table
-- Description: Separate tasks system for Smart Add, independent from notes

CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'new' CHECK (status IN ('new', 'in_progress', 'stalled', 'completed')),
    priority INTEGER DEFAULT 0 CHECK (priority BETWEEN 0 AND 3),
    assigned_to VARCHAR(200),
    due_date DATE,
    store_number VARCHAR(10),
    list_name VARCHAR(100) DEFAULT 'Inbox',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date) WHERE status != 'completed';
CREATE INDEX IF NOT EXISTS idx_tasks_assigned_to ON tasks(assigned_to) WHERE assigned_to IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_tasks_store_number ON tasks(store_number) WHERE store_number IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_tasks_list_name ON tasks(list_name);
CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority) WHERE priority > 0;

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_tasks_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    
    -- Auto-set completed_at when status changes to completed
    IF NEW.status = 'completed' AND OLD.status != 'completed' THEN
        NEW.completed_at = CURRENT_TIMESTAMP;
    END IF;
    
    -- Clear completed_at if status changes from completed
    IF NEW.status != 'completed' AND OLD.status = 'completed' THEN
        NEW.completed_at = NULL;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tasks_updated_at_trigger ON tasks;
CREATE TRIGGER tasks_updated_at_trigger
BEFORE UPDATE ON tasks
FOR EACH ROW
EXECUTE FUNCTION update_tasks_updated_at();
