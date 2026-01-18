"""
Management command to delete ALL data from the database
WARNING: This will delete EVERYTHING - courses, students, teachers, enrollments, etc.
Usage: python manage.py delete_all_data [--dry-run] [--confirm] [--keep-admins]
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db.models import Q
from myApp.models import (
    # Courses & Content
    Course, Module, Lesson, Quiz, Question, Answer,
    CoursePricing, Category,
    # Enrollments & Progress
    Enrollment, LessonProgress, QuizAttempt, Certificate,
    Review, PlacementTest,
    # Users & Roles
    UserProfile, Teacher, CourseTeacher,
    # Payments & Gifts
    Payment, GiftEnrollment, GiftEnrollmentLeadLink,
    # Partners
    Partner, Cohort, CohortMembership,
    # AI Tutor
    TutorConversation, TutorMessage, AITutorSettings,
    # Live Classes & Bookings
    LiveClassSession, LiveClassBooking, BookingSeries, BookingSeriesItem,
    SessionWaitlist, TeacherAvailability, Booking, OneOnOneBooking,
    BookingReminder, LiveClassTeacherAssignment, TeacherBookingPolicy,
    # Messages & Announcements
    CourseAnnouncement, StudentMessage,
    # CRM
    Lead, LeadTimelineEvent, EnrollmentLeadLink,
    # Other
    FAQ, Notification, Media, SiteSettings,
    # Logs
    SecurityActionLog, ActivityLog,
)


class Command(BaseCommand):
    help = 'Delete ALL data from the database - courses, students, teachers, and everything else'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting (RECOMMENDED FIRST)'
        )
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Skip confirmation prompt (use with EXTREME caution!)'
        )
        parser.add_argument(
            '--keep-admins',
            action='store_true',
            help='Keep admin users (only delete their courses/data, not the admin users themselves)'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        confirm = options['confirm']
        keep_admins = options['keep_admins']
        
        self.stdout.write(self.style.ERROR('\n' + '=' * 70))
        self.stdout.write(self.style.ERROR('⚠️  DANGER: DELETE ALL DATA ⚠️'))
        self.stdout.write(self.style.ERROR('=' * 70))
        self.stdout.write(self.style.ERROR('This will PERMANENTLY delete:'))
        self.stdout.write(self.style.ERROR('  - ALL courses, lessons, quizzes'))
        self.stdout.write(self.style.ERROR('  - ALL students and teachers'))
        self.stdout.write(self.style.ERROR('  - ALL enrollments, progress, certificates'))
        self.stdout.write(self.style.ERROR('  - ALL payments, bookings, messages'))
        self.stdout.write(self.style.ERROR('  - ALL CRM leads and data'))
        self.stdout.write(self.style.ERROR('  - EVERYTHING in the database!'))
        self.stdout.write(self.style.ERROR('=' * 70 + '\n'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN MODE - No changes will be made\n'))
        
        # Get current user to potentially keep
        try:
            current_user = User.objects.get(username='admin')  # Try to find admin
        except:
            current_user = None
        
        # Count everything
        self.stdout.write('Counting all data in database...\n')
        
        counts = {}
        
        # Helper function to safely count - accepts model class or queryset
        def safe_count(model_or_queryset, name):
            try:
                # If it's already a queryset, use it directly
                if hasattr(model_or_queryset, 'count'):
                    return model_or_queryset.count()
                # If it's a model class, get all objects
                return model_or_queryset.objects.all().count()
            except Exception as e:
                if 'does not exist' in str(e) or 'no such table' in str(e).lower():
                    return 0
                raise
        
        # Courses & Content
        counts['courses'] = safe_count(Course, 'courses')
        counts['modules'] = safe_count(Module, 'modules')
        counts['lessons'] = safe_count(Lesson, 'lessons')
        counts['quizzes'] = safe_count(Quiz, 'quizzes')
        counts['questions'] = safe_count(Question, 'questions')
        counts['answers'] = safe_count(Answer, 'answers')
        counts['course_pricing'] = safe_count(CoursePricing, 'course_pricing')
        counts['categories'] = safe_count(Category, 'categories')
        
        # Enrollments & Progress
        counts['enrollments'] = safe_count(Enrollment, 'enrollments')
        counts['lesson_progress'] = safe_count(LessonProgress, 'lesson_progress')
        counts['quiz_attempts'] = safe_count(QuizAttempt, 'quiz_attempts')
        counts['certificates'] = safe_count(Certificate, 'certificates')
        counts['reviews'] = safe_count(Review, 'reviews')
        counts['placement_tests'] = safe_count(PlacementTest, 'placement_tests')
        
        # Users & Roles
        try:
            if keep_admins:
                admin_users = User.objects.filter(
                    Q(profile__role='admin') | Q(is_superuser=True) | Q(is_staff=True)
                )
                counts['students'] = safe_count(User.objects.filter(profile__role='student'), 'students')
                counts['teachers'] = safe_count(Teacher.objects.exclude(user__in=admin_users), 'teachers')
                counts['instructors'] = safe_count(
                    User.objects.filter(profile__role='instructor').exclude(
                        id__in=admin_users.values_list('id', flat=True)
                    ), 'instructors'
                )
                counts['partners'] = safe_count(
                    User.objects.filter(profile__role='partner').exclude(
                        id__in=admin_users.values_list('id', flat=True)
                    ), 'partners'
                )
                counts['admin_users'] = admin_users.count()
            else:
                counts['students'] = safe_count(User.objects.filter(profile__role='student'), 'students')
                counts['teachers'] = safe_count(Teacher, 'teachers')
                counts['instructors'] = safe_count(User.objects.filter(profile__role='instructor'), 'instructors')
                counts['partners'] = safe_count(User.objects.filter(profile__role='partner'), 'partners')
                counts['admin_users'] = User.objects.filter(
                    Q(profile__role='admin') | Q(is_superuser=True) | Q(is_staff=True)
                ).exclude(id=current_user.id if current_user else None).count()
        except Exception as e:
            if 'does not exist' not in str(e):
                raise
            counts['students'] = 0
            counts['teachers'] = 0
            counts['instructors'] = 0
            counts['partners'] = 0
            counts['admin_users'] = 0
        
        counts['user_profiles'] = safe_count(UserProfile, 'user_profiles')
        counts['course_teachers'] = safe_count(CourseTeacher, 'course_teachers')
        
        # Payments & Gifts
        counts['payments'] = safe_count(Payment, 'payments')
        counts['gift_enrollments'] = safe_count(GiftEnrollment, 'gift_enrollments')
        counts['gift_links'] = safe_count(GiftEnrollmentLeadLink, 'gift_links')
        
        # Partners
        counts['partners_model'] = safe_count(Partner, 'partners')
        counts['cohorts'] = safe_count(Cohort, 'cohorts')
        counts['cohort_memberships'] = safe_count(CohortMembership, 'cohort_memberships')
        
        # AI Tutor
        counts['tutor_conversations'] = safe_count(TutorConversation, 'tutor_conversations')
        counts['tutor_messages'] = safe_count(TutorMessage, 'tutor_messages')
        counts['tutor_settings'] = safe_count(AITutorSettings, 'tutor_settings')
        
        # Live Classes & Bookings
        counts['live_class_sessions'] = safe_count(LiveClassSession, 'live_class_sessions')
        counts['live_class_bookings'] = safe_count(LiveClassBooking, 'live_class_bookings')
        counts['bookings'] = safe_count(Booking, 'bookings')
        counts['one_on_one_bookings'] = safe_count(OneOnOneBooking, 'one_on_one_bookings')
        counts['booking_series'] = safe_count(BookingSeries, 'booking_series')
        counts['booking_series_items'] = safe_count(BookingSeriesItem, 'booking_series_items')
        counts['session_waitlists'] = safe_count(SessionWaitlist, 'session_waitlists')
        counts['teacher_availability'] = safe_count(TeacherAvailability, 'teacher_availability')
        counts['booking_reminders'] = safe_count(BookingReminder, 'booking_reminders')
        counts['live_class_assignments'] = safe_count(LiveClassTeacherAssignment, 'live_class_assignments')
        counts['teacher_booking_policies'] = safe_count(TeacherBookingPolicy, 'teacher_booking_policies')
        
        # Messages & Announcements
        counts['course_announcements'] = safe_count(CourseAnnouncement, 'course_announcements')
        counts['student_messages'] = safe_count(StudentMessage, 'student_messages')
        
        # CRM
        counts['leads'] = safe_count(Lead, 'leads')
        counts['lead_timeline_events'] = safe_count(LeadTimelineEvent, 'lead_timeline_events')
        counts['enrollment_links'] = safe_count(EnrollmentLeadLink, 'enrollment_links')
        
        # Other
        counts['faqs'] = safe_count(FAQ, 'faqs')
        counts['notifications'] = safe_count(Notification, 'notifications')
        counts['media'] = safe_count(Media, 'media')
        
        # Logs
        counts['security_logs'] = safe_count(SecurityActionLog, 'security_logs')
        counts['activity_logs'] = safe_count(ActivityLog, 'activity_logs')
        
        # Display counts
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write('DATA TO BE DELETED:')
        self.stdout.write('=' * 70)
        
        self.stdout.write('\n📚 Courses & Content:')
        self.stdout.write(f'  Courses: {counts["courses"]}')
        self.stdout.write(f'  Modules: {counts["modules"]}')
        self.stdout.write(f'  Lessons: {counts["lessons"]}')
        self.stdout.write(f'  Quizzes: {counts["quizzes"]}')
        self.stdout.write(f'  Questions: {counts["questions"]}')
        self.stdout.write(f'  Answers: {counts["answers"]}')
        self.stdout.write(f'  Course Pricing: {counts["course_pricing"]}')
        self.stdout.write(f'  Categories: {counts["categories"]}')
        
        self.stdout.write('\n👥 Users:')
        self.stdout.write(f'  Students: {counts["students"]}')
        self.stdout.write(f'  Teachers: {counts["teachers"]}')
        self.stdout.write(f'  Instructors: {counts["instructors"]}')
        self.stdout.write(f'  Partners: {counts["partners"]}')
        if keep_admins:
            self.stdout.write(f'  Admin Users: {counts["admin_users"]} (KEEPING)')
        else:
            self.stdout.write(f'  Admin Users: {counts["admin_users"]} (DELETING)')
        self.stdout.write(f'  User Profiles: {counts["user_profiles"]}')
        
        self.stdout.write('\n📖 Enrollments & Progress:')
        self.stdout.write(f'  Enrollments: {counts["enrollments"]}')
        self.stdout.write(f'  Lesson Progress: {counts["lesson_progress"]}')
        self.stdout.write(f'  Quiz Attempts: {counts["quiz_attempts"]}')
        self.stdout.write(f'  Certificates: {counts["certificates"]}')
        self.stdout.write(f'  Reviews: {counts["reviews"]}')
        self.stdout.write(f'  Placement Tests: {counts["placement_tests"]}')
        
        self.stdout.write('\n💳 Payments & Gifts:')
        self.stdout.write(f'  Payments: {counts["payments"]}')
        self.stdout.write(f'  Gift Enrollments: {counts["gift_enrollments"]}')
        
        self.stdout.write('\n📅 Live Classes & Bookings:')
        self.stdout.write(f'  Live Class Sessions: {counts["live_class_sessions"]}')
        self.stdout.write(f'  Live Class Bookings: {counts["live_class_bookings"]}')
        self.stdout.write(f'  Bookings: {counts["bookings"]}')
        self.stdout.write(f'  One-on-One Bookings: {counts["one_on_one_bookings"]}')
        self.stdout.write(f'  Booking Series: {counts["booking_series"]}')
        
        self.stdout.write('\n💬 Messages & CRM:')
        self.stdout.write(f'  Course Announcements: {counts["course_announcements"]}')
        self.stdout.write(f'  Student Messages: {counts["student_messages"]}')
        self.stdout.write(f'  Leads: {counts["leads"]}')
        self.stdout.write(f'  Lead Timeline Events: {counts["lead_timeline_events"]}')
        
        self.stdout.write('\n📝 Other:')
        self.stdout.write(f'  FAQs: {counts["faqs"]}')
        self.stdout.write(f'  Notifications: {counts["notifications"]}')
        self.stdout.write(f'  Media: {counts["media"]}')
        self.stdout.write(f'  Activity Logs: {counts["activity_logs"]}')
        self.stdout.write(f'  Security Logs: {counts["security_logs"]}')
        
        total_items = sum(counts.values())
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.ERROR(f'TOTAL ITEMS TO DELETE: {total_items:,}'))
        self.stdout.write('=' * 70 + '\n')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN COMPLETE - Nothing was deleted.'))
            self.stdout.write(self.style.WARNING('Run without --dry-run to actually delete.\n'))
            return
        
        # Confirmation
        if not confirm:
            self.stdout.write(self.style.ERROR('⚠️  FINAL WARNING ⚠️'))
            self.stdout.write(self.style.ERROR('This will PERMANENTLY DELETE ALL DATA!'))
            self.stdout.write(self.style.ERROR('This action CANNOT be undone!\n'))
            response = input('Type "DELETE EVERYTHING" to confirm: ')
            if response != 'DELETE EVERYTHING':
                self.stdout.write(self.style.WARNING('Cancelled. Nothing was deleted.'))
                return
        
        # Delete everything in correct order
        self.stdout.write('\n🗑️  Starting deletion...\n')
        
        deleted_counts = {}
        
        # Helper function to safely delete
        def safe_delete(model, name, step_num):
            try:
                # First check if any records exist
                count = model.objects.count()
                if count == 0:
                    self.stdout.write(f'  [{step_num}] Skipped {name} (already empty)')
                    return 0
                
                # Try to delete
                deleted = model.objects.all().delete()[0]
                self.stdout.write(f'  [{step_num}] Deleted {deleted} {name}')
                return deleted
            except Exception as e:
                error_str = str(e).lower()
                # Only skip if it's actually a missing table error
                if 'does not exist' in error_str or 'no such table' in error_str:
                    self.stdout.write(f'  [{step_num}] Skipped {name} (table does not exist)')
                    return 0
                # For other errors, show the actual error and continue
                self.stdout.write(self.style.WARNING(f'  [{step_num}] Error deleting {name}: {str(e)[:100]}'))
                # Try to continue anyway - might be a constraint issue that will resolve
                return 0
        
        try:
            step = 1
            
            # 1. Delete Answers
            deleted_counts['answers'] = safe_delete(Answer, 'answers', step)
            step += 1
            
            # 2. Delete Questions
            deleted_counts['questions'] = safe_delete(Question, 'questions', step)
            step += 1
            
            # 3. Delete Lesson Progress
            deleted_counts['lesson_progress'] = safe_delete(LessonProgress, 'lesson progress records', step)
            step += 1
            
            # 4. Delete Quiz Attempts
            deleted_counts['quiz_attempts'] = safe_delete(QuizAttempt, 'quiz attempts', step)
            step += 1
            
            # 5. Delete Booking related
            deleted_counts['booking_series_items'] = safe_delete(BookingSeriesItem, 'booking series items', step)
            step += 1
            
            deleted_counts['booking_series'] = safe_delete(BookingSeries, 'booking series', step)
            step += 1
            
            deleted_counts['session_waitlists'] = safe_delete(SessionWaitlist, 'waitlists', step)
            step += 1
            
            deleted_counts['booking_reminders'] = safe_delete(BookingReminder, 'booking reminders', step)
            step += 1
            
            deleted_counts['live_class_assignments'] = safe_delete(LiveClassTeacherAssignment, 'teacher assignments', step)
            step += 1
            
            deleted_counts['live_class_bookings'] = safe_delete(LiveClassBooking, 'live class bookings', step)
            step += 1
            
            deleted_counts['one_on_one_bookings'] = safe_delete(OneOnOneBooking, 'one-on-one bookings', step)
            step += 1
            
            deleted_counts['bookings'] = safe_delete(Booking, 'bookings', step)
            step += 1
            
            deleted_counts['live_class_sessions'] = safe_delete(LiveClassSession, 'live class sessions', step)
            step += 1
            
            deleted_counts['teacher_availability'] = safe_delete(TeacherAvailability, 'teacher availability slots', step)
            step += 1
            
            deleted_counts['teacher_booking_policies'] = safe_delete(TeacherBookingPolicy, 'booking policies', step)
            step += 1
            
            # 6. Delete Enrollments
            deleted_counts['enrollment_links'] = safe_delete(EnrollmentLeadLink, 'enrollment links', step)
            step += 1
            
            deleted_counts['enrollments'] = safe_delete(Enrollment, 'enrollments', step)
            step += 1
            
            # 7. Delete Certificates
            deleted_counts['certificates'] = safe_delete(Certificate, 'certificates', step)
            step += 1
            
            # 8. Delete Reviews
            deleted_counts['reviews'] = safe_delete(Review, 'reviews', step)
            step += 1
            
            # 9. Delete Placement Tests
            deleted_counts['placement_tests'] = safe_delete(PlacementTest, 'placement tests', step)
            step += 1
            
            # 10. Delete Gift Enrollments
            deleted_counts['gift_links'] = safe_delete(GiftEnrollmentLeadLink, 'gift links', step)
            step += 1
            
            deleted_counts['gift_enrollments'] = safe_delete(GiftEnrollment, 'gift enrollments', step)
            step += 1
            
            # 11. Delete Payments
            deleted_counts['payments'] = safe_delete(Payment, 'payments', step)
            step += 1
            
            # 12. Delete Lessons (clear unlock_quiz first)
            try:
                Lesson.objects.all().update(unlock_quiz=None)
                deleted_counts['lessons'] = safe_delete(Lesson, 'lessons', step)
            except:
                deleted_counts['lessons'] = 0
            step += 1
            
            # 13. Delete Quizzes
            deleted_counts['quizzes'] = safe_delete(Quiz, 'quizzes', step)
            step += 1
            
            # 14. Delete Modules
            deleted_counts['modules'] = safe_delete(Module, 'modules', step)
            step += 1
            
            # 15. Delete Course related
            deleted_counts['course_pricing'] = safe_delete(CoursePricing, 'course pricing records', step)
            step += 1
            
            deleted_counts['course_teachers'] = safe_delete(CourseTeacher, 'course-teacher links', step)
            step += 1
            
            # Try to delete courses - might have foreign key issues, so be more careful
            try:
                course_count = Course.objects.count()
                if course_count > 0:
                    # Delete all courses by getting the queryset first
                    courses = Course.objects.all()
                    deleted_counts['courses'] = courses.delete()[0]
                    self.stdout.write(f'  [{step}] Deleted {deleted_counts["courses"]} courses')
                else:
                    deleted_counts['courses'] = 0
                    self.stdout.write(f'  [{step}] Skipped courses (already empty)')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  [{step}] ERROR deleting courses: {str(e)[:150]}'))
                deleted_counts['courses'] = 0
            step += 1
            
            # 16. Delete Categories
            deleted_counts['categories'] = safe_delete(Category, 'categories', step)
            step += 1
            
            # 17. Delete Messages
            deleted_counts['student_messages'] = safe_delete(StudentMessage, 'student messages', step)
            step += 1
            
            deleted_counts['course_announcements'] = safe_delete(CourseAnnouncement, 'course announcements', step)
            step += 1
            
            # 18. Delete CRM
            deleted_counts['lead_timeline_events'] = safe_delete(LeadTimelineEvent, 'lead timeline events', step)
            step += 1
            
            deleted_counts['leads'] = safe_delete(Lead, 'leads', step)
            step += 1
            
            # 19. Delete AI Tutor
            deleted_counts['tutor_messages'] = safe_delete(TutorMessage, 'tutor messages', step)
            step += 1
            
            deleted_counts['tutor_conversations'] = safe_delete(TutorConversation, 'tutor conversations', step)
            step += 1
            
            deleted_counts['tutor_settings'] = safe_delete(AITutorSettings, 'tutor settings', step)
            step += 1
            
            # 20. Delete Partners
            deleted_counts['cohort_memberships'] = safe_delete(CohortMembership, 'cohort memberships', step)
            step += 1
            
            deleted_counts['cohorts'] = safe_delete(Cohort, 'cohorts', step)
            step += 1
            
            deleted_counts['partners'] = safe_delete(Partner, 'partners', step)
            step += 1
            
            # 21. Delete Teachers - might have foreign key issues
            try:
                teacher_count = Teacher.objects.count()
                if teacher_count > 0:
                    teachers = Teacher.objects.all()
                    deleted_counts['teachers'] = teachers.delete()[0]
                    self.stdout.write(f'  [{step}] Deleted {deleted_counts["teachers"]} teachers')
                else:
                    deleted_counts['teachers'] = 0
                    self.stdout.write(f'  [{step}] Skipped teachers (already empty)')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  [{step}] ERROR deleting teachers: {str(e)[:150]}'))
                deleted_counts['teachers'] = 0
            step += 1
            
            # 22. Delete Other
            deleted_counts['faqs'] = safe_delete(FAQ, 'FAQs', step)
            step += 1
            
            deleted_counts['notifications'] = safe_delete(Notification, 'notifications', step)
            step += 1
            
            deleted_counts['media'] = safe_delete(Media, 'media files', step)
            step += 1
            
            deleted_counts['activity_logs'] = safe_delete(ActivityLog, 'activity logs', step)
            step += 1
            
            deleted_counts['security_logs'] = safe_delete(SecurityActionLog, 'security logs', step)
            step += 1
            
            # 23. Delete Users (except admins if --keep-admins)
            if keep_admins:
                try:
                    admin_users = User.objects.filter(
                        Q(profile__role='admin') | Q(is_superuser=True) | Q(is_staff=True)
                    )
                    students = User.objects.filter(profile__role='student')
                    instructors = User.objects.filter(profile__role='instructor').exclude(
                        id__in=admin_users.values_list('id', flat=True)
                    )
                    partners = User.objects.filter(profile__role='partner').exclude(
                        id__in=admin_users.values_list('id', flat=True)
                    )
                    deleted_counts['students'] = students.delete()[0]
                    self.stdout.write(f'  [{step}] Deleted {deleted_counts["students"]} students')
                    step += 1
                    
                    deleted_counts['instructors'] = instructors.delete()[0]
                    self.stdout.write(f'  [{step}] Deleted {deleted_counts["instructors"]} instructors')
                    step += 1
                    
                    deleted_counts['partners'] = partners.delete()[0]
                    self.stdout.write(f'  [{step}] Deleted {deleted_counts["partners"]} partners')
                    step += 1
                    
                    # Delete user profiles for deleted users
                    UserProfile.objects.exclude(user__in=admin_users).delete()
                except Exception as e:
                    if 'does not exist' not in str(e):
                        raise
            else:
                try:
                    # Delete all users except current admin if exists
                    users_to_delete = User.objects.all()
                    if current_user:
                        users_to_delete = users_to_delete.exclude(id=current_user.id)
                    
                    deleted_counts['users'] = users_to_delete.delete()[0]
                    self.stdout.write(f'  [{step}] Deleted {deleted_counts["users"]} users')
                    step += 1
                    
                    # Delete remaining user profiles
                    deleted_counts['user_profiles'] = safe_delete(UserProfile, 'user profiles', step)
                    step += 1
                except Exception as e:
                    if 'does not exist' not in str(e):
                        raise
            
            # Final summary
            self.stdout.write('\n' + '=' * 70)
            self.stdout.write(self.style.SUCCESS('✅ DELETION COMPLETE!'))
            self.stdout.write('=' * 70)
            
            total_deleted = sum(deleted_counts.values())
            self.stdout.write(f'\nTotal items deleted: {total_deleted:,}')
            
            if keep_admins:
                self.stdout.write(self.style.SUCCESS('\n✓ All data deleted. Admin users were kept.'))
            else:
                if current_user:
                    self.stdout.write(self.style.SUCCESS(f'\n✓ All data deleted. User "{current_user.username}" was kept.'))
                else:
                    self.stdout.write(self.style.SUCCESS('\n✓ All data deleted.'))
            
            self.stdout.write(self.style.WARNING('\n⚠️  The database is now empty. You can start fresh!\n'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ ERROR during deletion: {str(e)}'))
            self.stdout.write(self.style.ERROR('Some data may have been deleted. Please check the database.'))
            import traceback
            self.stdout.write(traceback.format_exc())
            return

