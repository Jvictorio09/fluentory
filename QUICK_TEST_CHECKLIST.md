# Quick Testing Checklist - How to Verify Each Item

## 🚀 Quick Start

1. **Set console email backend** (in `myProject/settings.py`):
   ```python
   EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
   ```

2. **Run migrations** (if not done):
   ```bash
   python manage.py migrate
   ```

3. **Start server**:
   ```bash
   python manage.py runserver
   ```

---

## ✅ Checklist Items - How to Check

### 1. Gift Purchase Sends Invite Email to Recipient

**Quick Check:**
- Purchase a gift as a user
- **Look at server console** - you should see email output
- **Look for**: `Subject: You've been gifted a course: [Course Title]`

**Command to verify:**
```bash
# Check server logs for email send
# Look for: "Gift invite email sent to"
```

---

### 2. Gift Purchase Sends Confirmation Email to Buyer

**Quick Check:**
- After purchasing gift (same as #1)
- **Look at server console** - should see SECOND email
- **Look for**: `Subject: Gift Sent: [Course Title]`

**Command to verify:**
```bash
# Check server logs
# Look for: "Gift confirmation email sent to buyer"
```

---

### 3. Gift Claim Sends Success Email to Recipient

**Quick Check:**
1. Get gift token from database or admin
2. Visit: `http://localhost:8000/gift/claim/[token]/`
3. Claim the gift
4. **Look at server console** - should see email
5. **Look for**: `Subject: Welcome to [Course Title]!`

**Database check:**
```python
python manage.py shell
>>> from myApp.models import GiftEnrollment
>>> gift = GiftEnrollment.objects.filter(status='claimed').latest('claimed_at')
>>> print(f"Claimed: {gift.claimed_at}")
```

---

### 4. Gift Claim Sends Notification Email to Buyer

**Quick Check:**
- After claiming gift (same as #3)
- **Look at server console** - should see SECOND email
- **Look for**: `Subject: Your Gift Was Claimed: [Course Title]`

**Note:** This is sent automatically when gift is claimed.

---

### 5. Activity Log Created When Gift is Claimed

**Quick Check:**
```python
python manage.py shell
>>> from myApp.models import ActivityLog
>>> log = ActivityLog.objects.filter(event_type='gift_claimed').latest('created_at')
>>> print(f"Event: {log.get_event_type_display()}")
>>> print(f"Summary: {log.summary}")
>>> print(f"Created: {log.created_at}")
```

**Expected:** Should show gift claimed event with course title and user name.

---

### 6. Activity Log Created When Teacher is Assigned/Reassigned

**Quick Check:**
1. Log in as admin
2. Create or edit a live class
3. Assign/reassign a teacher
4. Check database:

```python
python manage.py shell
>>> from myApp.models import ActivityLog, LiveClassSession
>>> lc = LiveClassSession.objects.latest('updated_at')
>>> logs = ActivityLog.objects.filter(entity_type='live_class', entity_id=lc.id)
>>> for log in logs:
...     print(f"{log.get_event_type_display()}: {log.summary}")
```

**Expected:** Should show teacher_assigned or teacher_reassigned events.

---

### 7. Activity Log Created When Lead Status is Updated

**Quick Check:**
1. Log in as admin
2. Go to `/dashboard/leads/`
3. Edit a lead and change status
4. Check database:

```python
python manage.py shell
>>> from myApp.models import ActivityLog, Lead
>>> lead = Lead.objects.latest('updated_at')
>>> log = ActivityLog.objects.filter(
...     entity_type='lead',
...     entity_id=lead.id,
...     event_type='lead_status_updated'
... ).latest('created_at')
>>> print(f"Status change: {log.summary}")
>>> print(f"Metadata: {log.metadata}")
```

**Expected:** Should show status change from old → new.

---

### 8. 403 Page Shows for Unauthorized Access

**Quick Check:**
1. Log in as a regular user (NOT admin)
2. Try to access: `http://localhost:8000/dashboard/leads/`
3. **Expected:** Should see "403 - Access Denied" page

**Or test via command:**
```python
python manage.py shell
>>> from django.test import Client
>>> from django.contrib.auth.models import User
>>> client = Client()
>>> user = User.objects.filter(profile__role='student').first()
>>> if user:
...     client.force_login(user)
...     response = client.get('/dashboard/leads/')
...     print(f"Status code: {response.status_code}")  # Should be 403
```

---

### 9. Admin-Only Pages are Protected

**Quick Check:**
- Test multiple admin routes as non-admin user:
  - `/dashboard/leads/` → 403
  - `/dashboard/courses/` → 403
  - `/dashboard/live-classes/` → 403
  - `/dashboard/crm-analytics/` → 403

**All should show 403 page, not redirect to home.**

---

### 10. Activity Logs Display Correctly in Detail Pages

**Quick Check:**

**A) Lead Detail:**
1. Go to `/dashboard/leads/[id]/`
2. Scroll to "Timeline / Activity" section
3. Look for "Activity Log" subsection
4. **Expected:** Should see activity logs below timeline events

**B) Live Class Detail:**
1. Go to `/dashboard/live-classes/[id]/`
2. Scroll to "Assignment Activity" section
3. Look for "Activity Log" subsection
4. **Expected:** Should see activity logs below assignment history

**Visual Check:**
- Logs should be formatted consistently
- Show event type, summary, actor, timestamp
- Match Fluentory UI style (dark/light mode compatible)

---

## 🔍 Automated Verification Script

Run the test script:
```bash
python test_implementation.py
```

This will check:
- ✅ All models exist
- ✅ Permissions work
- ✅ Email functions available
- ✅ Activity logs exist
- ✅ Recent gifts/leads/live classes

---

## 📋 Manual Testing Summary

| Item | What to Do | Where to Check |
|------|------------|----------------|
| 1-2 | Purchase gift | Server console (emails) |
| 3-4 | Claim gift | Server console (emails) |
| 5 | Claim gift | Database: `ActivityLog` |
| 6 | Assign teacher | Database: `ActivityLog` |
| 7 | Update lead status | Database: `ActivityLog` |
| 8 | Access as non-admin | Browser: 403 page |
| 9 | Access admin routes | Browser: 403 page |
| 10 | View detail pages | Browser: Activity log section |

---

## 🐛 Troubleshooting

**Emails not showing?**
- Check `EMAIL_BACKEND` is set to `console`
- Check server console output
- Check server logs for errors

**Activity logs not created?**
- Check server logs for errors
- Verify migrations are applied: `python manage.py migrate`
- Check database: `python manage.py shell` → `ActivityLog.objects.count()`

**403 page not showing?**
- Verify template exists: `myApp/templates/403.html`
- Check user role: `user.profile.role`
- Check server logs for errors

**Activity logs not displaying?**
- Check view context includes `activity_logs`
- Check template uses correct variable name
- Verify logs exist in database

---

## ✅ Success Criteria

All items pass if:
- ✅ Emails appear in console/logs
- ✅ Activity logs exist in database
- ✅ Activity logs visible in UI
- ✅ 403 page shows for unauthorized access
- ✅ No errors in server logs

---

For detailed step-by-step instructions, see **TESTING_GUIDE.md**

