"""
Simple command to delete all courses, students, and teachers
Admin can delete any course, student, or teacher regardless of who created them
Usage: python manage.py delete_courses_students_teachers [--dry-run] [--confirm]
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import connection, transaction
from django.db.models import Q
from myApp.models import (
    Course, Module, Lesson, Quiz, Question, Answer,
    Enrollment, LessonProgress, QuizAttempt, Certificate,
    Review, CourseTeacher, CoursePricing, Category,
    Teacher, UserProfile, LiveClassSession, LiveClassBooking,
    BookingSeries, BookingSeriesItem, SessionWaitlist,
    TeacherAvailability, LiveClassTeacherAssignment,
    Payment, GiftEnrollment
)


class Command(BaseCommand):
    help = 'Delete all courses, students, and teachers (admin can delete any)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Skip confirmation prompt'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        confirm = options['confirm']
        
        self.stdout.write(self.style.WARNING('\n' + '=' * 70))
        self.stdout.write(self.style.WARNING('⚠️  DELETE COURSES, STUDENTS & TEACHERS ⚠️'))
        self.stdout.write(self.style.WARNING('=' * 70))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN MODE - No changes will be made\n'))
        
        # Count data
        courses_count = Course.objects.count()
        students = User.objects.filter(profile__role='student')
        students_count = students.count()
        teachers_model = Teacher.objects.all()
        teachers_count = teachers_model.count()
        instructors = User.objects.filter(profile__role='instructor')
        instructors_count = instructors.count()
        
        self.stdout.write(f'\n📊 Current Data:')
        self.stdout.write(f'  Courses: {courses_count}')
        self.stdout.write(f'  Students: {students_count}')
        self.stdout.write(f'  Teachers: {teachers_count}')
        self.stdout.write(f'  Instructors: {instructors_count}')
        
        total = courses_count + students_count + teachers_count + instructors_count
        
        if total == 0:
            self.stdout.write(self.style.SUCCESS('\n✓ No data to delete!'))
            return
        
        self.stdout.write(f'\n📋 Total items to delete: {total}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n🔍 DRY RUN - Nothing was deleted.'))
            self.stdout.write(self.style.WARNING('Run without --dry-run to actually delete.\n'))
            return
        
        # Confirmation
        if not confirm:
            self.stdout.write(self.style.ERROR('\n⚠️  WARNING: This will PERMANENTLY delete:'))
            self.stdout.write(self.style.ERROR(f'  - {courses_count} courses (and all related data)'))
            self.stdout.write(self.style.ERROR(f'  - {students_count} students'))
            self.stdout.write(self.style.ERROR(f'  - {teachers_count} teachers'))
            self.stdout.write(self.style.ERROR(f'  - {instructors_count} instructors'))
            self.stdout.write(self.style.ERROR('This action CANNOT be undone!\n'))
            response = input('Type "DELETE" to confirm: ')
            if response != 'DELETE':
                self.stdout.write(self.style.WARNING('Cancelled. Nothing was deleted.'))
                return
        
        # Delete everything in a transaction
        with transaction.atomic():
            try:
                self.stdout.write('\n🗑️  Starting deletion...\n')
                
                # 1. Delete all related course data first
                self.stdout.write('  [1] Deleting course-related data...')
                
                # Delete in proper order to handle foreign keys
                Answer.objects.filter(question__quiz__course__isnull=False).delete()
                Question.objects.filter(quiz__course__isnull=False).delete()
                LessonProgress.objects.filter(enrollment__course__isnull=False).delete()
                QuizAttempt.objects.filter(quiz__course__isnull=False).delete()
                Enrollment.objects.all().delete()
                Certificate.objects.all().delete()
                Review.objects.all().delete()
                CoursePricing.objects.all().delete()
                CourseTeacher.objects.all().delete()
                
                # Clear lesson unlock_quiz references
                Lesson.objects.all().update(unlock_quiz=None)
                
                # Delete lessons, quizzes, modules
                Lesson.objects.all().delete()
                Quiz.objects.all().delete()
                Module.objects.all().delete()
                
                # Delete live class related data
                try:
                    BookingSeriesItem.objects.all().delete()
                    BookingSeries.objects.all().delete()
                    SessionWaitlist.objects.all().delete()
                    LiveClassTeacherAssignment.objects.all().delete()
                    LiveClassBooking.objects.all().delete()
                    TeacherAvailability.objects.all().delete()
                    LiveClassSession.objects.all().delete()
                except Exception as e:
                    self.stdout.write(f'    (Some live class tables may not exist: {str(e)[:50]})')
                
                # Delete courses
                deleted_courses = Course.objects.all().delete()[0]
                self.stdout.write(f'    ✓ Deleted {deleted_courses} courses')
                
                # 2. Delete categories
                deleted_categories = Category.objects.all().delete()[0]
                self.stdout.write(f'  [2] Deleted {deleted_categories} categories')
                
                # 3. Delete students
                deleted_students = students.delete()[0]
                self.stdout.write(f'  [3] Deleted {deleted_students} students')
                
                # 4. Delete instructors
                deleted_instructors = instructors.delete()[0]
                self.stdout.write(f'  [4] Deleted {deleted_instructors} instructors')
                
                # 5. Delete teachers (delete Teacher model instances)
                deleted_teachers = teachers_model.delete()[0]
                self.stdout.write(f'  [5] Deleted {deleted_teachers} teachers')
                
                # 6. Clean up orphaned user profiles
                UserProfile.objects.filter(
                    Q(role='student') | Q(role='instructor') | Q(role='teacher')
                ).delete()
                
                self.stdout.write('\n' + '=' * 70)
                self.stdout.write(self.style.SUCCESS('✅ DELETION COMPLETE!'))
                self.stdout.write('=' * 70)
                self.stdout.write(f'\nDeleted:')
                self.stdout.write(f'  - {deleted_courses} courses (and all related data)')
                self.stdout.write(f'  - {deleted_categories} categories')
                self.stdout.write(f'  - {deleted_students} students')
                self.stdout.write(f'  - {deleted_instructors} instructors')
                self.stdout.write(f'  - {deleted_teachers} teachers')
                self.stdout.write(self.style.SUCCESS('\n✓ All courses, students, and teachers have been deleted.\n'))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'\n❌ ERROR: {str(e)}'))
                import traceback
                self.stdout.write(traceback.format_exc())
                raise

