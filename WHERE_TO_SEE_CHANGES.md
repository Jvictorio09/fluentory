# Where to See the Booking System Changes

## 🌐 **Web Interface (In Your Browser)**

### **For Teachers:**

#### 1. **Create Group Sessions (Seat-Based)**
- **URL**: `http://localhost:8000/teacher/schedule/`
- **What to see** (✅ **Just Updated**):
  - Form to create live group sessions
  - **New fields added to form**:
    - **Duration** (minutes, default 60)
    - **Meeting Link** (Zoom/Google Meet URL)
    - **Total Seats** (number input, default 10)
    - **Enable Waitlist** (checkbox)
  - Date/Time field
  - List of existing sessions showing:
    - Remaining seats / Total seats
    - Waitlist count (if enabled)

#### 2. **Set 1:1 Availability**
- **URL**: `http://localhost:8000/teacher/availability/`
- **What to see**:
  - Form to create recurring slots (day of week, time range)
  - Form to create one-time slots (specific date/time)
  - List of your availability slots
  - Ability to block/unblock slots

#### 3. **Manage 1:1 Bookings**
- **URL**: `http://localhost:8000/teacher/one-on-one-bookings/`
- **What to see**:
  - List of pending/confirmed/declined 1:1 bookings
  - Approve/Decline buttons for pending bookings
  - Cancel option for confirmed bookings
  - Meeting links

#### 4. **View Session Bookings (Group Sessions)**
- **URL**: `http://localhost:8000/teacher/sessions/<session_id>/bookings/`
- **What to see**:
  - List of students who booked
  - Waitlist (if enabled)
  - Remaining seats count
  - Booking status

---

### **For Students:**

#### 1. **Book Group Session**
- **URL**: `http://localhost:8000/student/sessions/<session_id>/book/`
- **What to see**:
  - Session details with seat availability
  - "Book Now" button (disabled if full)
  - Waitlist option (if enabled)
  - Shows remaining seats count

#### 2. **Book 1:1 Session**
- **URL**: `http://localhost:8000/student/courses/<course_id>/book-one-on-one/`
- **What to see**:
  - List of available time slots for the course
  - Filter by date
  - "Book Slot" button for each available slot
  - Shows which slots are booked/unavailable

#### 3. **View My Bookings**
- **URL**: `http://localhost:8000/student/bookings/`
- **What to see**:
  - Your group session bookings
  - Your 1:1 bookings
  - Booking status (confirmed, waitlisted, pending, etc.)
  - Cancel/Reschedule options

---

## 📁 **Code Files Changed**

### **Models (Database Schema)**
- **File**: `myApp/models.py`
  - **Lines 1012-1119**: `LiveClassSession` model (Group Sessions)
    - `total_seats` field (line 1024)
    - `enable_waitlist` field (line 1025)
    - `meeting_link` field (line 1017)
    - `remaining_seats`, `is_full`, `booking_open` properties
  - **Lines 1135-1248**: `TeacherAvailability` model (1:1 Availability)
    - `slot_type` (recurring/one_time)
    - `start_datetime`, `end_datetime` for one-time slots
    - `is_available_for_booking` property
  - **Lines 1326-1387**: `Booking` model (Group Session Bookings)
    - `seats_booked` field (always 1)
    - Waitlist promotion logic
  - **Lines 1457-1565**: `OneOnOneBooking` model (1:1 Bookings)
    - Status: pending, confirmed, declined
    - Approval workflow
    - Recurring series support

### **Views (Business Logic)**
- **File**: `myApp/views.py`
  - **Lines 2077-2191**: `teacher_schedule()` - Create Group Sessions
  - **Lines 2880-2980**: `teacher_availability()` - Set 1:1 Availability
  - **Lines 3059-3120**: `student_book_session()` - Book Group Session
  - **Lines 3323-3413**: `student_book_one_on_one()` - Book 1:1 Slot
  - **Lines 3500-3560**: `teacher_one_on_one_approve/decline()` - Manage 1:1 Bookings

### **URLs (Routes)**
- **File**: `myProject/urls.py`
  - **Lines 41-47**: Student booking routes
  - **Lines 85-101**: Teacher management routes

### **Admin (Django Admin)**
- **File**: `myApp/admin.py`
  - Updated admin interfaces for all booking models
  - URL: `http://localhost:8000/django-admin/`
  - Models: `LiveClassSession`, `Booking`, `OneOnOneBooking`, `TeacherAvailability`

---

## 🧪 **Testing Steps**

### **Test Group Session Booking:**

