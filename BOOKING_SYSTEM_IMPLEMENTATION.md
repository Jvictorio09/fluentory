# Dual Booking System Implementation

## Overview

This document describes the implementation of a dual booking system for the Fluentory learning platform, supporting two distinct booking types with clear logic separation, permissions, and safeguards.

## Booking Types

### A) Group Session Booking (Seat-Based)

**Purpose**: Teachers create live group sessions where multiple students can book seats.

**Features**:
- **Seat Capacity**: Each session has a defined `total_seats` (default: 10)
- **Real-time Seat Tracking**: System tracks `remaining_seats` in real-time
- **Overbooking Prevention**: Cannot book when capacity is reached
- **Auto-close Booking**: Automatically closes when full (if waitlist disabled)
- **Optional Waitlist**: Can enable waitlist that activates after all seats are taken
- **1 Seat per Booking**: Each student booking consumes exactly 1 seat
- **Meeting Links**: Supports Zoom, Google Meet, or custom meeting links

**Model**: `LiveClassSession` (enhanced) + `Booking` (Group Session Bookings)

**Key Fields**:
- `total_seats`: Total seat capacity
- `enable_waitlist`: Enable/disable waitlist
- `meeting_link`: Primary meeting link (Zoom/Google Meet/Custom)
- `status`: Can be 'booking_closed' when full

### B) 1:1 Booking (Availability-Based)

**Purpose**: Students book time slots directly from teacher availability calendar.

**Features**:
- **Availability Slots**: Teachers define recurring or one-time availability slots
- **Direct Booking**: Students book directly from available slots
- **Teacher Approval**: Optional approval workflow (configurable per course/teacher)
- **Prevent Double Booking**: Once booked, slot is removed from availability
- **One-time or Recurring**: Supports single sessions or recurring series
- **Meeting Links**: Set by teacher or auto-generated

**Model**: `OneOnOneBooking` + `TeacherAvailability`

**Key Fields**:
- `availability_slot`: Links to teacher availability slot
- `status`: 'pending', 'confirmed', 'declined', 'cancelled'
- `meeting_link`: Meeting link for 1:1 session
- `is_recurring`: Support for recurring booking series

## Data Models

### Updated Models

#### LiveClassSession
- Added `total_seats` (default: 10)
- Added `enable_waitlist` (boolean)
- Added `meeting_link` (URL field)
- Added `booking_closed` status
- Properties: `remaining_seats`, `is_full`, `booking_open`
- Method: `update_booking_status()` - auto-closes when full

#### Booking (Group Session)
- Renamed to "Group Session Booking" (verbose name)
- Added `seats_booked` field (always 1)
- Updated `confirm()` to update session seat count
- Updated `cancel()` to free up seats and handle waitlist
- `related_name` changed to `group_bookings` on User model

#### TeacherAvailability
- Enhanced with booking availability checks
- Properties: `is_booked`, `is_available_for_booking`
- Method: `can_be_booked(user, course)` - validates booking eligibility

#### OneOnOneBooking (New)
- Links to `TeacherAvailability` slot
- Supports teacher approval workflow
- Handles recurring bookings
- Prevents double booking by deactivating slot

#### BookingReminder (Updated)
- Supports both booking types
- Fields: `group_booking` and `one_on_one_booking` (mutually exclusive)

### Course Model

**Booking Type Control**:
- `booking_type`: Choices - 'none', 'group_session', 'one_on_one'
- `requires_booking_approval`: Boolean for 1:1 bookings

**Teacher Override**:
- `CourseTeacher.requires_booking_approval`: Can override course-level setting per teacher

## Views & URLs

### Student Views

#### Group Session Bookings
- `student_book_session(session_id)`: Book a group session
- `student_bookings`: View all bookings (both types)
- `student_booking_cancel(booking_id)`: Cancel group booking
- `student_booking_reschedule(booking_id)`: Reschedule group booking

#### 1:1 Bookings
- `student_book_one_on_one(course_id)`: View available slots and book
- `student_book_one_on_one_submit(availability_id)`: Submit booking request
- `student_booking_one_on_one_cancel(booking_id)`: Cancel 1:1 booking

### Teacher Views

#### Group Session Management
- `teacher_schedule`: Create and manage group sessions
- `teacher_session_bookings(session_id)`: View bookings for a session
- `teacher_booking_cancel(booking_id)`: Cancel student booking
- `teacher_mark_attendance(booking_id)`: Mark attendance

#### 1:1 Booking Management
- `teacher_one_on_one_bookings`: View all 1:1 booking requests
- `teacher_one_on_one_approve(booking_id)`: Approve booking
- `teacher_one_on_one_decline(booking_id)`: Decline booking
- `teacher_one_on_one_cancel(booking_id)`: Cancel booking

