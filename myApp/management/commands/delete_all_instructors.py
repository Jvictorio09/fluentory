from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import connection
from myApp.models import Teacher, UserProfile, CourseTeacher


class Command(BaseCommand):
    help = 'Delete all instructors from the database (users with instructor role and their Teacher profiles)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )
        parser.add_argument(
            '--yes',
            action='store_true',
            help='Skip confirmation prompt',
        )
        parser.add_argument(
            '--keep-teachers',
            action='store_true',
            help='Keep Teacher model instances, only delete User records',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        skip_confirm = options['yes']
        keep_teachers = options['keep_teachers']
        
        # Find all instructors
        instructor_users = User.objects.filter(profile__role='instructor')
        instructor_count = instructor_users.count()
        
        # Also find users without profiles that might be instructors
        users_without_profile = User.objects.filter(profile__isnull=True)
        
        self.stdout.write('\n=== DELETE ALL INSTRUCTORS ===\n')
        self.stdout.write(f'Found {instructor_count} user(s) with instructor role')
        
        if instructor_count == 0:
            self.stdout.write(self.style.WARNING('No instructors found in the database.'))
            return
        
        # Show details
        self.stdout.write('\nInstructors to be deleted:')
        self.stdout.write('-' * 80)
        for user in instructor_users.select_related('profile'):
            teacher_info = ''
            try:
                if hasattr(user, 'teacher_profile'):
                    teacher_info = f' (Has Teacher profile: ID {user.teacher_profile.id})'
            except:
                pass
            
            self.stdout.write(
                f"  - User ID {user.id}: {user.username} ({user.email}){teacher_info}"
            )
        
        # Count Teacher profiles
        teacher_count = Teacher.objects.count()
        if teacher_count > 0:
            self.stdout.write(f'\nFound {teacher_count} Teacher profile(s) in database')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n=== DRY RUN MODE - No changes will be made ==='))
            self.stdout.write(f'Would delete: {instructor_count} instructor user(s)')
            if not keep_teachers and teacher_count > 0:
                self.stdout.write(f'Would delete: {teacher_count} Teacher profile(s)')
            return
        
        # Confirmation
        if not skip_confirm:
            self.stdout.write(self.style.WARNING('\n⚠️  WARNING: This will permanently delete:'))
            self.stdout.write(f'  - {instructor_count} instructor user(s)')
            if not keep_teachers and teacher_count > 0:
                self.stdout.write(f'  - {teacher_count} Teacher profile(s)')
            self.stdout.write('  - All related data (courses they created, etc.)')
            
            confirm = input('\nAre you sure you want to delete ALL instructors? (yes/no): ')
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.WARNING('Deletion cancelled.'))
                return
        
        # Delete related data first
        deleted_counts = {
            'course_teachers': 0,
            'teachers': 0,
            'users': 0,
        }
        
        try:
            # 1. Delete CourseTeacher relationships
            course_teachers = CourseTeacher.objects.filter(teacher__user__profile__role='instructor')
            deleted_counts['course_teachers'] = course_teachers.delete()[0]
            self.stdout.write(f'\n[1] Deleted {deleted_counts["course_teachers"]} CourseTeacher relationship(s)')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  Error deleting CourseTeacher: {str(e)[:100]}'))
        
        # 2. Delete Teacher profiles (if not keeping them)
        if not keep_teachers:
            try:
                # Get teacher IDs before deletion
                teacher_ids = list(Teacher.objects.values_list('id', flat=True))
                
                # Delete using raw SQL to avoid ORM relationship checks
                if teacher_ids:
                    with connection.cursor() as cursor:
                        if 'postgresql' in connection.vendor:
                            cursor.execute("DELETE FROM myApp_teacher WHERE id = ANY(%s)", [teacher_ids])
                        else:
                            placeholders = ','.join(['?' if 'sqlite' in connection.vendor.lower() else '%s'] * len(teacher_ids))
                            cursor.execute(f"DELETE FROM myApp_teacher WHERE id IN ({placeholders})", teacher_ids)
                    deleted_counts['teachers'] = cursor.rowcount if hasattr(cursor, 'rowcount') else len(teacher_ids)
                    self.stdout.write(f'[2] Deleted {deleted_counts["teachers"]} Teacher profile(s)')
                else:
                    self.stdout.write('[2] No Teacher profiles to delete')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  Error deleting Teacher profiles: {str(e)[:100]}'))
                # Fallback: try ORM deletion
                try:
                    deleted_counts['teachers'] = Teacher.objects.all().delete()[0]
                    self.stdout.write(f'[2] Deleted {deleted_counts["teachers"]} Teacher profile(s) (fallback method)')
                except Exception as e2:
                    self.stdout.write(self.style.ERROR(f'  Fallback deletion also failed: {str(e2)[:100]}'))
        else:
            self.stdout.write('[2] Skipping Teacher profile deletion (--keep-teachers flag set)')
        
        # 3. Delete UserProfile records for instructors
        try:
            instructor_profiles = UserProfile.objects.filter(role='instructor')
            deleted_counts['profiles'] = instructor_profiles.delete()[0]
            self.stdout.write(f'[3] Deleted {deleted_counts["profiles"]} UserProfile record(s)')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  Error deleting UserProfile: {str(e)[:100]}'))
        
        # 4. Delete User records
        try:
            # Get user IDs before deletion
            user_ids = list(instructor_users.values_list('id', flat=True))
            
            # Delete using raw SQL to avoid ORM relationship checks
            if user_ids:
                with connection.cursor() as cursor:
                    if 'postgresql' in connection.vendor:
                        cursor.execute("DELETE FROM auth_user WHERE id = ANY(%s)", [user_ids])
                    else:
                        placeholders = ','.join(['?' if 'sqlite' in connection.vendor.lower() else '%s'] * len(user_ids))
                        cursor.execute(f"DELETE FROM auth_user WHERE id IN ({placeholders})", user_ids)
                deleted_counts['users'] = cursor.rowcount if hasattr(cursor, 'rowcount') else len(user_ids)
                self.stdout.write(f'[4] Deleted {deleted_counts["users"]} instructor user(s)')
            else:
                self.stdout.write('[4] No users to delete')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  Error deleting users: {str(e)[:100]}'))
            # Fallback: try ORM deletion
            try:
                deleted_counts['users'] = instructor_users.delete()[0]
                self.stdout.write(f'[4] Deleted {deleted_counts["users"]} instructor user(s) (fallback method)')
            except Exception as e2:
                self.stdout.write(self.style.ERROR(f'  Fallback deletion also failed: {str(e2)[:100]}'))
        
        # Summary
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write(self.style.SUCCESS('DELETION SUMMARY:'))
        self.stdout.write(f'  CourseTeacher relationships: {deleted_counts["course_teachers"]}')
        if not keep_teachers:
            self.stdout.write(f'  Teacher profiles: {deleted_counts["teachers"]}')
        self.stdout.write(f'  Instructor users: {deleted_counts["users"]}')
        self.stdout.write('=' * 80)
        
        # Verify
        remaining = User.objects.filter(profile__role='instructor').count()
        if remaining > 0:
            self.stdout.write(self.style.WARNING(f'\n⚠️  Warning: {remaining} instructor(s) still remain in database'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✓ All instructors have been deleted successfully!'))

