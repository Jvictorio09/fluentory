# Fix for meeting_url IntegrityError

## Problem
Error: `null value in column "meeting_url" of relation "myApp_liveclasssession" violates not-null constraint`

The database has a `meeting_url` column that is NOT NULL, but:
1. The Django model field is named `meeting_link` (not `meeting_url`)
2. Django was trying to insert NULL because the field mapping didn't match the database column

## Root Cause
- **Database column**: `meeting_url` (NOT NULL)
- **Model field**: `meeting_link`
- **Issue**: Django generates column name `meeting_link` from field name, but database actually has `meeting_url`
- **Result**: INSERT statement didn't include `meeting_url`, causing NULL constraint violation

## Solution

### 1. Model Field Mapping (myApp/models.py)
Added `db_column='meeting_url'` to map the Django field to the existing database column:
```python
meeting_link = models.URLField(
    blank=True, 
    help_text='Zoom / Google Meet / Custom meeting link', 
    db_column='meeting_url', 
    default=''
)
```

### 2. View Logic (myApp/views.py)
- **Ensures** `meeting_link` is always set (empty string if not provided)
- **Strips** whitespace from form input
- **Checks** multiple form fields (`meeting_link`, `zoom_link`, `google_meet_link`)
- **Explicitly sets** `meeting_link` in `create()` call

### 3. Model Save Method (myApp/models.py)
- **Safety net**: Sets `meeting_link = ''` if None before save
- **Prevents** IntegrityError even if view somehow doesn't set it

## Changes Made

### myApp/models.py:
```python
# Updated field definition
meeting_link = models.URLField(
    blank=True, 
    help_text='Zoom / Google Meet / Custom meeting link', 
    db_column='meeting_url',  # Maps to existing DB column
    default=''  # Default empty string for NOT NULL constraint
)

# Updated save() method
def save(self, *args, **kwargs):
    # ... existing logic ...
    
    # CRITICAL: Ensure meeting_link (maps to meeting_url column) is never None
    if not hasattr(self, 'meeting_link') or self.meeting_link is None:
        self.meeting_link = ''
    
    super().save(*args, **kwargs)
```

### myApp/views.py - teacher_schedule view:
```python
# CRITICAL: meeting_url column in DB is NOT NULL, so always provide a value
meeting_link = (
    request.POST.get('meeting_link', '').strip() or 
    request.POST.get('zoom_link', '').strip() or 
    request.POST.get('google_meet_link', '').strip() or 
    ''
)

live_class = LiveClassSession.objects.create(
    ...
    meeting_link=meeting_link,  # REQUIRED: meeting_url column is NOT NULL
    ...
)
```

## Result

✅ Django now correctly maps `meeting_link` field to `meeting_url` database column
✅ `meeting_link` is always set (empty string minimum) before INSERT
✅ No IntegrityError when creating sessions
✅ Both `scheduled_end` and `meeting_url` are properly populated

## Testing

1. **Restart the Django development server**
2. Navigate to `/teacher/schedule/`
3. Fill out the form (meeting link can be left empty)
4. Submit the form
5. **Expected Result**: 
   - ✅ Session is created successfully
   - ✅ No IntegrityError for `meeting_url`
   - ✅ No IntegrityError for `scheduled_end`
   - ✅ Session appears in live classes list

## Key Points

1. **`db_column` mapping**: Connects Django field name to actual database column name
2. **Always provide value**: NOT NULL columns must have a value (empty string is acceptable for URLField with blank=True)
3. **Safety net in save()**: Model's save() method ensures field is never None
4. **View validation**: View ensures field is set before calling create()

