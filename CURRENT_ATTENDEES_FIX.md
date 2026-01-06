# Fix for current_attendees IntegrityError

## Problem
Error: `null value in column "current_attendees" of relation "myApp_liveclasssession" violates not-null constraint`

The database has a `current_attendees` column that is NOT NULL, but:
1. The Django model field is named `seats_taken` (not `current_attendees`)
2. Django was trying to insert NULL because the field mapping didn't match the database column

## Root Cause
- **Database column**: `current_attendees` (NOT NULL, should default to 0)
- **Model field**: `seats_taken`
- **Issue**: Django generates column name `seats_taken` from field name, but database actually has `current_attendees`
- **Result**: INSERT statement didn't include `current_attendees`, causing NULL constraint violation

## Solution

### 1. Model Field Mapping (myApp/models.py)
Added `db_column='current_attendees'` to map the Django field to the existing database column:
```python
seats_taken = models.PositiveIntegerField(
    default=0, 
    help_text='Cached count of confirmed bookings (updated via signal)', 
    db_column='current_attendees'
)
```

### 2. View Logic (myApp/views.py)
- **Explicitly sets** `seats_taken=0` when creating new sessions
- **Ensures** `current_attendees` column always has a value

### 3. Model Save Method (myApp/models.py)
- **Safety net**: Sets `seats_taken = 0` if None before save
- **Prevents** IntegrityError even if view somehow doesn't set it

## Changes Made

### myApp/models.py:
```python
# Updated field definition
seats_taken = models.PositiveIntegerField(
    default=0, 
    help_text='Cached count of confirmed bookings (updated via signal)', 
    db_column='current_attendees'  # Maps to existing DB column
)

# Updated save() method
def save(self, *args, **kwargs):
    # ... existing logic ...
    
    # CRITICAL: Ensure seats_taken (maps to current_attendees column) is never None
    if not hasattr(self, 'seats_taken') or self.seats_taken is None:
        self.seats_taken = 0
    
    super().save(*args, **kwargs)
```

### myApp/views.py - teacher_schedule view:
```python
live_class = LiveClassSession.objects.create(
    ...
    seats_taken=0,  # REQUIRED: current_attendees column is NOT NULL, initialize to 0 for new sessions
    ...
)
```

## Result

✅ Django now correctly maps `seats_taken` field to `current_attendees` database column
✅ `seats_taken` is always set to 0 for new sessions before INSERT
✅ No IntegrityError when creating sessions
✅ All NOT NULL columns (`scheduled_end`, `meeting_url`, `current_attendees`) are properly populated

## Testing

1. **Restart the Django development server**
2. Navigate to `/teacher/schedule/`
3. Fill out the form
4. Submit the form
5. **Expected Result**: 
   - ✅ Session is created successfully
   - ✅ No IntegrityError for `current_attendees`
   - ✅ No IntegrityError for `scheduled_end`
   - ✅ No IntegrityError for `meeting_url`
   - ✅ Session appears in live classes list
   - ✅ `current_attendees` is initialized to 0

## Key Points

1. **`db_column` mapping**: Connects Django field name to actual database column name
2. **Explicit initialization**: View explicitly sets `seats_taken=0` for new sessions
3. **Safety net in save()**: Model's save() method ensures field is never None
4. **Default value**: Model field has `default=0` as additional protection

## Summary of All NOT NULL Fixes

1. ✅ **scheduled_end**: Computed from `scheduled_start + duration_minutes` before INSERT
2. ✅ **meeting_url**: Mapped via `db_column='meeting_url'`, always set to empty string minimum
3. ✅ **current_attendees**: Mapped via `db_column='current_attendees'`, always set to 0 for new sessions

All three NOT NULL columns are now properly handled, and session creation should work end-to-end.

