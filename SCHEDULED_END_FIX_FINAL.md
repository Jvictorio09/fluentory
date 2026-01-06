# Final Fix for scheduled_end IntegrityError

## Problem
PostgreSQL was rejecting INSERT statements because the `scheduled_end` column has a NOT NULL constraint, but the value wasn't being set before the INSERT operation.

## Root Cause
The `scheduled_end` field exists as a database column with NOT NULL constraint, but:
1. The view was computing `scheduled_end_naive` but there might have been edge cases where it wasn't set
2. The model's `save()` method had logic to compute it, but PostgreSQL rejects the INSERT BEFORE any save logic can run if a NOT NULL column is missing

## Solution

### 1. Model Field Definition (myApp/models.py)
- `scheduled_end` is defined as a `DateTimeField` (required, no `null=True`)
- This ensures Django knows about the field and includes it in INSERT statements

### 2. View Logic (myApp/views.py)
- **Explicitly computes** `scheduled_end_naive = scheduled_start_naive + timedelta(minutes=duration_minutes)`
- **Validates** that `scheduled_end_naive` is not None before creating
- **Double-checks** computation by recomputing if values don't match
- **Passes** `scheduled_end=scheduled_end_naive` to `LiveClassSession.objects.create()`

### 3. Model Save Method (myApp/models.py)
- **Safety net**: Computes `scheduled_end` if it's None before calling `super().save()`
- Uses multiple fallback strategies:
  1. Compute from `scheduled_start + duration_minutes`
  2. Use `end_at_utc` converted to naive datetime
  3. Final fallback: recompute from `scheduled_start + duration_minutes`

## Changes Made

### myApp/views.py - teacher_schedule view:
```python
# Compute end time: start + duration
scheduled_end_utc = scheduled_start_utc + timedelta(minutes=duration_minutes)

# Convert to naive datetime for scheduled_start/scheduled_end
scheduled_start_naive = scheduled_start_utc.replace(tzinfo=None) if scheduled_start_utc.tzinfo else scheduled_start_utc
scheduled_end_naive = scheduled_end_utc.replace(tzinfo=None) if scheduled_end_utc.tzinfo else scheduled_end_utc

# VALIDATION: Ensure scheduled_end_naive is computed correctly
if scheduled_end_naive is None:
    messages.error(request, 'Failed to compute session end time. Please try again.')
    return redirect('teacher_schedule')

# Double-check: recompute if needed
if scheduled_start_naive and duration_minutes:
    expected_end = scheduled_start_naive + timedelta(minutes=duration_minutes)
    if abs((scheduled_end_naive - expected_end).total_seconds()) > 1:
        scheduled_end_naive = expected_end

# Create with scheduled_end explicitly set
live_class = LiveClassSession.objects.create(
    ...
    scheduled_end=scheduled_end_naive,  # REQUIRED: Set before INSERT
    ...
)
```

### myApp/models.py - LiveClassSession.save():
```python
def save(self, *args, **kwargs):
    # CRITICAL: Compute scheduled_end BEFORE save to avoid IntegrityError
    if self.scheduled_start and self.duration_minutes:
        current_scheduled_end = getattr(self, 'scheduled_end', None)
        if current_scheduled_end is None:
            self.scheduled_end = self.scheduled_start + timedelta(minutes=self.duration_minutes)
    
    # ... other logic ...
    
    # FINAL CHECK: Ensure scheduled_end is set (safety net)
    if getattr(self, 'scheduled_end', None) is None:
        if self.end_at_utc:
            self.scheduled_end = self.end_at_utc.replace(tzinfo=None) if ... else self.end_at_utc
        elif self.scheduled_start and self.duration_minutes:
            self.scheduled_end = self.scheduled_start + timedelta(minutes=self.duration_minutes)
    
    super().save(*args, **kwargs)
```

## Testing

1. **Restart the Django development server** to ensure latest code is loaded
2. Navigate to `/teacher/schedule/`
3. Fill out the form:
   - Select a course
   - Enter title
   - Set scheduled start time
   - Set duration (minutes)
   - Set total seats
4. Submit the form
5. **Expected Result**: 
   - ✅ Session is created successfully
   - ✅ No IntegrityError
   - ✅ Session appears in live classes list
   - ✅ `scheduled_end` is correctly set in database

## Key Points

1. **Field must be set BEFORE INSERT**: The view explicitly sets `scheduled_end` in the `create()` call
2. **Model has safety net**: The `save()` method ensures `scheduled_end` is computed if somehow missing
3. **Validation added**: View validates that `scheduled_end_naive` is not None before creating
4. **Multiple fallbacks**: If one computation method fails, others will catch it

## Verification

After applying this fix:
- The INSERT statement will include `scheduled_end` in the VALUES clause
- PostgreSQL will accept the INSERT because all NOT NULL columns have values
- The session will be saved successfully

