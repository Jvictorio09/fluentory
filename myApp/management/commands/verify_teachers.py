from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from myApp.models import Teacher


class Command(BaseCommand):
    help = 'Verify and list all teachers in the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--delete-all',
            action='store_true',
            help='Delete all teachers (use with caution!)',
        )
        parser.add_argument(
            '--delete-ids',
            nargs='+',
            type=int,
            help='Delete specific teacher IDs',
        )

    def handle(self, *args, **options):
        teachers = Teacher.objects.all().select_related('user')
        count = teachers.count()
        
        self.stdout.write(f'\n=== TEACHER VERIFICATION ===\n')
        self.stdout.write(f'Total Teachers: {count}\n')
        
        if count > 0:
            self.stdout.write('Teacher Details:')
            self.stdout.write('-' * 80)
            for teacher in teachers:
                self.stdout.write(
                    f"ID: {teacher.id} | "
                    f"User: {teacher.user.username} ({teacher.user.email}) | "
                    f"Approved: {teacher.is_approved} | "
                    f"Created: {teacher.created_at}"
                )
        
        # Delete operations
        if options['delete_all']:
            if count == 0:
                self.stdout.write(self.style.WARNING('\nNo teachers to delete.'))
                return
            
            confirm = input(f'\nAre you sure you want to delete ALL {count} teachers? (yes/no): ')
            if confirm.lower() == 'yes':
                deleted_count = teachers.delete()[0]
                self.stdout.write(self.style.SUCCESS(f'\nDeleted {deleted_count} teacher(s).'))
            else:
                self.stdout.write(self.style.WARNING('\nDeletion cancelled.'))
        
        elif options['delete_ids']:
            teacher_ids = options['delete_ids']
            teachers_to_delete = Teacher.objects.filter(id__in=teacher_ids)
            delete_count = teachers_to_delete.count()
            
            if delete_count == 0:
                self.stdout.write(self.style.WARNING(f'\nNo teachers found with IDs: {teacher_ids}'))
                return
            
            self.stdout.write(f'\nTeachers to delete:')
            for teacher in teachers_to_delete:
                self.stdout.write(f"  - ID {teacher.id}: {teacher.user.username} ({teacher.user.email})")
            
            confirm = input(f'\nDelete these {delete_count} teacher(s)? (yes/no): ')
            if confirm.lower() == 'yes':
                deleted_count = teachers_to_delete.delete()[0]
                self.stdout.write(self.style.SUCCESS(f'\nDeleted {deleted_count} teacher(s).'))
            else:
                self.stdout.write(self.style.WARNING('\nDeletion cancelled.'))

