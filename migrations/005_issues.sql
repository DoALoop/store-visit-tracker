-- Migration: Issues/Feedback
-- Description: Create table for tracking feature requests, bugs, and feedback

CREATE TABLE IF NOT EXISTS issues (
    id SERIAL PRIMARY KEY,
    type VARCHAR(20) NOT NULL CHECK (type IN ('feature', 'bug', 'feedback')),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'new' CHECK (status IN ('new', 'in_progress', 'completed')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_issues_status ON issues(status);
CREATE INDEX IF NOT EXISTS idx_issues_type ON issues(type);
CREATE INDEX IF NOT EXISTS idx_issues_created ON issues(created_at DESC);

-- Grant permissions to store_tracker user
GRANT SELECT, INSERT, UPDATE, DELETE ON issues TO store_tracker;
GRANT USAGE, SELECT ON SEQUENCE issues_id_seq TO store_tracker;
