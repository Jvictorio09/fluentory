"""
Management command to clean up orphaned CourseTeacher records.

This command finds and removes CourseTeacher records where:
1. The teacher_id doesn't exist in the Teacher table
2. The teacher.user doesn't exist in the User table

Usage:
    python manage.py cleanup_orphaned_courseteacher
    python manage.py cleanup_orphaned_courseteacher --dry-run  # Preview only
"""

from django.core.management.base import BaseCommand
from django.db import connection
from django.contrib.auth.models import User
from myApp.models import CourseTeacher, Teacher, Course


class Command(BaseCommand):
    help = 'Clean up orphaned CourseTeacher records where teacher_id or teacher.user is invalid'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview what would be deleted without actually deleting',
        )
        parser.add_argument(
            '--repair',
            action='store_true',
            help='Attempt to repair records by finding matching users (experimental)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        repair = options['repair']
        
        self.stdout.write(self.style.WARNING('Scanning for orphaned CourseTeacher records...'))
        
        # Find CourseTeacher records with invalid teacher_id
        orphaned_by_teacher = []
        all_assignments = CourseTeacher.objects.select_related('teacher', 'teacher__user').all()
        
        for assignment in all_assignments:
            is_orphaned = False
            reason = []
            
            # Check if teacher exists
            try:
                teacher = assignment.teacher
                if not teacher:
                    is_orphaned = True
                    reason.append('teacher is None')
            except Teacher.DoesNotExist:
                is_orphaned = True
                reason.append('teacher_id does not exist in Teacher table')
            except Exception as e:
                is_orphaned = True
                reason.append(f'error accessing teacher: {str(e)}')
            
            # Check if teacher.user exists
            if not is_orphaned:
                try:
                    user = assignment.teacher.user
                    if not user:
                        is_orphaned = True
                        reason.append('teacher.user is None')
                    else:
                        # Verify user exists in User table
                        try:
                            User.objects.get(pk=user.pk)
                        except User.DoesNotExist:
                            is_orphaned = True
                            reason.append('teacher.user_id does not exist in User table')
                except Exception as e:
                    is_orphaned = True
                    reason.append(f'error accessing teacher.user: {str(e)}')
            
            if is_orphaned:
                orphaned_by_teacher.append({
                    'assignment': assignment,
                    'reason': '; '.join(reason)
                })
        
        if not orphaned_by_teacher:
            self.stdout.write(self.style.SUCCESS('No orphaned CourseTeacher records found.'))
            return
        
        self.stdout.write(self.style.WARNING(f'\nFound {len(orphaned_by_teacher)} orphaned CourseTeacher record(s):'))
        
        for item in orphaned_by_teacher:
            assignment = item['assignment']
            reason = item['reason']
            self.stdout.write(
                f'  - ID {assignment.id}: Course "{assignment.course.title}" (ID: {assignment.course_id}), '
                f'Teacher ID: {assignment.teacher_id}, Reason: {reason}'
            )
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\nDRY RUN: No records were deleted. Run without --dry-run to delete.'))
            return
        
        # Attempt repair if requested
        if repair:
            self.stdout.write(self.style.WARNING('\nAttempting to repair records...'))
            repaired_count = 0
            
            for item in orphaned_by_teacher[:]:  # Copy list to modify during iteration
                assignment = item['assignment']
                teacher_id = assignment.teacher_id
                
                # Try to find a valid Teacher with this ID
                try:
                    teacher = Teacher.objects.select_related('user').get(pk=teacher_id)
                    if teacher.user:
                        try:
                            User.objects.get(pk=teacher.user.pk)
                            # Teacher is valid, remove from orphaned list
                            orphaned_by_teacher.remove(item)
                            repaired_count += 1
                            self.stdout.write(
                                self.style.SUCCESS(f'  ✓ Repaired assignment ID {assignment.id}')
                            )
                            continue
                        except User.DoesNotExist:
                            pass
                except Teacher.DoesNotExist:
                    pass
                
                # Try to find teacher by course instructor
                try:
                    course = assignment.course
                    if course.instructor:
                        teacher, created = Teacher.objects.get_or_create(
                            user=course.instructor,
                            defaults={'permission_level': 'standard', 'is_approved': True}
                        )
                        if teacher.user and User.objects.filter(pk=teacher.user.pk).exists():
                            assignment.teacher = teacher
                            assignment.save()
                            orphaned_by_teacher.remove(item)
                            repaired_count += 1
                            self.stdout.write(
                                self.style.SUCCESS(f'  ✓ Repaired assignment ID {assignment.id} using course instructor')
                            )
                            continue
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'  ✗ Could not repair assignment ID {assignment.id}: {str(e)}')
                    )
            
            if repaired_count > 0:
                self.stdout.write(
                    self.style.SUCCESS(f'\nRepaired {repaired_count} record(s).')
                )
        
        # Delete remaining orphaned records
        if orphaned_by_teacher:
            self.stdout.write(self.style.WARNING(f'\nDeleting {len(orphaned_by_teacher)} orphaned record(s)...'))
            deleted_count = 0
            
            for item in orphaned_by_teacher:
                try:
                    assignment = item['assignment']
                    course_title = assignment.course.title
                    assignment.delete()
                    deleted_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'  ✓ Deleted assignment ID {assignment.id} (Course: "{course_title}")')
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'  ✗ Error deleting assignment ID {item["assignment"].id}: {str(e)}')
                    )
            
            self.stdout.write(
                self.style.SUCCESS(f'\nSuccessfully deleted {deleted_count} orphaned CourseTeacher record(s).')
            )
        else:
            self.stdout.write(self.style.SUCCESS('\nAll orphaned records were repaired.'))

