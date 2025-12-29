"""
Check actual table names in the database
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myProject.settings')
django.setup()

from django.db import connection
from myApp.models import StudentMessage, Teacher, CourseTeacher

print("=" * 70)
print("Checking table names...")
print("=" * 70)

# Get table names from models
print(f"\nModel table names:")
print(f"  StudentMessage: {StudentMessage._meta.db_table}")
print(f"  Teacher: {Teacher._meta.db_table}")
print(f"  CourseTeacher: {CourseTeacher._meta.db_table}")

# Check actual tables in database
cursor = connection.cursor()
vendor = connection.vendor

if 'postgresql' in vendor:
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name LIKE '%studentmessage%' OR table_name LIKE '%teacher%'
        ORDER BY table_name;
    """)
    print(f"\nActual tables in database (matching pattern):")
    for row in cursor.fetchall():
        print(f"  {row[0]}")
    
    # Check columns in the actual studentmessage table
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND (table_name LIKE '%studentmessage%' OR table_name LIKE '%teacher%')
        ORDER BY table_name;
    """)
    tables = [row[0] for row in cursor.fetchall()]
    
    for table in tables:
        if 'studentmessage' in table.lower():
            print(f"\nColumns in {table}:")
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = %s
                ORDER BY ordinal_position;
            """, [table])
            for col in cursor.fetchall():
                print(f"  - {col[0]}")
elif 'sqlite' in vendor:
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND (name LIKE '%studentmessage%' OR name LIKE '%teacher%');")
    print(f"\nActual tables in database (matching pattern):")
    for row in cursor.fetchall():
        print(f"  {row[0]}")

cursor.close()



