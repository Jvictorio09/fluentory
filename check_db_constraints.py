"""
Check and report database constraint issues for CourseTeacher table
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myProject.settings')
django.setup()

from django.db import connection

def check_constraints():
    """Check foreign key constraints on CourseTeacher table"""
    with connection.cursor() as cursor:
        vendor = connection.vendor
        
        if 'postgresql' in vendor:
            # Check foreign key constraints on myapp_courseteacher table
            cursor.execute("""
                SELECT 
                    tc.constraint_name,
                    tc.table_name,
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                    AND tc.table_name = 'myapp_courseteacher'
                ORDER BY kcu.column_name;
            """)
            
            constraints = cursor.fetchall()
            print("Foreign Key Constraints on myapp_courseteacher:")
            print("=" * 80)
            for constraint in constraints:
                constraint_name, table, column, foreign_table, foreign_column = constraint
                print(f"Constraint: {constraint_name}")
                print(f"  Column: {column}")
                print(f"  References: {foreign_table}.{foreign_column}")
                print()
                
                # Check if constraint is pointing to wrong table
                if column == 'teacher_id' and foreign_table != 'myapp_teacher':
                    print(f"  ⚠ ERROR: teacher_id should reference myapp_teacher, but references {foreign_table}")
                elif column == 'teacher_id' and foreign_table == 'myapp_teacher':
                    print(f"  ✓ Correct: teacher_id references myapp_teacher")
        else:
            print(f"Unsupported database: {vendor}")

if __name__ == '__main__':
    check_constraints()


