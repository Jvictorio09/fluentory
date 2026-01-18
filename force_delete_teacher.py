"""
Force delete a teacher by ID - handles all foreign key relationships
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myProject.settings')
django.setup()

from django.db import connection
from myApp.models import Teacher, User, UserProfile
from django.db.models import Q

def force_delete_teacher(teacher_id):
    """Force delete a teacher and all related data"""
    
    print("=" * 70)
    print(f"FORCE DELETING TEACHER ID: {teacher_id}")
    print("=" * 70)
    print()
    
    try:
        teacher = Teacher.objects.get(id=teacher_id)
        user = teacher.user
        user_id = user.id
        
        print(f"Teacher: {teacher.user.username}")
        print(f"User ID: {user_id}")
        print()
        
        # Step 1: Delete related data that references Teacher
        print("Step 1: Deleting related data...")
        
        # CourseTeacher
        try:
            from myApp.models import CourseTeacher
            deleted = CourseTeacher.objects.filter(teacher=teacher).delete()
            print(f"  ✓ Deleted {deleted[0]} CourseTeacher records")
        except Exception as e:
            print(f"  ⚠ CourseTeacher: {e}")
        
        # LiveClassBooking, BookingSeries, etc.
        try:
            from myApp.models import LiveClassBooking, BookingSeries, TeacherBookingPolicy, LiveClassSession, TeacherAvailability
            deleted = LiveClassBooking.objects.filter(teacher=teacher).delete()
            print(f"  ✓ Deleted {deleted[0]} LiveClassBooking records")
            
            deleted = BookingSeries.objects.filter(teacher=teacher).delete()
            print(f"  ✓ Deleted {deleted[0]} BookingSeries records")
            
            deleted = TeacherBookingPolicy.objects.filter(teacher=teacher).delete()
            print(f"  ✓ Deleted {deleted[0]} TeacherBookingPolicy records")
            
            # LiveClassSession - set teacher to NULL (SET_NULL)
            updated = LiveClassSession.objects.filter(teacher=teacher).update(teacher=None)
            print(f"  ✓ Set teacher to NULL for {updated} LiveClassSession records")
            
            deleted = TeacherAvailability.objects.filter(teacher=teacher).delete()
            print(f"  ✓ Deleted {deleted[0]} TeacherAvailability records")
        except Exception as e:
            print(f"  ⚠ Booking/availability data: {e}")
        
        # Step 2: Delete UserProfile first (if it exists)
        print("\nStep 2: Deleting UserProfile...")
        try:
            if hasattr(user, 'profile'):
                user.profile.delete()
                print("  ✓ UserProfile deleted")
        except Exception as e:
            print(f"  ⚠ UserProfile deletion: {e}")
        
        # Step 3: Delete User (should cascade delete Teacher)
        print("\nStep 3: Deleting User (cascades to Teacher)...")
        try:
            # Check if user is admin/superuser
            if user.is_superuser or user.is_staff:
                print("  ⚠ User is superuser/staff - skipping User deletion")
                # Just delete Teacher directly
                teacher.delete()
                print("  ✓ Teacher deleted directly")
            else:
                # Delete User - should cascade delete Teacher
                user.delete()
                print("  ✓ User deleted (Teacher should cascade)")
                
                # Verify Teacher is deleted
                if not Teacher.objects.filter(id=teacher_id).exists():
                    print("  ✓ Teacher successfully deleted (cascaded from User)")
                else:
                    print("  ⚠ Teacher still exists - deleting directly")
                    Teacher.objects.filter(id=teacher_id).delete()
        except Exception as e:
            print(f"  ✗ Error: {e}")
            # Try deleting Teacher directly
            try:
                teacher.delete()
                print("  ✓ Teacher deleted directly (fallback)")
            except Exception as e2:
                print(f"  ✗ Teacher deletion failed: {e2}")
                # Last resort: raw SQL
                try:
                    with connection.cursor() as cursor:
                        cursor.execute(f'DELETE FROM "myApp_teacher" WHERE id = %s', [teacher_id])
                    print("  ✓ Teacher deleted via raw SQL")
                except Exception as e3:
                    print(f"  ✗ Raw SQL deletion failed: {e3}")
                    raise
        
        # Final verification
        print("\nVerification:")
        if Teacher.objects.filter(id=teacher_id).exists():
            print(f"  ✗ Teacher {teacher_id} still exists!")
            return False
        else:
            print(f"  ✓ Teacher {teacher_id} successfully deleted!")
            return True
            
    except Teacher.DoesNotExist:
        print(f"  ✗ Teacher {teacher_id} does not exist")
        return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        teacher_id = int(sys.argv[1])
        success = force_delete_teacher(teacher_id)
        if success:
            print("\n✓ Teacher deletion successful!")
        else:
            print("\n✗ Teacher deletion failed!")
    else:
        print("Usage: python force_delete_teacher.py <teacher_id>")
        print("\nExample: python force_delete_teacher.py 1")

