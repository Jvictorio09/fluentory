#!/usr/bin/env python
"""
Add missing columns to CourseTeacher table
Run with: python manage.py shell < fix_courseteacher_columns.py
Or: python -c "exec(open('fix_courseteacher_columns.py').read())"
"""
import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myProject.settings')

try:
    import django
    django.setup()
except Exception as e:
    print(f"Error setting up Django: {e}")
    print("Please run this script with: python manage.py shell < fix_courseteacher_columns.py")
    sys.exit(1)

from django.db import connection

def add_missing_columns():
    """Add missing columns to CourseTeacher table"""
    table_name = 'myApp_courseteacher'
    
    with connection.cursor() as cursor:
        # Check if table exists
        if 'postgresql' in connection.vendor:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = %s
                );
            """, [table_name])
            table_exists = cursor.fetchone()[0]
            
            if not table_exists:
                print(f"Table {table_name} does not exist. Skipping.")
                return
            
            # Check and add can_manage_schedule
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_name = %s AND column_name = 'can_manage_schedule'
                );
            """, [table_name])
            column_exists = cursor.fetchone()[0]
            
            if not column_exists:
                print(f"Adding can_manage_schedule column to {table_name}...")
                cursor.execute(f"""
                    ALTER TABLE {table_name}
                    ADD COLUMN can_manage_schedule BOOLEAN DEFAULT FALSE NOT NULL;
                """)
                print("✓ Added can_manage_schedule column")
            else:
                print("✓ can_manage_schedule column already exists")
            
            # Check and add requires_booking_approval
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_name = %s AND column_name = 'requires_booking_approval'
                );
            """, [table_name])
            column_exists = cursor.fetchone()[0]
            
            if not column_exists:
                print(f"Adding requires_booking_approval column to {table_name}...")
                cursor.execute(f"""
                    ALTER TABLE {table_name}
                    ADD COLUMN requires_booking_approval BOOLEAN NULL;
                """)
                print("✓ Added requires_booking_approval column")
            else:
                print("✓ requires_booking_approval column already exists")
                
        else:
            # SQLite
            cursor.execute(f"""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='{table_name}';
            """)
            if not cursor.fetchone():
                print(f"Table {table_name} does not exist. Skipping.")
                return
            
            # Check columns
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'can_manage_schedule' not in columns:
                print(f"Adding can_manage_schedule column to {table_name}...")
                cursor.execute(f"""
                    ALTER TABLE {table_name}
                    ADD COLUMN can_manage_schedule BOOLEAN DEFAULT 0 NOT NULL;
                """)
                print("✓ Added can_manage_schedule column")
            else:
                print("✓ can_manage_schedule column already exists")
            
            if 'requires_booking_approval' not in columns:
                print(f"Adding requires_booking_approval column to {table_name}...")
                cursor.execute(f"""
                    ALTER TABLE {table_name}
                    ADD COLUMN requires_booking_approval BOOLEAN NULL;
                """)
                print("✓ Added requires_booking_approval column")
            else:
                print("✓ requires_booking_approval column already exists")
    
    print("\n✅ CourseTeacher table columns fixed!")

if __name__ == '__main__':
    try:
        add_missing_columns()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

