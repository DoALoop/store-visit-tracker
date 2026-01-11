-- Migration: Add visit_photos table for storing photo attachments
-- Description: Store photo metadata with GCS URLs for store visit photos

CREATE TABLE IF NOT EXISTS visit_photos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    visit_id INTEGER NOT NULL REFERENCES store_visits(id) ON DELETE CASCADE,
    gcs_url TEXT NOT NULL,
    filename VARCHAR(255) NOT NULL,
    content_type VARCHAR(100) DEFAULT 'image/jpeg',
    file_size INTEGER,
    caption TEXT,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for efficient lookup by visit
CREATE INDEX IF NOT EXISTS idx_visit_photos_visit_id ON visit_photos(visit_id);

-- Index for chronological ordering
CREATE INDEX IF NOT EXISTS idx_visit_photos_uploaded_at ON visit_photos(uploaded_at);
