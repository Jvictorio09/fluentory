# Complete Fix for current_attendees IntegrityError

## Problem
Error: `null value in column "current_attendees" of relation "myApp_liveclasssession" violates not-null constraint`

The database has a `current_attendees` column that is NOT NULL, but the Django model was using a different column name (`seats_taken`), causing INSERT statements to omit the value.

## Solution Applied

### 1. Model Field Mapping (myApp/models.py)
✅ Added `db_column='current_attendees'` to map `seats_taken` field to the database column:
```python
seats_taken = models.PositiveIntegerField(
    default=0, 
    help_text='Cached count of confirmed bookings (updated via signal)', 
    db_column='current_attendees'
)
```

### 2. View Logic (myApp/views.py)
✅ Explicitly sets `seats_taken=0` when creating new sessions:
```python
live_class = LiveClassSession.objects.create(
    ...
    seats_taken=0,  # REQUIRED: current_attendees column is NOT NULL
    ...
)
```

### 3. Model Save Method (myApp/models.py)
✅ Safety net that ensures `seats_taken` is never None:
```python
def save(self, *args, **kwargs):
    # ... existing logic ...
    
    # CRITICAL: Ensure seats_taken (maps to current_attendees column) is never None
    if not hasattr(self, 'seats_taken') or self.seats_taken is None:
        self.seats_taken = 0
    
    super().save(*args, **kwargs)
```

### 4. Database Migration (myApp/migrations/0021_fix_current_attendees_column.py)
✅ Created migration to:
- Update any existing NULL values to 0
- Add database-level default value of 0
- Update Django's state to recognize `db_column='current_attendees'` mapping

## Steps to Apply the Fix

1. **Apply the migration**:
   ```bash
   python manage.py migrate myApp 0021
   ```

2. **Restart the Django development server** to load the updated model code

3. **Test creating a session** at `/teacher/schedule/`

## Expected Result

✅ Django correctly maps `seats_taken` field to `current_attendees` database column
✅ `seats_taken` is always set to 0 for new sessions before INSERT
✅ Database column has default value of 0 at database level
✅ No IntegrityError when creating sessions
✅ All NOT NULL columns are properly populated:
   - `scheduled_end`: Computed from `scheduled_start + duration_minutes`
   - `meeting_url`: Always set (empty string minimum)
   - `current_attendees`: Always set to 0 for new sessions

## Verification

After applying the migration and restarting the server:

1. Navigate to `/teacher/schedule/`
2. Fill out the form:
   - Course
   - Title
   - Scheduled Start
   - Duration
   - Total Seats
   - (Meeting link optional)
3. Submit the form
4. **Expected**: Session is created successfully with no errors
5. **Verify**: Check database to confirm `current_attendees = 0` for the new session

## Summary of All NOT NULL Column Fixes

| Column | Model Field | Solution | Status |
|--------|-------------|----------|--------|
| `scheduled_end` | `scheduled_end` | Computed from `scheduled_start + duration_minutes` | ✅ Fixed |
| `meeting_url` | `meeting_link` | `db_column='meeting_url'`, default empty string | ✅ Fixed |
| `current_attendees` | `seats_taken` | `db_column='current_attendees'`, default=0 | ✅ Fixed |

All three NOT NULL columns are now properly handled with:
- Correct field-to-column mapping
- Explicit values set in view
- Safety nets in model save() method
- Database-level defaults where applicable

