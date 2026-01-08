# Fluentory Testing Guide - Email, Permissions & Activity Logs

## Prerequisites

1. **Set up console email backend** (for easy email testing):
   ```python
   # In myProject/settings.py or environment variables
   EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
   ```
   This will print emails to the console instead of sending them.

2. **Start Django development server**:
   ```bash
   python manage.py runserver
   ```

3. **Have test accounts ready**:
   - Admin user
   - Regular user (for gift buyer)
   - Another user (for gift recipient)

---

## Testing Checklist

### ✅ 1. Gift Purchase Sends Invite Email to Recipient

**Steps:**
1. Log in as a regular user (buyer)
2. Navigate to a course page
3. Click "Gift this Course"
4. Fill in:
   - Recipient email: `test-recipient@example.com`
   - Recipient name (optional)
   - Gift message (optional)
   - Sender name (optional)
5. Complete the purchase/payment flow
6. **Check Console Output**: Look for email in server console:
   ```
   Subject: You've been gifted a course: [Course Title]
   To: test-recipient@example.com
   ```
7. **Check Server Logs**: Look for:
   ```
   INFO: Gift invite email sent to test-recipient@example.com
   INFO: Email sent successfully: subject='...', recipient=['test-recipient@example.com']
   ```

**What to Verify:**
- Email appears in console with correct recipient
- Email contains course title, claim button, gift message (if provided)
- No errors in server logs

**Database Check:**
```python
python manage.py shell
>>> from myApp.models import GiftEnrollment
>>> gift = GiftEnrollment.objects.latest('created_at')
>>> print(f"Recipient: {gift.recipient_email}, Status: {gift.status}")
```

---

### ✅ 2. Gift Purchase Sends Confirmation Email to Buyer

