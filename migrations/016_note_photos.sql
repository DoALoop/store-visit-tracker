-- Migration: Create note_photos table
-- Description: Allow attaching photos to notes (similar to visit_photos)

CREATE TABLE IF NOT EXISTS note_photos (
    id VARCHAR(36) PRIMARY KEY,
    note_id VARCHAR(36) NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    gcs_url TEXT NOT NULL,
    filename VARCHAR(255),
    content_type VARCHAR(100),
    file_size INTEGER,
    caption TEXT,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_note_photos_note_id ON note_photos(note_id);

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON note_photos TO store_tracker;
