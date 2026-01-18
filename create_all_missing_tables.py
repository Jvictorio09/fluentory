"""
Create ALL missing tables in one go
This will create all Django tables and all your app tables
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myProject.settings')
django.setup()

from django.core.management import call_command
from django.db import connection

def create_all_tables():
    """Create all missing tables"""
    
    print("=" * 70)
    print("CREATING ALL MISSING TABLES")
    print("=" * 70)
    print()
    
    # Step 1: Create django_session first (critical for login)
    print("Step 1: Creating django_session table...")
    with connection.cursor() as cursor:
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS django_session (
                    session_key VARCHAR(40) NOT NULL PRIMARY KEY,
                    session_data TEXT NOT NULL,
                    expire_date TIMESTAMP WITH TIME ZONE NOT NULL
                );
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS django_session_expire_date_a5c62663 
                ON django_session (expire_date);
            """)
            print("  ✓ django_session table created")
        except Exception as e:
            if 'already exists' in str(e).lower():
                print("  ✓ django_session table already exists")
            else:
                print(f"  ⚠ {e}")
    
    # Step 2: Run migrations for all Django built-in apps
    print("\nStep 2: Running migrations for Django built-in apps...")
    django_apps = ['contenttypes', 'auth', 'admin', 'sessions']
    for app in django_apps:
        try:
            call_command('migrate', app, verbosity=0)
            print(f"  ✓ {app} migrations applied")
        except Exception as e:
            print(f"  ⚠ {app}: {e}")
    
    # Step 3: Run migrations for your app
    print("\nStep 3: Running migrations for myApp...")
    try:
        call_command('migrate', 'myApp', verbosity=1)
        print("  ✓ myApp migrations applied")
    except Exception as e:
        print(f"  ⚠ myApp migration error: {e}")
        print("  (This is okay if tables already exist)")
    
    # Step 4: Verify critical tables exist
    print("\nStep 4: Verifying critical tables...")
    critical_tables = [
        'django_session',
        'auth_user',
        'myapp_userprofile',
        'myapp_teacher',
        'myapp_giftenrollment',
    ]
    
    with connection.cursor() as cursor:
        for table in critical_tables:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND LOWER(table_name) = LOWER(%s)
                );
            """, [table])
            exists = cursor.fetchone()[0]
            if exists:
                print(f"  ✓ {table} exists")
            else:
                print(f"  ✗ {table} MISSING")
    
    print()
    print("=" * 70)
    print("DONE!")
    print("=" * 70)
    print()
    print("If any tables are still missing, run:")
    print("  python manage.py migrate")
    print()
    print("Then try accessing the dashboard again!")

if __name__ == '__main__':
    try:
        create_all_tables()
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()