## Business Logic

### Group Session Booking Flow

1. **Teacher Creates Session**:
   - Sets date, time, duration
   - Defines `total_seats` (e.g., 10)
   - Sets meeting link
   - Optionally enables waitlist

2. **Student Books**:
   - Checks if seats available
   - If available: Status = 'confirmed', seat consumed
   - If full + waitlist: Status = 'waitlisted'
   - If full + no waitlist: Cannot book

3. **Seat Management**:
   - Real-time tracking via `remaining_seats` property
   - Auto-closes booking when full (if waitlist disabled)
   - When cancelled, seat freed and waitlist promoted

### 1:1 Booking Flow

1. **Teacher Sets Availability**:
   - Creates recurring or one-time slots
   - Links to course (optional)
   - Sets timezone

2. **Student Views Available Slots**:
   - Filters by course and teacher
   - Shows only `is_available_for_booking` slots

3. **Student Books**:
   - If approval required: Status = 'pending'
   - If no approval: Status = 'confirmed', slot deactivated
   - Slot removed from availability

4. **Teacher Approval** (if required):
   - Reviews pending requests
   - Approve → Status = 'confirmed', slot deactivated
   - Decline → Status = 'declined', slot remains available

5. **Cancellation**:
   - Student/Teacher cancels
   - Slot reactivated (for one-time slots)
   - Notification sent

## Permissions & Safeguards

### Course-Level Control
- Each course has one `booking_type`: 'none', 'group_session', or 'one_on_one'
- Teachers control which type is enabled per course
- UI shows clear labels for booking type

### Group Session Safeguards
- **Seat Limit Enforcement**: Cannot exceed `total_seats`
- **Overbooking Prevention**: Real-time seat counting
- **Waitlist Management**: Automatic promotion when seats free
- **One Booking Per User**: Unique constraint on (user, session)

### 1:1 Booking Safeguards
- **Double Booking Prevention**: Slot deactivated when booked
- **Time Conflict Check**: Validates no overlapping bookings
- **Teacher Approval**: Configurable per course/teacher
- **One Booking Per Slot**: Unique constraint on (user, availability_slot)

## Timezone Support

- `TeacherAvailability.timezone`: Stores teacher's timezone
- `UserProfile.timezone`: Stores student's timezone
- All datetime fields use Django's timezone-aware datetime
- Display conversion handled in templates/views

## Scalability Considerations

- **Database Indexes**: Added on frequently queried fields
- **Efficient Queries**: Uses `select_related` for related objects
- **Real-time Updates**: Properties calculate on-the-fly (can be cached if needed)
- **Notification System**: Asynchronous notifications for booking events

## Future Integration Points

- **Payment Integration**: Booking models ready for payment links
- **Analytics**: Booking data structured for reporting
- **Calendar Integration**: `google_calendar_event_id` field for sync
- **Recurring Series**: Framework for recurring 1:1 bookings

## Migration

Migration file: `0017_add_dual_booking_system.py`

**Changes**:
- Added `OneOnOneBooking` model
- Updated `Booking` model (added `seats_booked`, changed `related_name`)
- Updated `BookingReminder` (supports both types)
- Updated `LiveClassSession` (in migration 0016)

**Data Migration**: Not required - new system is backward compatible with existing bookings.

## Testing Checklist

- [ ] Create group session with seat capacity
- [ ] Book group session (seat tracking)
- [ ] Enable waitlist, test waitlist promotion
- [ ] Cancel booking, verify seat freed
- [ ] Create teacher availability slots
- [ ] Book 1:1 slot (auto-confirm)
- [ ] Book 1:1 slot (with approval required)
- [ ] Teacher approve/decline workflow
- [ ] Cancel 1:1 booking, verify slot reactivated
- [ ] Test timezone handling
- [ ] Test double-booking prevention
- [ ] Test course-level booking type control

## Admin Interface

Both booking types are accessible in Django Admin:
- **Group Session Bookings**: `BookingAdmin`
- **1:1 Bookings**: `OneOnOneBookingAdmin`
- **Booking Reminders**: `BookingReminderAdmin` (handles both types)

## API Endpoints (Future)

The system is structured to support REST API endpoints:
- `/api/bookings/group/` - Group session bookings
- `/api/bookings/one-on-one/` - 1:1 bookings
- `/api/availability/` - Teacher availability slots

## Notes

- Clear separation: Group Session and 1:1 bookings use different models
- UI labels clearly distinguish booking types
- Teachers control booking type per course via `Course.booking_type`
- System is timezone-aware and scalable
- Ready for payment and analytics integration

