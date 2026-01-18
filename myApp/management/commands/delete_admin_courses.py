"""
Management command to delete all courses created by admin users and their related data
Usage: python manage.py delete_admin_courses [--dry-run] [--confirm]
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db.models import Q
from myApp.models import (
    Course, Module, Lesson, Quiz, Question, Answer,
    Enrollment, LessonProgress, QuizAttempt, Certificate,
    Review, CourseTeacher, CoursePricing
)


class Command(BaseCommand):
    help = 'Delete all courses created by admin users and all related data (lessons, quizzes, enrollments, etc.)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting (recommended first)'
        )
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Skip confirmation prompt (use with caution!)'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        confirm = options['confirm']
        
        self.stdout.write(self.style.WARNING('\n=== DELETE ADMIN COURSES ===\n'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made\n'))
        
        # Find admin users
        admin_users = User.objects.filter(
            Q(profile__role='admin') | 
            Q(is_superuser=True) |
            Q(is_staff=True)
        ).distinct()
        
        if not admin_users.exists():
            self.stdout.write(self.style.ERROR('No admin users found!'))
            return
        
        self.stdout.write(f'Found {admin_users.count()} admin user(s):')
        for admin in admin_users:
            self.stdout.write(f'  - {admin.username} ({admin.email or "No email"})')
        
        # Find courses created by admin users
        # Check both instructor field and courses created by admin
        admin_courses = Course.objects.filter(
            Q(instructor__in=admin_users) |
            Q(course_teachers__teacher__user__in=admin_users)
        ).distinct()
        
        # Also get courses where admin is the instructor
        courses_count = admin_courses.count()
        
        if courses_count == 0:
            self.stdout.write(self.style.SUCCESS('\nNo courses found for admin users.'))
            return
        
        self.stdout.write(f'\nFound {courses_count} course(s) to delete:')
        for course in admin_courses:
            instructor_name = course.instructor.username if course.instructor else 'No instructor'
            self.stdout.write(f'  - {course.title} (Instructor: {instructor_name}, Status: {course.status})')
        
        # Count related data
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write('Related data to be deleted:')
        self.stdout.write('=' * 60)
        
        # Count related objects
        modules_count = Module.objects.filter(course__in=admin_courses).count()
        lessons_count = Lesson.objects.filter(module__course__in=admin_courses).count()
        quizzes_count = Quiz.objects.filter(
            Q(course__in=admin_courses) | 
            Q(module__course__in=admin_courses) | 
            Q(lesson__module__course__in=admin_courses)
        ).distinct().count()
        questions_count = Question.objects.filter(
            quiz__course__in=admin_courses
        ).distinct().count()
        answers_count = Answer.objects.filter(
            question__quiz__course__in=admin_courses
        ).distinct().count()
        enrollments_count = Enrollment.objects.filter(course__in=admin_courses).count()
        lesson_progress_count = LessonProgress.objects.filter(
            enrollment__course__in=admin_courses
        ).count()
        quiz_attempts_count = QuizAttempt.objects.filter(
            quiz__course__in=admin_courses
        ).distinct().count()
        certificates_count = Certificate.objects.filter(course__in=admin_courses).count()
        reviews_count = Review.objects.filter(course__in=admin_courses).count()
        course_teachers_count = CourseTeacher.objects.filter(course__in=admin_courses).count()
        course_pricing_count = CoursePricing.objects.filter(course__in=admin_courses).count()
        
        self.stdout.write(f'  Courses: {courses_count}')
        self.stdout.write(f'  Modules: {modules_count}')
        self.stdout.write(f'  Lessons: {lessons_count}')
        self.stdout.write(f'  Quizzes: {quizzes_count}')
        self.stdout.write(f'  Questions: {questions_count}')
        self.stdout.write(f'  Answers: {answers_count}')
        self.stdout.write(f'  Enrollments: {enrollments_count}')
        self.stdout.write(f'  Lesson Progress: {lesson_progress_count}')
        self.stdout.write(f'  Quiz Attempts: {quiz_attempts_count}')
        self.stdout.write(f'  Certificates: {certificates_count}')
        self.stdout.write(f'  Reviews: {reviews_count}')
        self.stdout.write(f'  Course-Teacher Links: {course_teachers_count}')
        self.stdout.write(f'  Course Pricing: {course_pricing_count}')
        
        total_items = (courses_count + modules_count + lessons_count + quizzes_count + 
                      questions_count + answers_count + enrollments_count + 
                      lesson_progress_count + quiz_attempts_count + certificates_count + 
                      reviews_count + course_teachers_count + course_pricing_count)
        
        self.stdout.write(f'\nTotal items to delete: {total_items}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\nDRY RUN - Nothing was deleted. Run without --dry-run to delete.'))
            return
        
        # Confirmation
        if not confirm:
            self.stdout.write(self.style.ERROR('\n⚠️  WARNING: This will PERMANENTLY delete all data listed above!'))
            self.stdout.write(self.style.ERROR('This action CANNOT be undone!\n'))
            response = input('Type "DELETE" to confirm: ')
            if response != 'DELETE':
                self.stdout.write(self.style.WARNING('Cancelled. Nothing was deleted.'))
                return
        
        # Delete in correct order to avoid foreign key issues
        self.stdout.write('\nDeleting...')
        
        deleted_counts = {
            'answers': 0,
            'questions': 0,
            'lesson_progress': 0,
            'quiz_attempts': 0,
            'enrollments': 0,
            'certificates': 0,
            'reviews': 0,
            'course_teachers': 0,
            'lessons': 0,
            'quizzes': 0,
            'modules': 0,
            'course_pricing': 0,
            'courses': 0,
        }
        
        try:
            # 1. Delete Answers (depends on Questions)
            answers = Answer.objects.filter(question__quiz__course__in=admin_courses)
            deleted_counts['answers'] = answers.count()
            answers.delete()
            self.stdout.write(f'  [1/13] Deleted {deleted_counts["answers"]} answers')
            
            # 2. Delete Questions (depends on Quiz)
            questions = Question.objects.filter(quiz__course__in=admin_courses)
            deleted_counts['questions'] = questions.count()
            questions.delete()
            self.stdout.write(f'  [2/13] Deleted {deleted_counts["questions"]} questions')
            
            # 3. Delete LessonProgress (depends on Enrollment and Lesson)
            lesson_progress = LessonProgress.objects.filter(enrollment__course__in=admin_courses)
            deleted_counts['lesson_progress'] = lesson_progress.count()
            lesson_progress.delete()
            self.stdout.write(f'  [3/13] Deleted {deleted_counts["lesson_progress"]} lesson progress records')
            
            # 4. Delete QuizAttempts (depends on Quiz and User)
            quiz_attempts = QuizAttempt.objects.filter(quiz__course__in=admin_courses)
            deleted_counts['quiz_attempts'] = quiz_attempts.count()
            quiz_attempts.delete()
            self.stdout.write(f'  [4/13] Deleted {deleted_counts["quiz_attempts"]} quiz attempts')
            
            # 5. Delete Enrollments (depends on Course)
            enrollments = Enrollment.objects.filter(course__in=admin_courses)
            deleted_counts['enrollments'] = enrollments.count()
            enrollments.delete()
            self.stdout.write(f'  [5/13] Deleted {deleted_counts["enrollments"]} enrollments')
            
            # 6. Delete Certificates (depends on Course)
            certificates = Certificate.objects.filter(course__in=admin_courses)
            deleted_counts['certificates'] = certificates.count()
            certificates.delete()
            self.stdout.write(f'  [6/13] Deleted {deleted_counts["certificates"]} certificates')
            
            # 7. Delete Reviews (depends on Course)
            reviews = Review.objects.filter(course__in=admin_courses)
            deleted_counts['reviews'] = reviews.count()
            reviews.delete()
            self.stdout.write(f'  [7/13] Deleted {deleted_counts["reviews"]} reviews')
            
            # 8. Delete CourseTeacher links (depends on Course)
            course_teachers = CourseTeacher.objects.filter(course__in=admin_courses)
            deleted_counts['course_teachers'] = course_teachers.count()
            course_teachers.delete()
            self.stdout.write(f'  [8/13] Deleted {deleted_counts["course_teachers"]} course-teacher links')
            
            # 9. Delete Lessons (depends on Module) - unlock_quiz is SET_NULL so safe
            lessons = Lesson.objects.filter(module__course__in=admin_courses)
            deleted_counts['lessons'] = lessons.count()
            lessons.update(unlock_quiz=None)  # Clear foreign key first
            lessons.delete()
            self.stdout.write(f'  [9/13] Deleted {deleted_counts["lessons"]} lessons')
            
            # 10. Delete Quizzes (depends on Course/Module/Lesson)
            quizzes = Quiz.objects.filter(
                Q(course__in=admin_courses) | 
                Q(module__course__in=admin_courses) | 
                Q(lesson__module__course__in=admin_courses)
            ).distinct()
            deleted_counts['quizzes'] = quizzes.count()
            quizzes.delete()
            self.stdout.write(f'  [10/13] Deleted {deleted_counts["quizzes"]} quizzes')
            
            # 11. Delete Modules (depends on Course)
            modules = Module.objects.filter(course__in=admin_courses)
            deleted_counts['modules'] = modules.count()
            modules.delete()
            self.stdout.write(f'  [11/13] Deleted {deleted_counts["modules"]} modules')
            
            # 12. Delete CoursePricing (depends on Course)
            course_pricing = CoursePricing.objects.filter(course__in=admin_courses)
            deleted_counts['course_pricing'] = course_pricing.count()
            course_pricing.delete()
            self.stdout.write(f'  [12/13] Deleted {deleted_counts["course_pricing"]} course pricing records')
            
            # 13. Delete Courses (last)
            deleted_counts['courses'] = admin_courses.count()
            course_titles = [c.title for c in admin_courses]
            admin_courses.delete()
            self.stdout.write(f'  [13/13] Deleted {deleted_counts["courses"]} courses')
            
            # Summary
            self.stdout.write('\n' + '=' * 60)
            self.stdout.write(self.style.SUCCESS('DELETION COMPLETE!'))
            self.stdout.write('=' * 60)
            
            total_deleted = sum(deleted_counts.values())
            self.stdout.write(f'\nTotal items deleted: {total_deleted}')
            self.stdout.write('\nDeleted courses:')
            for title in course_titles:
                self.stdout.write(f'  - {title}')
            
            self.stdout.write(self.style.SUCCESS('\n✓ All admin courses and related data have been deleted.\n'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\nERROR during deletion: {str(e)}'))
            self.stdout.write(self.style.ERROR('Some data may have been deleted. Please check the database.'))
            import traceback
            self.stdout.write(traceback.format_exc())
            return

