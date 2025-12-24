# Database Migration Guide: Notes Normalization (v1.0 → v2.0)

## Overview

This guide walks you through migrating from the old denormalized note structure to the new normalized structure.

### What Changed?

**BEFORE (v1.0 - Denormalized):**
```
store_visits TABLE:
├── store_notes TEXT  → "Note 1\nNote 2\nNote 3" (single field!)
├── mkt_notes TEXT    → "Mkt 1\nMkt 2" (single field!)
├── good TEXT         → "Good 1\nGood 2" (single field!)
└── top_3 TEXT        → "Top 1\nTop 2\nTop 3" (single field!)
```

**AFTER (v2.0 - Normalized):**
```
store_visits TABLE:
├── id (PK)
├── storeNbr
├── calendar_date
├── rating
├── [17 metric columns]
└── [DEPRECATED: store_notes, mkt_notes, good, top_3]

store_visit_notes TABLE:        (NEW)
├── id (PK)
├── visit_id (FK)
├── note_text
└── sequence

store_market_notes TABLE:       (NEW)
├── id (PK)
├── visit_id (FK)
├── note_text
└── sequence

store_good_notes TABLE:         (NEW)
├── id (PK)
├── visit_id (FK)
├── note_text
└── sequence

store_improvement_notes TABLE:  (NEW)
├── id (PK)
├── visit_id (FK)
├── note_text
└── sequence
```

## Why Normalize?

✅ **Queryable:** Can find visits with specific notes  
✅ **Updateable:** Can modify/delete individual notes  
✅ **Scalable:** Proper database design (3NF)  
✅ **Searchable:** Full-text search on note content  
✅ **Flexible:** Easy to add metadata (edited_by, edit_timestamp, etc.)  

## Migration Steps

### Step 1: Backup Your Database (CRITICAL!)

```bash
# Create a backup of your database
pg_dump -U <username> -d <database_name> > backup_$(date +%Y%m%d_%H%M%S).sql

# Example:
pg_dump -U storeapp -d store_visit_tracker > backup_20251218.sql

# Verify backup was created
ls -lh backup_20251218.sql
```

**IMPORTANT:** Keep this backup safe until you've verified the migration worked!

### Step 2: Run the Migration Script

Connect to your database and run the migration:

```bash
# Using psql command line:
psql -U <username> -d <database_name> -f migrations/001_normalize_notes.sql

# Example:
psql -U storeapp -d store_visit_tracker -f migrations/001_normalize_notes.sql
```

You should see output like:
```
NOTICE:  Migrated store_notes: 45 rows
NOTICE:  Migrated mkt_notes: 38 rows
NOTICE:  Migrated good notes: 42 rows
NOTICE:  Migrated top_3 notes: 45 rows
NOTICE:  Data migration completed successfully!
=== Migration Verification ===
NOTICE:  store_visit_notes: 45 rows
NOTICE:  store_market_notes: 38 rows
NOTICE:  store_good_notes: 42 rows
NOTICE:  store_improvement_notes: 45 rows
```

### Step 3: Verify the Migration

Query the new tables to confirm data was migrated:

```sql
-- Check counts
SELECT COUNT(*) as visit_notes FROM store_visit_notes;
SELECT COUNT(*) as market_notes FROM store_market_notes;
SELECT COUNT(*) as good_notes FROM store_good_notes;
SELECT COUNT(*) as improvement_notes FROM store_improvement_notes;

-- Sample data
SELECT * FROM store_visit_notes LIMIT 5;
SELECT * FROM store_good_notes LIMIT 5;

-- Verify no orphaned notes (all visit_ids exist)
SELECT COUNT(*) FROM store_visit_notes svn 
WHERE NOT EXISTS (SELECT 1 FROM store_visits sv WHERE sv.id = svn.visit_id);
-- Should return 0 if all data is clean
```

### Step 4: Update Your Code

After the migration, you need to update:

1. **Backend (main.py):**
   - `/api/save-visit` endpoint to write to new tables
   - `/api/get-visits` endpoint to read from new tables
   - `/api/visit/<id>` endpoint to read from new tables

2. **Frontend (index.html):**
   - Update note parsing/display to handle array responses
   - Update modal display to handle normalized structure

### Step 5: Deploy and Test

1. Update `main.py` with the new save/read logic
2. Test locally:
   ```bash
   python main.py
   # Try creating a new visit
   # Try viewing visits
   # Verify notes display correctly
   ```
3. Deploy to production
4. Monitor logs for errors

### Step 6: Cleanup (Optional - After Confirming Everything Works)

