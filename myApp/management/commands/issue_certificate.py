"""
Django management command to issue certificates
Usage: python manage.py issue_certificate <user_id> <course_id>
       python manage.py issue_certificate --all  # Issue for all completed enrollments
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from myApp.models import Certificate, Course, Enrollment
from myApp.utils.certificate_utils import create_certificate

User = get_user_model()


class Command(BaseCommand):
    help = 'Issue a certificate to a user for completing a course'

    def add_arguments(self, parser):
        parser.add_argument('user_id', nargs='?', type=int, help='User ID')
        parser.add_argument('course_id', nargs='?', type=int, help='Course ID')
        parser.add_argument(
            '--all',
            action='store_true',
            help='Issue certificates for all completed enrollments',
        )
        parser.add_argument(
            '--enrollment-id',
            type=int,
            help='Issue certificate for a specific enrollment ID',
        )

    def handle(self, *args, **options):
        if options['all']:
            # Issue certificates for all completed enrollments
            enrollments = Enrollment.objects.filter(
                status='completed',
                course__has_certificate=True
            ).select_related('user', 'course')
            
            count = 0
            for enrollment in enrollments:
                # Check if certificate already exists
                if not Certificate.objects.filter(user=enrollment.user, course=enrollment.course).exists():
                    try:
                        certificate = create_certificate(
                            user=enrollment.user,
                            course=enrollment.course,
                            enrollment=enrollment
                        )
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'✓ Issued certificate to {enrollment.user.username} for {enrollment.course.title}'
                            )
                        )
                        count += 1
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(
                                f'✗ Failed to issue certificate to {enrollment.user.username} for {enrollment.course.title}: {e}'
                            )
                        )
            
            self.stdout.write(
                self.style.SUCCESS(f'\n✅ Issued {count} certificate(s)')
            )
        
        elif options['enrollment_id']:
            # Issue certificate for specific enrollment
            try:
                enrollment = Enrollment.objects.get(id=options['enrollment_id'])
                if enrollment.status != 'completed':
                    raise CommandError(f'Enrollment {enrollment.id} is not completed')
                if not enrollment.course.has_certificate:
                    raise CommandError(f'Course {enrollment.course.title} does not have certificates enabled')
                
                certificate = create_certificate(
                    user=enrollment.user,
                    course=enrollment.course,
                    enrollment=enrollment
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ Issued certificate to {enrollment.user.username} for {enrollment.course.title}'
                    )
                )
            except Enrollment.DoesNotExist:
                raise CommandError(f'Enrollment {options["enrollment_id"]} does not exist')
        
        elif options['user_id'] and options['course_id']:
            # Issue certificate for specific user and course
            try:
                user = User.objects.get(id=options['user_id'])
                course = Course.objects.get(id=options['course_id'])
                
                if not course.has_certificate:
                    raise CommandError(f'Course {course.title} does not have certificates enabled')
                
                # Check if enrollment exists
                enrollment = Enrollment.objects.filter(user=user, course=course).first()
                
                certificate = create_certificate(
                    user=user,
                    course=course,
                    enrollment=enrollment
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ Issued certificate to {user.username} for {course.title}'
                    )
                )
            except User.DoesNotExist:
                raise CommandError(f'User {options["user_id"]} does not exist')
            except Course.DoesNotExist:
                raise CommandError(f'Course {options["course_id"]} does not exist')
        else:
            raise CommandError('You must provide either user_id and course_id, --enrollment-id, or --all')

