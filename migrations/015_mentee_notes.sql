-- Migration: Add notes column to mentees
-- Description: Add a text field for miscellaneous notes for each mentee

ALTER TABLE mentees ADD COLUMN IF NOT EXISTS notes TEXT;