**Steps:**
1. Complete a gift purchase (same as test #1)
2. **Check Console Output**: Look for SECOND email in server console:
   ```
   Subject: Gift Sent: [Course Title]
   To: [buyer's email]
   ```
3. **Check Server Logs**: Look for:
   ```
   INFO: Gift confirmation email sent to buyer
   INFO: Email sent successfully: subject='Gift Sent: ...', recipient=['buyer@example.com']
   ```

**What to Verify:**
- Buyer receives confirmation email
- Email contains recipient email, order reference, course title
- No errors in server logs

**Database Check:**
```python
python manage.py shell
>>> from myApp.models import GiftEnrollment
>>> gift = GiftEnrollment.objects.latest('created_at')
>>> print(f"Buyer: {gift.buyer.email}, Payment: {gift.payment}")
```

---

### ✅ 3. Gift Claim Sends Success Email to Recipient

**Steps:**
1. Get a gift token from a pending gift:
   ```python
   python manage.py shell
   >>> from myApp.models import GiftEnrollment
   >>> gift = GiftEnrollment.objects.filter(status='pending_claim').first()
   >>> print(gift.gift_token)
   ```
2. Log out (or use incognito/private window)
3. Navigate to: `http://localhost:8000/gift/claim/[gift_token]/`
4. Sign up or log in with the recipient email
5. Claim the gift
6. **Check Console Output**: Look for email:
   ```
   Subject: Welcome to [Course Title]!
   To: [recipient email]
   ```
7. **Check Server Logs**: Look for:
   ```
   INFO: Activity logged: gift_claimed for gift #X by [user]
   INFO: Email sent successfully: subject='Welcome to ...', recipient=['recipient@example.com']
   ```

**What to Verify:**
- Recipient receives "Welcome" email after claiming
- Email contains course title and "Open Course Dashboard" button
- Gift status changes to 'claimed' in database
- Enrollment is created

**Database Check:**
```python
python manage.py shell
>>> from myApp.models import GiftEnrollment, Enrollment
>>> gift = GiftEnrollment.objects.latest('updated_at')
>>> print(f"Status: {gift.status}, Claimed at: {gift.claimed_at}")
>>> print(f"Enrollment: {gift.enrollment}")
```

---

### ✅ 4. Gift Claim Sends Notification Email to Buyer

**Steps:**
1. Complete gift claim (same as test #3)
2. **Check Console Output**: Look for SECOND email:
   ```
   Subject: Your Gift Was Claimed: [Course Title]
   To: [buyer's email]
   ```
3. **Check Server Logs**: Look for:
   ```
   INFO: Email sent successfully: subject='Your Gift Was Claimed: ...', recipient=['buyer@example.com']
   ```

**What to Verify:**
- Buyer receives notification that gift was claimed
- Email contains recipient email and claimed date
- Both emails (recipient + buyer) are sent

**Note:** Buyer notification is enabled by default (`notify_buyer=True` in `send_claim_success_email`)

---

### ✅ 5. Activity Log Created When Gift is Claimed

**Steps:**
1. Claim a gift (same as test #3)
2. **Check Database**:
   ```python
   python manage.py shell
   >>> from myApp.models import ActivityLog
   >>> log = ActivityLog.objects.filter(event_type='gift_claimed').latest('created_at')
   >>> print(f"Event: {log.get_event_type_display()}")
   >>> print(f"Summary: {log.summary}")
   >>> print(f"Actor: {log.actor}")
   >>> print(f"Metadata: {log.metadata}")
   ```
3. **Check Server Logs**: Look for:
   ```
   INFO: Activity logged: gift_claimed for gift #X by [user]
   ```

**What to Verify:**
- ActivityLog entry exists with `entity_type='gift'`
- `event_type='gift_claimed'`
- Summary contains course title and user name
- Metadata contains gift_id, enrollment_id, course_id

**UI Check:**
- Navigate to gift detail page (if exists) or check in admin
- Activity log should be visible

---

### ✅ 6. Activity Log Created When Teacher is Assigned/Reassigned

**Steps:**

**A) Test Teacher Assignment (New Live Class):**
1. Log in as admin
2. Navigate to: `/dashboard/live-classes/create/`
3. Fill in live class details
4. Select a teacher from dropdown
5. Save
6. **Check Database**:
   ```python
   python manage.py shell
   >>> from myApp.models import ActivityLog, LiveClassSession
   >>> live_class = LiveClassSession.objects.latest('created_at')
   >>> log = ActivityLog.objects.filter(
   ...     entity_type='live_class',
   ...     entity_id=live_class.id,
   ...     event_type='teacher_assigned'
   ... ).first()
   >>> print(f"Event: {log.get_event_type_display()}")
   >>> print(f"Summary: {log.summary}")
   >>> print(f"Actor: {log.actor}")
   ```

**B) Test Teacher Reassignment:**
1. Navigate to: `/dashboard/live-classes/[id]/edit/`
2. Change the assigned teacher
3. Add reason/notes (optional)
4. Save
5. **Check Database**:
   ```python
   python manage.py shell
   >>> from myApp.models import ActivityLog, LiveClassSession
   >>> live_class = LiveClassSession.objects.get(id=[id])
   >>> log = ActivityLog.objects.filter(
   ...     entity_type='live_class',
   ...     entity_id=live_class.id,
   ...     event_type='teacher_reassigned'
   ... ).latest('created_at')
   >>> print(f"Event: {log.get_event_type_display()}")
   >>> print(f"Summary: {log.summary}")
   >>> print(f"Metadata: {log.metadata}")
   ```

**What to Verify:**
- ActivityLog entry exists with `entity_type='live_class'`
- `event_type` is 'teacher_assigned' or 'teacher_reassigned'
- Summary shows teacher names
- Actor is the admin user who made the assignment
- Metadata contains live_class_id, teacher_id, course_id

**UI Check:**
- Navigate to: `/dashboard/live-classes/[id]/`
- Scroll to "Activity Log" section
- Should see assignment/reassignment entries

---

### ✅ 7. Activity Log Created When Lead Status is Updated

**Steps:**
1. Log in as admin
2. Navigate to: `/dashboard/leads/`
3. Click on a lead to view details
4. Click "Edit Lead"
5. Change the status (e.g., from "New" to "Contacted")
6. Save
7. **Check Database**:
   ```python
   python manage.py shell
   >>> from myApp.models import ActivityLog, Lead
   >>> lead = Lead.objects.latest('updated_at')
   >>> log = ActivityLog.objects.filter(
   ...     entity_type='lead',
   ...     entity_id=lead.id,
   ...     event_type='lead_status_updated'
   ... ).latest('created_at')
   >>> print(f"Event: {log.get_event_type_display()}")
   >>> print(f"Summary: {log.summary}")
   >>> print(f"Old Status: {log.metadata.get('old_status')}")
   >>> print(f"New Status: {log.metadata.get('new_status')}")
   >>> print(f"Actor: {log.actor}")
   ```

**What to Verify:**
- ActivityLog entry exists with `entity_type='lead'`
- `event_type='lead_status_updated'`
- Summary shows old status → new status
- Metadata contains old_status, new_status, lead_id, lead_email
- Actor is the admin user who made the change

**UI Check:**
- Navigate to: `/dashboard/leads/[id]/`
- Scroll to "Activity Log" section (below Timeline)
- Should see status update entry

---

### ✅ 8. 403 Page Shows for Unauthorized Access

**Steps:**

**A) Test as Non-Admin:**
1. Log in as a regular user (student role)
2. Try to access admin-only pages:
   - `/dashboard/leads/`
   - `/dashboard/courses/`
   - `/dashboard/live-classes/`
   - `/dashboard/crm-analytics/`
