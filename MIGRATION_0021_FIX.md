# Fix for Migration 0021 - DuplicateColumn Error

## Problem
Error: `DuplicateColumn: column "current_attendees" of relation "myApp_liveclasssession" already exists`

The migration was trying to create or modify the `current_attendees` column, but it already exists in the database as a legacy column.

## Root Cause
- The database already has `current_attendees` column (legacy)
- Using `AlterField` with `db_column` can cause Django to try to rename/create columns
- Migration needed to be idempotent and only update Django's state, not modify database schema

## Solution

### Updated Migration 0021

The migration now uses `SeparateDatabaseAndState` to:
1. **Database operations only**: Backfill NULL values and set defaults (no column creation)
2. **State-only update**: Tell Django that `seats_taken` maps to `current_attendees` without modifying the database

### Migration Operations

1. **RunPython**: 
   - Backfills NULL values: `UPDATE ... SET current_attendees = 0 WHERE current_attendees IS NULL`
   - Sets database-level default: `ALTER COLUMN current_attendees SET DEFAULT 0`
   - Ensures NOT NULL constraint: `ALTER COLUMN current_attendees SET NOT NULL`
   - All operations are idempotent (safe to run multiple times)

2. **SeparateDatabaseAndState**:
   - **State operations**: Updates Django's model state to know `seats_taken` maps to `current_attendees`
   - **Database operations**: Empty - no schema changes (column already exists)

## Key Changes

### Before (Problematic):
```python
operations = [
    migrations.RunPython(...),
    migrations.AlterField(...),  # This can try to create/rename columns
]
```

### After (Fixed):
```python
operations = [
    migrations.RunPython(...),  # Only data operations
    migrations.SeparateDatabaseAndState(
        state_operations=[...],  # Only updates Django state
        database_operations=[],  # No DB schema changes
    ),
]
```

## Applying the Fix

### If migration 0021 was NOT yet applied:
1. The fixed migration should apply cleanly:
   ```bash
   python manage.py migrate myApp 0021
   ```

### If migration 0021 was partially applied or marked as applied:
1. If it failed partway through, you may need to:
   ```bash
   # Check migration status
   python manage.py showmigrations myApp
   
   # If 0021 shows as applied but schema isn't correct, you can:
   # Option A: Fake unapply and reapply
   python manage.py migrate myApp 0020
   python manage.py migrate myApp 0021 --fake
   python manage.py migrate myApp 0021
   
   # Option B: If 0021 is not applied, just run it
   python manage.py migrate myApp 0021
   ```

2. If 0021 was already recorded as applied in `django_migrations` table but failed:
   - Manually backfill data: `UPDATE myapp_liveclasssession SET current_attendees = 0 WHERE current_attendees IS NULL;`
   - Set default: `ALTER TABLE myapp_liveclasssession ALTER COLUMN current_attendees SET DEFAULT 0;`
   - Migration state is already updated, so Django knows about the mapping

## Verification

After applying the migration:

1. **Check migration status**:
   ```bash
   python manage.py showmigrations myApp
   ```
   Should show `0021_fix_current_attendees_column` as applied.

2. **Verify database**:
   - Column `current_attendees` exists
   - No NULL values in `current_attendees`
   - Default value is 0

3. **Test session creation**:
   - Navigate to `/teacher/schedule/`
   - Create a new session
   - Verify it saves successfully
   - Check database: `current_attendees` should be 0 for new session

## Expected Result

✅ Migration runs without `DuplicateColumn` error
✅ NULL values are backfilled to 0
✅ Database default is set to 0
✅ Django knows `seats_taken` maps to `current_attendees`
✅ New sessions initialize `current_attendees` to 0
✅ No database schema changes (column already existed)

