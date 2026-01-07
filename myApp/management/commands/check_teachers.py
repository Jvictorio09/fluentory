from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from myApp.models import Teacher


class Command(BaseCommand):
    help = 'Check teacher profiles in the database'

    def handle(self, *args, **options):
        self.stdout.write('\n=== TEACHER PROFILES IN DATABASE ===\n')
        
        # Count teachers
        teacher_count = Teacher.objects.count()
        self.stdout.write(f'Total Teacher Profiles: {teacher_count}\n')
        
        if teacher_count > 0:
            self.stdout.write('Teacher Details:')
            self.stdout.write('-' * 80)
            for teacher in Teacher.objects.all().select_related('user'):
                self.stdout.write(
                    f"ID: {teacher.id} | "
                    f"User: {teacher.user.username} ({teacher.user.email}) | "
                    f"Permission: {teacher.permission_level} | "
                    f"Approved: {teacher.is_approved} | "
                    f"Online: {teacher.is_online}"
                )
        else:
            self.stdout.write(self.style.WARNING('No teacher profiles found in database.'))
        
        # Check users with instructor role but no teacher profile
        self.stdout.write('\n=== USERS WITH INSTRUCTOR ROLE BUT NO TEACHER PROFILE ===\n')
        from myApp.models import UserProfile
        instructor_users = User.objects.filter(profile__role='instructor')
        users_without_teacher = [u for u in instructor_users if not hasattr(u, 'teacher_profile')]
        
        if users_without_teacher:
            self.stdout.write(f'Found {len(users_without_teacher)} users with instructor role but no teacher profile:')
            for user in users_without_teacher:
                self.stdout.write(f"  - {user.username} ({user.email})")
        else:
            self.stdout.write('All instructor users have teacher profiles.')
        
        # Check all users
        self.stdout.write('\n=== ALL USERS ===\n')
        total_users = User.objects.count()
        self.stdout.write(f'Total Users: {total_users}')
        
        self.stdout.write('\nDone!')