3. **Expected**: Should see 403 page with:
   - "403 - Access Denied" heading
   - "You don't have permission to access this page" message
   - User role displayed
   - "Go to Home" and "My Dashboard" buttons

**B) Test as Teacher (if applicable):**
1. Log in as teacher
2. Try to access admin-only pages (same as above)
3. **Expected**: Should see 403 page

**C) Test Direct URL Access:**
1. Log out completely
2. Try to access: `/dashboard/leads/1/edit/`
3. **Expected**: Should redirect to login, then show 403 after login if not admin

**What to Verify:**
- 403 page displays correctly
- Page shows user's current role
- Navigation buttons work
- No errors in server logs

**Server Logs Check:**
- Should see no errors, just normal access attempts

---

### ✅ 9. Admin-Only Pages are Protected

**Steps:**
1. Create a list of all admin-only routes:
   ```python
   # Check myApp/dashboard_urls.py for routes with @role_required(['admin'])
   ```
2. Test each route as:
   - **Non-authenticated user**: Should redirect to login
   - **Regular user (student)**: Should show 403
   - **Admin user**: Should show page normally

**Key Routes to Test:**
- `/dashboard/` (overview)
- `/dashboard/leads/`
- `/dashboard/leads/create/`
- `/dashboard/leads/[id]/`
- `/dashboard/leads/[id]/edit/`
- `/dashboard/courses/`
- `/dashboard/courses/create/`
- `/dashboard/live-classes/`
- `/dashboard/live-classes/create/`
- `/dashboard/crm-analytics/`
- `/dashboard/teachers/`
- `/dashboard/users/`

**What to Verify:**
- All routes require authentication
- All routes check for admin role
- Non-admins see 403 page
- Admins can access all pages

**Quick Test Script:**
```python
# Create test_users.py
from django.test import Client
from django.contrib.auth.models import User
from myApp.models import UserProfile

# Test as student
student = User.objects.filter(profile__role='student').first()
client = Client()
client.force_login(student)
response = client.get('/dashboard/leads/')
print(f"Student access: {response.status_code}")  # Should be 403

# Test as admin
admin = User.objects.filter(profile__role='admin').first()
client.force_login(admin)
response = client.get('/dashboard/leads/')
print(f"Admin access: {response.status_code}")  # Should be 200
```

---

### ✅ 10. Activity Logs Display Correctly in Detail Pages

**Steps:**

**A) Lead Detail Page:**
1. Log in as admin
2. Navigate to: `/dashboard/leads/[id]/`
3. Scroll down to "Timeline / Activity" section
4. Look for "Activity Log" subsection (below timeline events)
5. **Verify**:
   - Activity logs are displayed
   - Each log shows: Event type, Summary, Actor, Timestamp
   - Logs are in reverse chronological order (newest first)
   - Formatting matches Fluentory UI style

