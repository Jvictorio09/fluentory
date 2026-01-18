"""
Check if GiftEnrollment table exists and create it if needed
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myProject.settings')
django.setup()

from django.db import connection
from django.core.management import call_command

def check_and_create_table():
    """Check if table exists, if not, run the migration"""
    
    print("=" * 70)
    print("CHECKING GiftEnrollment TABLE")
    print("=" * 70)
    print()
    
    # Check if table exists
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND LOWER(table_name) = LOWER('myApp_giftenrollment')
            );
        """)
        exists = cursor.fetchone()[0]
        
        if exists:
            print("✓ Table 'myApp_giftenrollment' EXISTS")
            
            # Count rows
            cursor.execute('SELECT COUNT(*) FROM "myApp_giftenrollment";')
            count = cursor.fetchone()[0]
            print(f"  Rows: {count}")
        else:
            print("✗ Table 'myApp_giftenrollment' DOES NOT EXIST")
            print()
            print("Attempting to create it...")
            print()
            
            # Check migration status
            try:
                # Try to apply the specific migration
                print("Running migration 0030_giftenrollment...")
                call_command('migrate', 'myApp', '0030', verbosity=2)
                print()
                print("✓ Migration applied successfully!")
            except Exception as e:
                print(f"⚠ Error applying migration: {e}")
                print()
                print("Trying to apply all migrations...")
                try:
                    call_command('migrate', 'myApp', verbosity=2)
                    print()
                    print("✓ All migrations applied!")
                except Exception as e2:
                    print(f"✗ Error: {e2}")
                    print()
                    print("You may need to run: python manage.py migrate")
    
    print()
    print("=" * 70)

if __name__ == '__main__':
    check_and_create_table()

