"""
Fix orphaned Course records that reference non-existent users
Run this to clean up data issues
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myProject.settings')
django.setup()

from django.contrib.auth.models import User
from myApp.models import Course, CourseTeacher, Teacher

def fix_orphaned_courses():
    """Find and report courses with invalid instructor references"""
    print("Checking for orphaned courses...")
    
    # Find all courses
    all_courses = Course.objects.all()
    orphaned = []
    
    for course in all_courses:
        if course.instructor_id:
            # Check if instructor user exists
            if not User.objects.filter(id=course.instructor_id).exists():
                orphaned.append(course)
                print(f"⚠ Course '{course.title}' (ID: {course.id}) has invalid instructor_id: {course.instructor_id}")
    
    if orphaned:
        print(f"\nFound {len(orphaned)} orphaned courses")
        print("You may need to update these courses to have valid instructors or set instructor=None")
    else:
        print("✓ No orphaned courses found")
    
    # Check for CourseTeacher with invalid teacher references
    print("\nChecking CourseTeacher records...")
    all_assignments = CourseTeacher.objects.all()
    invalid_assignments = []
    
    for assignment in all_assignments:
        if not Teacher.objects.filter(id=assignment.teacher_id).exists():
            invalid_assignments.append(assignment)
            print(f"⚠ CourseTeacher (ID: {assignment.id}) has invalid teacher_id: {assignment.teacher_id}")
    
    if invalid_assignments:
        print(f"\nFound {len(invalid_assignments)} invalid CourseTeacher records")
        print("These need to be deleted or fixed")
    else:
        print("✓ All CourseTeacher records are valid")
    
    # Check Teacher records
    print("\nChecking Teacher records...")
    all_teachers = Teacher.objects.all()
    invalid_teachers = []
    
    for teacher in all_teachers:
        if not User.objects.filter(id=teacher.user_id).exists():
            invalid_teachers.append(teacher)
            print(f"⚠ Teacher (ID: {teacher.id}) has invalid user_id: {teacher.user_id}")
    
    if invalid_teachers:
        print(f"\nFound {len(invalid_teachers)} invalid Teacher records")
    else:
        print("✓ All Teacher records are valid")

if __name__ == '__main__':
    fix_orphaned_courses()


