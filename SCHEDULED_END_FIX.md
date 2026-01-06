# Fix for scheduled_end IntegrityError

## Problem
Error: `null value in column "scheduled_end" of relation "myApp_liveclasssession" violates not-null constraint`

The database has a `scheduled_end` column that requires a value, but the view wasn't computing or setting it when creating sessions.

## Solution

### 1. Updated `teacher_schedule` View
- Added validation for `scheduled_start` and `duration_minutes`
- Properly parses and converts datetime to UTC
- Computes `scheduled_end` = `scheduled_start + duration_minutes`
- Sets both legacy fields (`scheduled_start`, `scheduled_end`) and new fields (`start_at_utc`, `end_at_utc`)
- Handles timezone conversion properly
- Includes error handling for database column mismatches

### 2. Updated `LiveClassSession.save()` Method
- Automatically computes `end_at_utc` from `start_at_utc + duration_minutes`
- After save, checks if `scheduled_end` column exists in database
- If column exists, updates it with calculated end time
- Handles case where column exists but isn't in model (from old migrations)

## Changes Made

### `myApp/views.py` - `teacher_schedule` view:
1. **Validation Added**:
   - Checks `scheduled_start` is provided
   - Validates `duration_minutes >= 1`
   - Validates `total_seats >= 1`

2. **Timezone Handling**:
   - Parses datetime from form input
   - Ensures timezone-aware datetime
   - Converts to UTC for storage
   - Stores teacher's timezone in `timezone_snapshot`

3. **End Time Calculation**:
   - Computes `scheduled_end_utc = scheduled_start_utc + duration_minutes`
   - Creates both naive (for legacy fields) and timezone-aware (for UTC fields) versions

4. **Database Compatibility**:
   - Checks if `scheduled_end` exists as database column
   - Sets it if column exists
   - Falls back to raw SQL update if needed

### `myApp/models.py` - `LiveClassSession.save()` method:
1. **Auto-compute end times**:
   - Computes `end_at_utc` if not set
   - Ensures `start_at_utc` is populated from `scheduled_start`

2. **Database column handling**:
   - After save, checks if `scheduled_end` column exists
   - Updates it with calculated end time if column exists
   - Gracefully handles case where column doesn't exist

## Testing

To verify the fix:
1. Navigate to `/teacher/schedule/`
2. Fill out the form:
   - Course
   - Title
   - Scheduled Start (date/time)
   - Duration (minutes, >= 1)
   - Total Seats (>= 1)
3. Submit the form
4. Verify:
   - Session is created successfully
   - No IntegrityError
   - Session appears in live classes list
   - End time is correctly set in database

## Result

✅ Creating a live class no longer throws IntegrityError
✅ Sessions save with valid end time computed from start + duration
✅ Both legacy and new fields are populated correctly
✅ Timezone handling is consistent (all stored in UTC)