Once you've confirmed the new code is working with the migrated data, you can optionally drop the old columns:

```sql
-- CAUTION: Only do this after confirming new code is working!
ALTER TABLE store_visits DROP COLUMN store_notes;
ALTER TABLE store_visits DROP COLUMN mkt_notes;
ALTER TABLE store_visits DROP COLUMN good;
ALTER TABLE store_visits DROP COLUMN top_3;
```

**WARNING:** Only drop these after:
- ✅ Updating all code to use new tables
- ✅ Verifying data migrated correctly
- ✅ Testing new code thoroughly
- ✅ Having a backup you can restore from

## Backward Compatibility

For the transition period:
- ✅ Old columns are kept in `store_visits`
- ✅ Old and new code can coexist
- ✅ You can gradually migrate features
- ✅ Easy to rollback if needed

BUT: The migration script only runs once (uses `CREATE TABLE IF NOT EXISTS`). Once new tables exist, you must use them for new data.

## Troubleshooting

### Issue: Migration fails with "permission denied"

**Solution:** Make sure your user has permissions to create tables:
```sql
GRANT CREATE ON DATABASE store_visit_tracker TO storeapp;
GRANT USAGE, CREATE ON SCHEMA public TO storeapp;
```

### Issue: Some notes are missing after migration

**Cause:** Notes with only whitespace get filtered out (by design).  
**Check:**
```sql
-- Find empty notes in old columns
SELECT id, store_notes FROM store_visits 
WHERE store_notes IS NOT NULL AND TRIM(store_notes) = '';
```

### Issue: Notes are in wrong order

**Cause:** Sequence numbers may not match original order for complex note structures.  
**Fix:** The migration preserves order using SQL ROW_NUMBER() - if you see issues, check the sequence values:
```sql
SELECT visit_id, sequence, note_text FROM store_visit_notes ORDER BY visit_id, sequence;
```

### Issue: Duplicate visit_ids or referential integrity errors

**Cause:** Data corruption or store_visits table was modified during migration.  
**Recovery:** Restore from backup and try again:
```bash
psql -U storeapp -d store_visit_tracker < backup_20251218.sql
```

## Performance Considerations

### Before (v1.0)
- ✗ Slow text parsing on every read
- ✗ Can't index note content
- ✗ TEXT fields can be large

### After (v2.0)
- ✅ Indexed lookups
- ✅ Full-text search support (GIN indexes)
- ✅ Better query planning
- ✅ Smaller average field size

### Expected Performance

```sql
-- Fast: Get all notes for a visit (indexed)
SELECT * FROM store_visit_notes WHERE visit_id = 123;
-- Index: idx_visit_notes_visit_id ✅

-- Fast: Full-text search across notes
SELECT * FROM store_visit_notes 
WHERE to_tsvector('english', note_text) @@ plainto_tsquery('english', 'customer');
-- Index: idx_visit_notes_text ✅

-- Fast: Join to get complete visit
SELECT sv.*, svn.note_text 
FROM store_visits sv
LEFT JOIN store_visit_notes svn ON sv.id = svn.visit_id
WHERE sv.id = 123;
-- Indexes: PRIMARY KEY, idx_visit_notes_visit_id ✅
```

## Rollback Plan

If something goes wrong:

1. **Stop the application**
2. **Restore the backup:**
   ```bash
   psql -U storeapp -d store_visit_tracker < backup_20251218.sql
   ```
3. **Verify data is restored:**
   ```sql
   SELECT COUNT(*) FROM store_visits;
   ```
4. **Restart application with old code**
5. **Investigate what went wrong**

## Timeline

Recommended migration timeline:

1. **Day 1:** Create backup, run migration script, verify
2. **Day 2-3:** Test new code locally, fix any issues
3. **Day 4:** Deploy new code to production
4. **Day 5-7:** Monitor for issues, confirm everything works
5. **Week 2:** Optional - drop old columns (after confirming)

## Files Modified

Migration-related files:
- ✅ `migrations/001_normalize_notes.sql` - The migration script
- ✅ `schema.sql` - Updated with new tables
- ✅ `MIGRATION_GUIDE.md` - This file
- 📝 `main.py` - Will be updated next (not yet)
- 📝 `index.html` - Will be updated next (not yet)

## Questions?

Refer to:
- API documentation: `API_ENDPOINTS.md`
- Backend code: `main.py`
- Frontend code: `index.html`
- Database schema: `schema.sql`

---

**Database Schema Version:** 2.0 (Normalized)  
**Migration File:** 001_normalize_notes.sql  
**Last Updated:** 2025-12-18  
**Status:** Ready for migration
