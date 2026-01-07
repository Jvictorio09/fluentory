# Teacher and Student Functions Documentation

**Last Updated:** Based on comprehensive codebase review  
**Project:** Fluentory Learning Platform

---

## Table of Contents

1. [Teacher Functions](#teacher-functions)
2. [Student Functions](#student-functions)
3. [Shared Features](#shared-features)
4. [Models and Data Structures](#models-and-data-structures)

---

## TEACHER FUNCTIONS

### Overview
Teachers (also referred to as Instructors in the system) are content creators and class deliverers who manage courses, lessons, quizzes, and interact with students. Teachers require approval from admins before they can fully access the platform.

### Access & Authentication
- **Role**: Uses `'instructor'` role in `UserProfile` but has separate `Teacher` model
- **Dashboard**: `/teacher/` - Teacher Dashboard
- **Approval System**: Teachers must be approved by admins before full access
- **Permission Levels**: Standard, Premium, Admin

### Core Teacher Capabilities

#### 1. **Dashboard & Analytics**
- **Function**: `teacher_dashboard()`
- **Features**:
  - View key performance indicators (KPIs)
  - Total students count
  - Active students (last 7 days)
  - Total assigned courses
  - Upcoming live classes (next 5)
  - Recent announcements
  - Unread messages count
  - Online status tracking
  - Live activity feed

#### 2. **Course Management**
- **View Courses**: `teacher_courses()`
  - View all assigned courses
  - Filter by status (draft, published, archived)
  - Search courses by title/description
  - View course assignments with permissions

- **Create Course**: `teacher_course_create()`
  - Create new courses
  - Set course metadata (title, description, outcome)
  - Choose category and level
  - Set course type (Recorded, Live, Hybrid)
  - Set pricing (free or paid)
  - Auto-assigned with full permissions

- **Edit Course**: `teacher_course_edit()`
  - Edit course details
  - Update metadata, pricing, status
  - Upload/change thumbnail
  - Permission-based access (requires 'edit' or 'full' permission)

#### 3. **Lesson Management**
- **View Lessons**: `teacher_lessons()`
  - View all lessons in a course
  - Organized by modules
  - Filter by module

- **Create Lesson**: `teacher_lesson_create()`
  - Create new lessons within modules
  - Set lesson type (Video, Text, Quiz, Assignment, Interactive)
  - Add video URL and duration
  - Add text content
  - Set lesson order
  - Mark as preview lesson
  - Set unlock conditions

- **Edit Lesson**: `teacher_lesson_edit()`
  - Modify lesson content
  - Update video/text content
  - Change lesson settings
  - Reorder lessons

#### 4. **Quiz Management**
- **View Quizzes**: `teacher_quizzes()`
  - View all quizzes for a course
  - Filter by quiz type (Lesson, Module, Final, Placement)

- **Create Quiz**: `teacher_quiz_create()`
  - Create new quizzes
  - Set quiz type
  - Configure settings:
    - Passing score (default: 70%)
    - Time limit (optional)
    - Max attempts (default: 3)
    - Randomize questions
    - Show correct answers

- **Edit Quiz**: `teacher_quiz_edit()`
  - Modify quiz settings
  - Update quiz details

- **Manage Questions**: `teacher_quiz_questions()`
  - Add/edit/delete questions
  - Question types:
    - Multiple Choice
    - True/False
    - Fill in the Blank
    - Matching
    - Short Answer
  - Set points per question
  - Add explanations and hints
  - Reorder questions

#### 5. **Student Management**
- **View Students**: `teacher_course_students()`
  - View all students enrolled in assigned courses
  - View student progress
  - Track completion rates
  - View individual student details

- **Student Progress Tracking**:
  - View lesson completion status
  - Track quiz attempts and scores
  - Monitor enrollment progress
  - View time spent on lessons

#### 6. **Live Classes**
- **Schedule Live Classes**: `teacher_course_live_classes()`
  - Create scheduled live class sessions
  - Set date, time, and duration
  - Add video conferencing links (Zoom, Google Meet)
  - Set meeting ID and password
  - Set maximum attendees
  - Manage session status (Scheduled, Live, Completed, Cancelled)

- **Availability Management**: `teacher_availability()`
  - Set recurring weekly availability slots
  - Create one-time availability slots
  - Block/unblock time slots
  - Set timezone
  - Link availability to specific courses

- **Session Management**:
  - Start/end live sessions
  - Track attendance
  - Manage bookings and waitlists
  - Handle cancellations and rescheduling

#### 7. **Announcements**
- **Send Announcements**: `teacher_announcements()`
  - Create course announcements
  - Pin important announcements
  - Send to all enrolled students
  - View announcement history

#### 8. **Messaging**
- **Message Students**: `StudentMessage` model
  - Send messages to enrolled students
  - Reply to student messages
  - Track read/unread status
  - Link messages to specific courses

#### 9. **AI Tutor Configuration**
- **Configure AI Tutor**: `teacher_ai_settings()`
  - Set AI model (GPT-4o Mini, GPT-4o, GPT-3.5 Turbo)
  - Configure temperature and max tokens
  - Choose personality style:
    - Friendly & Encouraging
    - Professional & Formal
    - Casual & Conversational
    - Enthusiastic & Motivational
    - Patient & Supportive
    - Custom
  - Set custom system prompts
  - Configure context inclusion
  - Set conversation history limits

### Teacher Models & Properties

#### Teacher Model
- `user`: OneToOne relationship with User
- `permission_level`: Standard, Premium, Admin
- `is_approved`: Approval status
- `approved_at`: When approved
- `approved_by`: Admin who approved
- `is_online`: Current online status
- `last_seen`: Last activity timestamp
- `bio`: Teacher biography
- `specialization`: Area of expertise
- `years_experience`: Experience level

#### CourseTeacher Model (Course Assignments)
- `course`: ForeignKey to Course
- `teacher`: ForeignKey to Teacher
- `permission_level`: View Only, Can Edit, Full Access
- `can_create_live_classes`: Boolean
- `can_manage_schedule`: Boolean
- `assigned_at`: Assignment timestamp
- `assigned_by`: User who assigned

### Teacher Methods
- `update_online_status(is_online_value)`: Update online status and timestamp
- `is_recently_online`: Property to check if online in last 15 minutes

---

## STUDENT FUNCTIONS

### Overview
Students are learners who enroll in courses, take lessons, complete quizzes, interact with AI tutors, and earn certificates. They are the primary consumers of the platform's educational content.

### Access & Authentication
- **Role**: `'student'` role in `UserProfile` (default role)
- **Dashboard**: `/student/` - Student Dashboard
- **Default Access**: All new users are students by default

### Core Student Capabilities

#### 1. **Dashboard & Home**
- **Function**: `student_home()`
- **Features**:
  - Current enrollment (continue learning)
  - Active enrollments list (last 5)
  - Recommended courses (not enrolled)
  - Placement test results
  - Upcoming milestones/quizzes
  - Certificates count
  - Weekly learning minutes
  - Unread notifications
  - Learning streak tracking
  - Progress overview

#### 2. **Course Browsing & Enrollment**
- **Browse Courses**: `student_courses()`
  - View course catalog
  - Filter by level (Beginner, Intermediate, Advanced)
  - Filter by category
  - Search courses
  - View multi-currency pricing
  - See enrolled status
  - Pagination (12 courses per page)

- **Course Detail**: `student_course_detail()`
  - View full course information
  - See course modules and lessons
  - Read reviews and ratings
  - View similar courses
  - Check enrollment status
  - Enroll in course
  - View pricing in selected currency

#### 3. **Learning & Progress**
- **My Learning**: `student_learning()`
  - View all active enrollments
  - View completed courses
  - Track progress percentage
  - See current lesson position
  - Calculate estimated hours remaining
  - View days since enrollment
  - Continue learning from last position

- **Course Player**: `student_course_player()`
  - Watch video lessons
  - Read text lessons
  - Take interactive lessons
  - Track video position (resume playback)
  - Track time spent
  - Mark lessons as complete
  - Take notes on lessons
  - Navigate between lessons
  - View lesson progress
  - Access AI tutor from lessons

#### 4. **Quizzes & Assessments**
- **Take Quizzes**:
  - Lesson quizzes
  - Module quizzes
  - Final assessments
  - Placement tests
  - Multiple question types
  - See results and explanations
  - Track attempts
  - View passing status

- **Placement Test**: `student_placement()`
  - Take placement assessment
  - Get recommended level (Beginner, Intermediate, Advanced)
  - Receive course recommendations
  - View detailed category scores
  - Retake placement test

#### 5. **AI Tutor**
- **AI Tutor Conversations**:
  - Start conversations with AI tutor
  - Ask questions about lessons
  - Get explanations and help
  - Context-aware responses (includes lesson/course context)
  - Multiple conversation threads
  - View conversation history
  - Customizable AI personality (set by teacher)

#### 6. **Certificates**
- **View Certificates**: `student_certificates()`
  - View all earned certificates
  - Download certificate PDFs
  - View QR codes for verification
  - Access verification URLs
  - See certificate details (course, issue date)

#### 7. **Live Classes & Bookings**
- **View Bookings**: `student_bookings()`
  - View all live class bookings
  - See booking status (Pending, Confirmed, Waitlisted, Cancelled, Attended)
  - View upcoming sessions
  - Cancel bookings (up to 24 hours before)
  - Reschedule bookings
  - View session details

- **Book Sessions**: `student_sessions_book()`
  - Browse available live class sessions
  - Book sessions for enrolled courses
  - Join waitlist if full
  - Receive booking confirmations
  - Get reminders (24h, 1h before)

#### 8. **Settings & Profile**
- **Account Settings**: `student_settings()`
  - Update personal information (name, email)
  - Set preferred language
  - Set timezone
  - Set daily learning goal (minutes)
  - Update learning goals
  - Manage profile preferences

- **Currency Selection**: `set_currency()`
  - Select preferred currency for pricing
  - View courses in selected currency
  - Multi-currency support (USD, EUR, SAR, AED, JOD, GBP)

#### 9. **Progress Tracking**
- **Learning Streaks**:
  - Automatic streak calculation
  - Current streak tracking
  - Longest streak record
  - Daily activity tracking
  - Streak updates on activity

- **Progress Metrics**:
  - Course completion percentage
  - Lesson completion status
  - Quiz scores and attempts
  - Time spent learning
  - Total learning minutes
  - Weekly learning statistics

### Student Models & Properties

#### Enrollment Model
- `user`: ForeignKey to User
- `course`: ForeignKey to Course
- `status`: Active, Completed, Paused, Expired
- `progress_percentage`: Completion percentage
- `current_module`: Current module position
- `current_lesson`: Current lesson position
- `enrolled_at`: Enrollment timestamp
- `expires_at`: Access expiration (optional)
- `completed_at`: Completion timestamp
- `is_gifted`: Gifted enrollment flag
- `gifted_by`: User who gifted
- `partner`: Partner organization (if applicable)

#### LessonProgress Model
- `enrollment`: ForeignKey to Enrollment
- `lesson`: ForeignKey to Lesson
- `started_at`: When lesson was started
- `completed`: Completion status
- `completed_at`: Completion timestamp
- `video_position`: Last video position (seconds)
- `time_spent`: Total time spent (seconds)
- `notes`: Student notes on lesson

#### QuizAttempt Model
- `user`: ForeignKey to User
- `quiz`: ForeignKey to Quiz
- `enrollment`: ForeignKey to Enrollment (optional)
- `score`: Percentage score
- `passed`: Passing status
- `started_at`: Start timestamp
- `completed_at`: Completion timestamp
- `time_taken`: Time spent (seconds)
- `answers`: JSON field storing answers

#### Certificate Model
- `certificate_id`: Unique UUID
- `user`: ForeignKey to User
- `course`: ForeignKey to Course
- `enrollment`: OneToOne with Enrollment
- `issued_at`: Issue timestamp
- `title`: Certificate title
- `qr_code`: QR code image
- `verification_url`: Public verification URL
- `pdf_file`: Certificate PDF
- `is_verified`: Verification status
- `verified_count`: Number of verifications

### Student Methods
- `Enrollment.update_progress()`: Calculate and update progress percentage
- `LessonProgress.mark_complete()`: Mark lesson as complete and update enrollment
- `Certificate.generate_qr_code()`: Generate QR code for verification
- `UserProfile.update_streak()`: Update learning streak based on activity

---

## SHARED FEATURES

### 1. **Notifications**
- Milestone reached
- Certificate earned
- Learning reminders
- Announcements
- Payment updates
- Course updates
- Read/unread tracking

### 2. **Reviews & Ratings**
- Students can review courses
- Rate courses (1-5 stars)
- Write review content
- View all course reviews
- Featured reviews

### 3. **Multi-Currency Support**
- USD, EUR, SAR, AED, JOD, GBP
- Course pricing per currency
- Student currency preference
- Dynamic price display

### 4. **Course Types**
- **Recorded**: Self-paced video courses
- **Live**: Scheduled live sessions
- **Hybrid**: Combination of recorded and live

### 5. **Course Levels**
- Beginner
- Intermediate
- Advanced

### 6. **Content Types**
- Video lessons
- Text/Article lessons
- Quiz lessons
- Assignment lessons
- Interactive lessons

---

## MODELS AND DATA STRUCTURES

### Key Relationships

#### Teacher → Course
- Many-to-Many through `CourseTeacher`
- Permission-based access
- Can create/edit based on permissions

#### Student → Course
- Many-to-Many through `Enrollment`
- One enrollment per student per course
- Tracks progress and status

#### Course → Module → Lesson
- Hierarchical structure
- Modules contain lessons
- Lessons can unlock based on conditions

#### Course → Quiz
- Multiple quizzes per course
- Different quiz types (lesson, module, final, placement)
- Questions and answers structure

#### Student → AI Tutor
- One-to-Many through `TutorConversation`
- Multiple conversations per student
- Context-aware (lesson/course)

#### Student → Certificate
- One certificate per student per course
- Generated upon course completion
- QR code verification

#### Teacher → Live Classes
- One-to-Many relationship
- Scheduled sessions
- Booking system for students

#### Teacher → Student Messages
- One-to-Many relationship
- Bidirectional messaging
- Course-context aware

---

## PERMISSION SYSTEM

### Teacher Permissions
1. **View Only**: Can view course content but cannot edit
2. **Can Edit**: Can edit course, lessons, and quizzes
3. **Full Access**: Complete control including live classes and schedule management

### Course Assignment Permissions
- `can_create_live_classes`: Boolean flag
- `can_manage_schedule`: Boolean flag
- `permission_level`: View Only, Can Edit, Full Access

---

## STATUS TRACKING

### Enrollment Status
- `active`: Currently enrolled and learning
- `completed`: Course finished
- `paused`: Temporarily paused
- `expired`: Access expired

### Live Class Status
- `scheduled`: Upcoming session
- `live`: Currently in progress
- `completed`: Session finished
- `cancelled`: Session cancelled

### Booking Status
- `pending`: Awaiting confirmation
- `confirmed`: Booking confirmed
- `waitlisted`: On waitlist
- `cancelled`: Booking cancelled
- `attended`: Student attended
- `no_show`: Student didn't attend

---

## NOTES

1. **Admin Access**: Superusers and admins can access teacher views automatically (godlike admin feature)
2. **Auto-Profile Creation**: User profiles are automatically created via Django signals
3. **Streak Calculation**: Learning streaks are automatically updated on activity
4. **Progress Tracking**: Progress percentages are calculated automatically
5. **Multi-Language Support**: Platform supports multiple languages (stored in `preferred_language`)
6. **Timezone Support**: Both teachers and students can set their timezone
7. **Online Status**: Teachers' online status is tracked and updated automatically

---

## FUTURE ENHANCEMENTS (Noted in Codebase)

- Certificate templates system
- Enhanced analytics dashboard
- More detailed progress reports
- Advanced scheduling features
- Calendar integration for teachers
- Enhanced AI tutor features

---

**Document Version**: 1.0  
**Last Review**: Based on models.py and views.py analysis

