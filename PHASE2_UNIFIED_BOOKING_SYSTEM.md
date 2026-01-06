# Phase 2: Unified Booking System - Implementation Summary

## ✅ Models Created

### 1. **LiveClassSession** (Extended)
**New Fields Added:**
- `start_at_utc` - Session start time in UTC
- `end_at_utc` - Session end time in UTC
- `timezone_snapshot` - Teacher timezone at creation time
- `meeting_provider` - Zoom / Google Meet / Microsoft Teams / Custom
- `meeting_passcode` - Meeting passcode/password
- `capacity` - Alias for total_seats (Phase 2 naming)
- `seats_taken` - Cached count of confirmed bookings

**Backward Compatibility:**
- `scheduled_start` remains for legacy support
- `meeting_password` remains as legacy field
- `total_seats` remains, `capacity` is alias

### 2. **LiveClassBooking** (Unified Model)
**Replaces:** `Booking` + `OneOnOneBooking`

**Core Fields:**
- `booking_type` - 'group_session' or 'one_on_one'
- `course`, `teacher`, `student_user`
- `start_at_utc`, `end_at_utc` - UTC-based scheduling
- `status` - pending, confirmed, declined, cancelled, attended, no_show, rescheduled

**Group-Specific:**
- `session` - FK to LiveClassSession (nullable for 1:1)
- `seats_reserved` - Number of seats (default 1)

**Approval & Audit:**
- `decision_at`, `decided_by` - Approval tracking
- `cancelled_by`, `cancelled_at`, `cancel_reason` - Cancellation tracking

**Notes:**
- `student_note`, `teacher_note`

**Indexes:**
- `(booking_type, status)`
- `(student_user, start_at_utc)`
- `(teacher, start_at_utc)`

### 3. **TeacherBookingPolicy**
**Controls booking rules per teacher/course**

**Fields:**
- `teacher`, `course` (nullable - default policy if null)
- `requires_approval_for_one_on_one` - Boolean
- `requires_approval_for_group` - Boolean (usually false)
- `min_notice_hours` - Minimum hours before booking allowed
- `cancel_window_hours` - Hours before start when cancellation allowed
- `buffer_before_minutes`, `buffer_after_minutes` - Buffer times
- `max_bookings_per_day` - Optional daily limit

**Unique Constraint:** `(teacher, course)` - One policy per teacher per course

### 4. **BookingSeries**
**Recurring booking series**

**Fields:**
- `student_user`, `teacher`, `course`
- `type` - 'one_on_one_series' or 'group_series'
- `status` - active, paused, cancelled, completed
- `frequency` - weekly, biweekly, monthly, custom
- `interval` - Interval for frequency (e.g., every 2 weeks)
- `days_of_week` - Comma-separated days for weekly recurrences
- `occurrence_count` OR `until_date` - Series end condition
- `default_meeting_link`, `default_meeting_id`, `default_meeting_passcode`

### 5. **BookingSeriesItem**
**Individual occurrence in a series**

**Fields:**
- `series` - FK to BookingSeries
- `booking` - FK to LiveClassBooking
- `occurrence_index` - Occurrence number (1, 2, 3, ...)

**Unique Constraint:** `(series, occurrence_index)`

### 6. **SessionWaitlist**
**Waitlist for group sessions**

**Fields:**
- `session` - FK to LiveClassSession
- `student_user` - FK to User
- `status` - waiting, offered, accepted, expired
- `created_at`, `offered_at`, `accepted_at`, `expired_at`

**Unique Constraint:** `(session, student_user)` - One waitlist entry per student per session

**Methods:**
- `offer_seat()` - Offer seat to this waitlist entry
- `accept_offer()` - Accept the offered seat
- `expire_offer()` - Mark offer as expired

## 📋 Migration Created

**File:** `myApp/migrations/0018_phase2_unified_booking_system.py`

**Changes:**
- Added new fields to LiveClassSession
- Created 5 new models (LiveClassBooking, TeacherBookingPolicy, BookingSeries, BookingSeriesItem, SessionWaitlist)
- Created indexes for performance
- Set up unique constraints

## 🔄 Backward Compatibility

### Legacy Models Still Exist:
- `Booking` - Still functional, but new bookings should use `LiveClassBooking`
- `OneOnOneBooking` - Still functional, but new bookings should use `LiveClassBooking`
- `TeacherAvailability` - Still used for 1:1 availability slots

### Migration Strategy:
1. **Phase 2 models coexist** with Phase 1 models
2. **New bookings** should use `LiveClassBooking`
3. **Legacy bookings** remain in `Booking`/`OneOnOneBooking` for history
4. **Views can be updated gradually** to use unified model

## 🎯 Design Goals Achieved

✅ **Unified Booking Model** - Single model for group + 1:1  
✅ **UTC-Based Scheduling** - All times stored in UTC with timezone snapshot  
✅ **Approval Workflow** - Policy-based approval rules  
✅ **Recurring Series** - Support for recurring bookings with history preservation  
✅ **Waitlist System** - FIFO waitlist with offer/accept/expire workflow  
✅ **Audit Trail** - Complete tracking of decisions, cancellations, approvals  
✅ **No Breaking Changes** - Phase 1 UI continues to work  

## 🚀 Next Steps

1. **Run Migration:**
   ```bash
   python manage.py migrate myApp 0018
   ```

2. **Update Views:**
   - Gradually migrate views to use `LiveClassBooking`
   - Keep legacy models for backward compatibility

3. **Add Signals:**
   - Auto-update `seats_taken` when bookings confirmed/cancelled
   - Auto-populate `start_at_utc`/`end_at_utc` from `scheduled_start`

4. **Add Notifications:**
   - Waitlist offer notifications
   - Approval request notifications
   - Series booking confirmations

5. **Add Calendar Sync:**
   - Export bookings to Google Calendar/iCal
   - Import availability from external calendars

## 📊 Database Schema

```
LiveClassSession
├── start_at_utc, end_at_utc (NEW)
├── timezone_snapshot (NEW)
├── meeting_provider, meeting_passcode (NEW)
├── capacity, seats_taken (NEW)
└── ... (existing fields)

LiveClassBooking (NEW)
├── booking_type (group_session | one_on_one)
├── course, teacher, student_user
├── start_at_utc, end_at_utc
├── session (nullable for 1:1)
├── seats_reserved
└── ... (approval/audit fields)

TeacherBookingPolicy (NEW)
├── teacher, course (nullable)
└── ... (approval rules)

BookingSeries (NEW)
├── student_user, teacher, course
├── type, status
└── ... (recurrence rules)

BookingSeriesItem (NEW)
├── series, booking, occurrence_index
└── ...

SessionWaitlist (NEW)
├── session, student_user
├── status
└── ... (timestamps)
```

## ✅ Status: Models Created & Migration Ready

All Phase 2 models are implemented and ready for migration. The system supports:
- Unified booking model
- Policy-based approvals
- Recurring series
- Waitlist management
- Complete audit trail

**Ready for:** Phase 3 (Payments, Notifications, Calendar Sync)