1. **As Teacher**:
   ```
   1. Go to: http://localhost:8000/teacher/schedule/
   2. Click "Create New Session"
   3. Fill in:
      - Date/Time
      - Duration: 60 minutes
      - Meeting Link: https://zoom.us/j/123456
      - Total Seats: 5
      - Enable Waitlist: ✓ (checked)
   4. Save
   ```

2. **As Student**:
   ```
   1. Go to: http://localhost:8000/student/sessions/<session_id>/book/
   2. You'll see: "5 seats available"
   3. Click "Book Now"
   4. Status: Confirmed ✓
   
   5. Book 4 more students (total 5) → All confirmed
   6. Book 6th student → Waitlisted ⏳
   7. Cancel 1 booking → 1st waitlisted student promoted to Confirmed
   ```

### **Test 1:1 Booking:**

1. **As Teacher**:
   ```
   1. Go to: http://localhost:8000/teacher/availability/
   2. Create Recurring Slot:
      - Day: Monday
      - Start: 10:00 AM
      - End: 11:00 AM
      - Course: Select a course
   3. Create One-Time Slot:
      - Date: Tomorrow
      - Start: 2:00 PM
      - End: 3:00 PM
   4. Save
   ```

2. **As Student**:
   ```
   1. Go to: http://localhost:8000/student/courses/<course_id>/book-one-on-one/
   2. See available slots
   3. Click "Book" on a slot
   4. If course requires approval: Status = "Pending" ⏳
   5. If no approval needed: Status = "Confirmed" ✓
   ```

3. **As Teacher (Approval)**:
   ```
   1. Go to: http://localhost:8000/teacher/one-on-one-bookings/
   2. See pending bookings
   3. Click "Approve" → Booking confirmed
   4. Click "Decline" → Booking declined
   ```

---

## 📊 **Database Changes**

### **Migration Applied**:
- **File**: `myApp/migrations/0017_add_dual_booking_system.py`
- **Status**: ✅ Applied successfully
- **What it did**:
  - Added `total_seats`, `enable_waitlist`, `meeting_link` to `LiveClassSession`
  - Added `seats_booked` to `Booking`
  - Created `OneOnOneBooking` model
  - Updated `BookingReminder` model

### **View in Database**:
```sql
-- Check Group Sessions
SELECT id, scheduled_start, total_seats, enable_waitlist, meeting_link 
FROM myapp_liveclasssession;

-- Check Bookings (with seat count)
SELECT id, user_id, session_id, seats_booked, status 
FROM myapp_booking;

-- Check 1:1 Bookings
SELECT id, user_id, availability_slot_id, status, meeting_link 
FROM myapp_oneononebooking;

-- Check Availability
SELECT id, slot_type, day_of_week, start_time, end_time, start_datetime 
FROM myapp_teacheravailability;
```

---

## 🎯 **Quick Reference**

| Feature | Teacher View | Student View | Admin View |
|---------|-------------|--------------|------------|
| **Group Sessions** | `/teacher/schedule/` | `/student/sessions/<id>/book/` | `/django-admin/myApp/liveclasssession/` |
| **1:1 Availability** | `/teacher/availability/` | `/student/courses/<id>/book-one-on-one/` | `/django-admin/myApp/teacheravailability/` |
| **1:1 Bookings** | `/teacher/one-on-one-bookings/` | `/student/bookings/` | `/django-admin/myApp/oneononebooking/` |
| **Group Bookings** | `/teacher/sessions/<id>/bookings/` | `/student/bookings/` | `/django-admin/myApp/booking/` |

---

## 🚀 **To Start Testing**

1. **Start Django Server**:
   ```bash
   python manage.py runserver
   ```

2. **Login as Teacher**:
   - Go to: `http://localhost:8000/login/`
   - Login with teacher account

3. **Login as Student**:
   - Go to: `http://localhost:8000/login/`
   - Login with student account

4. **Start Testing**:
   - Follow the testing steps above
   - Check seat counts, waitlist behavior, approval workflow

---

## ✅ **What You Should See**

### **Group Session Features:**
- ✅ Total seats field in creation form
- ✅ Waitlist checkbox
- ✅ Meeting link field
- ✅ Remaining seats displayed
- ✅ Booking closes automatically when full (if no waitlist)
- ✅ Waitlist promotes when seats free up

### **1:1 Booking Features:**
- ✅ Recurring slots (day of week, time range)
- ✅ One-time slots (specific date/time)
- ✅ Course filtering
- ✅ Approval workflow (if enabled)
- ✅ Auto-confirm (if approval disabled)
- ✅ Booked slots removed from availability
- ✅ Recurring series support

---

**All changes are live and ready to test! 🎉**

