"""
Check ALL teacher-related tables to find any other missing columns
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myProject.settings')
django.setup()

from django.db import connection
from myApp.models import Teacher, CourseTeacher, StudentMessage, LiveClassSession, CourseAnnouncement

print("=" * 70)
print("Checking ALL Teacher-related tables for missing columns")
print("=" * 70)

cursor = connection.cursor()
vendor = connection.vendor

tables_to_check = [
    (Teacher, 'myApp_teacher'),
    (CourseTeacher, 'myApp_courseteacher'),
    (StudentMessage, 'myApp_studentmessage'),
    (LiveClassSession, 'myApp_liveclasssession'),
    (CourseAnnouncement, 'myApp_courseannouncement'),
]

if 'postgresql' in vendor:
    for model, table_name in tables_to_check:
        print(f"\n{'='*70}")
        print(f"Table: {table_name}")
        print(f"{'='*70}")
        
        # Get actual columns
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = %s
            ORDER BY ordinal_position;
        """, [table_name])
        actual_cols = set([row[0] for row in cursor.fetchall()])
        
        # Get expected columns from model
        expected_cols = set()
        for field in model._meta.get_fields():
            if hasattr(field, 'column'):
                expected_cols.add(field.column)
            elif hasattr(field, 'related_model') and hasattr(field, 'get_attname'):
                expected_cols.add(field.get_attname())
        
        print(f"\nExpected columns ({len(expected_cols)}):")
        for col in sorted(expected_cols):
            status = "[OK]" if col in actual_cols else "[MISSING]"
            print(f"  {status} {col}")
        
        missing = expected_cols - actual_cols
        if missing:
            print(f"\n[MISSING COLUMNS]: {', '.join(sorted(missing))}")
        else:
            print(f"\n[OK] All columns present!")

cursor.close()


