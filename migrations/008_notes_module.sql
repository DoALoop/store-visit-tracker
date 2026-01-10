-- Migration 008: Notes Module
-- Adds tables for Obsidian-style notes with wikilinks, tags, and tasks

-- Notes table
CREATE TABLE IF NOT EXISTS notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    content TEXT,
    folder_path VARCHAR(500) DEFAULT '/',
    is_pinned BOOLEAN DEFAULT FALSE,
    is_daily_note BOOLEAN DEFAULT FALSE,
    daily_date DATE,
    linked_visit_id INTEGER REFERENCES store_visits(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP  -- soft delete for sync
);

-- Indexes for notes table
CREATE INDEX IF NOT EXISTS notes_folder_path_idx ON notes(folder_path);
CREATE INDEX IF NOT EXISTS notes_daily_date_idx ON notes(daily_date) WHERE is_daily_note = TRUE;
CREATE INDEX IF NOT EXISTS notes_linked_visit_idx ON notes(linked_visit_id) WHERE linked_visit_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS notes_deleted_at_idx ON notes(deleted_at) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS notes_updated_at_idx ON notes(updated_at);

-- Full-text search index
CREATE INDEX IF NOT EXISTS notes_fts_idx ON notes
    USING gin(to_tsvector('english', coalesce(title,'') || ' ' || coalesce(content,'')));

-- Note links (wikilinks between notes)
CREATE TABLE IF NOT EXISTS note_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_note_id UUID REFERENCES notes(id) ON DELETE CASCADE,
    target_note_id UUID REFERENCES notes(id) ON DELETE CASCADE,
    target_title VARCHAR(500) NOT NULL,  -- store title for unresolved links
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_note_id, target_note_id)
);

CREATE INDEX IF NOT EXISTS note_links_source_idx ON note_links(source_note_id);
CREATE INDEX IF NOT EXISTS note_links_target_idx ON note_links(target_note_id);
CREATE INDEX IF NOT EXISTS note_links_target_title_idx ON note_links(target_title);

-- Tags
CREATE TABLE IF NOT EXISTS note_tags (
    note_id UUID REFERENCES notes(id) ON DELETE CASCADE,
    tag VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (note_id, tag)
);

CREATE INDEX IF NOT EXISTS note_tags_tag_idx ON note_tags(tag);

-- Tasks extracted from notes
CREATE TABLE IF NOT EXISTS note_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    note_id UUID REFERENCES notes(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    is_completed BOOLEAN DEFAULT FALSE,
    due_date DATE,
    priority INTEGER DEFAULT 0,  -- 0=none, 1=low, 2=medium, 3=high
    line_number INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS note_tasks_note_idx ON note_tasks(note_id);
CREATE INDEX IF NOT EXISTS note_tasks_due_idx ON note_tasks(due_date) WHERE NOT is_completed;
CREATE INDEX IF NOT EXISTS note_tasks_completed_idx ON note_tasks(is_completed);
CREATE INDEX IF NOT EXISTS note_tasks_priority_idx ON note_tasks(priority) WHERE priority > 0;

-- Templates
CREATE TABLE IF NOT EXISTS note_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    content TEXT,
    is_daily_template BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Folders (for folder metadata, actual structure is in folder_path)
CREATE TABLE IF NOT EXISTS note_folders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    path VARCHAR(500) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    parent_path VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS note_folders_parent_idx ON note_folders(parent_path);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_notes_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at
DROP TRIGGER IF EXISTS notes_updated_at_trigger ON notes;
CREATE TRIGGER notes_updated_at_trigger
    BEFORE UPDATE ON notes
    FOR EACH ROW
    EXECUTE FUNCTION update_notes_updated_at();

DROP TRIGGER IF EXISTS note_tasks_updated_at_trigger ON note_tasks;
CREATE TRIGGER note_tasks_updated_at_trigger
    BEFORE UPDATE ON note_tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_notes_updated_at();

DROP TRIGGER IF EXISTS note_templates_updated_at_trigger ON note_templates;
CREATE TRIGGER note_templates_updated_at_trigger
    BEFORE UPDATE ON note_templates
    FOR EACH ROW
    EXECUTE FUNCTION update_notes_updated_at();
