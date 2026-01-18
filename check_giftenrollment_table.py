"""
Check if GiftEnrollment table exists in the database
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myProject.settings')
django.setup()

from django.db import connection

def check_table_exists():
    """Check if myApp_giftenrollment table exists"""
    with connection.cursor() as cursor:
        # Check PostgreSQL
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND LOWER(table_name) = LOWER('myApp_giftenrollment')
            );
        """)
        exists = cursor.fetchone()[0]
        
        print("=" * 70)
        print("CHECKING GiftEnrollment TABLE")
        print("=" * 70)
        print()
        
        if exists:
            print("✓ Table 'myApp_giftenrollment' EXISTS in database")
            
            # Check if it has any columns
            cursor.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND LOWER(table_name) = LOWER('myApp_giftenrollment')
                ORDER BY ordinal_position;
            """)
            columns = cursor.fetchall()
            if columns:
                print(f"\n  Columns ({len(columns)}):")
                for col_name, col_type in columns:
                    print(f"    - {col_name} ({col_type})")
            else:
                print("  ⚠ Table exists but has no columns!")
        else:
            print("✗ Table 'myApp_giftenrollment' DOES NOT EXIST in database")
            print()
            print("Checking migrations...")
            
            # Check migration status
            from django.db.migrations.recorder import MigrationRecorder
            recorder = MigrationRecorder(connection)
            applied = recorder.applied_migrations()
            
            gift_migrations = [m for m in applied if 'gift' in m[1].lower()]
            if gift_migrations:
                print(f"  Found {len(gift_migrations)} gift-related migrations applied:")
                for app, name in gift_migrations:
                    print(f"    - {app}.{name}")
            else:
                print("  ⚠ No gift-related migrations found in applied migrations")
        
        print()
        print("=" * 70)

if __name__ == '__main__':
    check_table_exists()