**B) Live Class Detail Page:**
1. Navigate to: `/dashboard/live-classes/[id]/`
2. Scroll to "Assignment Activity" section
3. Look for "Activity Log" subsection (below assignment history)
4. **Verify**:
   - Activity logs are displayed
   - Shows teacher assignment/reassignment events
   - Formatting matches Fluentory UI style

**C) Test with Multiple Logs:**
1. Perform multiple actions (status changes, assignments)
2. Refresh detail page
3. **Verify**:
   - All logs are displayed
   - No duplicates
   - Correct ordering

**What to Verify:**
- Activity logs section is visible
- Logs are properly formatted
- All fields display correctly (event type, summary, actor, timestamp)
- Empty state shows if no logs exist
- UI matches Fluentory design (dark/light mode compatible)

**Database Verification:**
```python
python manage.py shell
>>> from myApp.models import ActivityLog, Lead, LiveClassSession
>>> 
>>> # Check lead activity logs
>>> lead = Lead.objects.first()
>>> logs = ActivityLog.objects.filter(entity_type='lead', entity_id=lead.id)
>>> print(f"Lead {lead.id} has {logs.count()} activity logs")
>>> 
>>> # Check live class activity logs
>>> live_class = LiveClassSession.objects.first()
>>> logs = ActivityLog.objects.filter(entity_type='live_class', entity_id=live_class.id)
>>> print(f"Live class {live_class.id} has {logs.count()} activity logs")
```

---

## Quick Verification Commands

### Check All Activity Logs
```python
python manage.py shell
>>> from myApp.models import ActivityLog
>>> logs = ActivityLog.objects.all().order_by('-created_at')[:10]
>>> for log in logs:
...     print(f"{log.created_at} - {log.get_event_type_display()} - {log.summary}")
```

### Check Email Logs (if using file backend)
```bash
# If EMAIL_BACKEND is set to file backend
cat emails/*.log
```

### Check Server Logs
```bash
# Look for email and activity log entries
tail -f logs/django.log | grep -E "(Email|Activity|gift|teacher|lead)"
```

### Verify Permissions
```python
python manage.py shell
>>> from myApp.permissions import is_admin, is_teacher
>>> from django.contrib.auth.models import User
>>> 
>>> user = User.objects.get(username='testuser')
>>> print(f"Is admin: {is_admin(user)}")
>>> print(f"Is teacher: {is_teacher(user)}")
```

---

## Common Issues & Solutions

### Emails Not Appearing
- **Check**: `EMAIL_BACKEND` setting
- **Solution**: Use `console` backend for testing: `EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'`

### Activity Logs Not Created
- **Check**: Server logs for errors
- **Solution**: Verify imports are correct, check exception handling

### 403 Page Not Showing
- **Check**: Template exists at `myApp/templates/403.html`
- **Solution**: Verify `role_required` decorator is updated

### Activity Logs Not Displaying
- **Check**: Context variable name in view matches template
- **Solution**: Verify `activity_logs` is in context and template uses correct variable name

---

## Test Data Setup

### Create Test Gift
```python
python manage.py shell
>>> from django.contrib.auth.models import User
>>> from myApp.models import Course, GiftEnrollment
>>> 
>>> buyer = User.objects.first()
>>> course = Course.objects.first()
>>> gift = GiftEnrollment.objects.create(
...     buyer=buyer,
...     course=course,
...     recipient_email='test@example.com',
...     recipient_name='Test Recipient',
...     sender_name='Test Sender',
...     gift_message='Test gift message',
...     status='pending_claim'
... )
>>> print(f"Gift token: {gift.gift_token}")
```

### Create Test Lead
```python
python manage.py shell
>>> from myApp.models import Lead
>>> lead = Lead.objects.create(
...     name='Test Lead',
...     email='testlead@example.com',
...     source='website',
...     status='new'
... )
>>> print(f"Lead ID: {lead.id}")
```

---

## Success Criteria

All tests pass if:
- ✅ Emails appear in console/logs with correct content
- ✅ Activity logs are created in database
- ✅ Activity logs display in UI
- ✅ 403 page shows for unauthorized access
- ✅ Admin pages are accessible only to admins
- ✅ No errors in server logs
- ✅ All UI elements render correctly

