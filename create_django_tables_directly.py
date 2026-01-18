"""
Create Django built-in tables directly using SQL
This bypasses migrations and creates tables directly
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myProject.settings')
django.setup()

from django.db import connection
from django.contrib.sessions.models import Session
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User, Group, Permission

def table_exists(table_name):
    """Check if table exists"""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND LOWER(table_name) = LOWER(%s)
            );
        """, [table_name])
        return cursor.fetchone()[0]

def create_django_session_table():
    """Create django_session table directly"""
    if table_exists('django_session'):
        print("✓ django_session table already exists")
        return True
    
    print("Creating django_session table...")
    with connection.cursor() as cursor:
        try:
            # Create the table
            cursor.execute("""
                CREATE TABLE django_session (
                    session_key VARCHAR(40) NOT NULL PRIMARY KEY,
                    session_data TEXT NOT NULL,
                    expire_date TIMESTAMP NOT NULL
                );
            """)
            
            # Create index
            cursor.execute("""
                CREATE INDEX django_session_expire_date_a5c62663 
                ON django_session (expire_date);
            """)
            
            print("✓ Created django_session table")
            return True
        except Exception as e:
            if 'already exists' in str(e).lower():
                print("✓ django_session table already exists")
                return True
            print(f"✗ Error: {e}")
            return False

def create_all_django_tables():
    """Create all missing Django built-in tables"""
    
    print("=" * 70)
    print("CREATING DJANGO BUILT-IN TABLES")
    print("=" * 70)
    print()
    
    # 1. django_session
    create_django_session_table()
    
    # 2. Check and create other Django tables via migrations
    print("\nRunning Django migrations for built-in apps...")
    from django.core.management import call_command
    
    try:
        # Run migrations for sessions app
        call_command('migrate', 'sessions', verbosity=1)
        print("✓ Sessions migrations applied")
    except Exception as e:
        print(f"⚠ Sessions migration: {e}")
    
    try:
        # Run migrations for contenttypes
        call_command('migrate', 'contenttypes', verbosity=1)
        print("✓ Contenttypes migrations applied")
    except Exception as e:
        print(f"⚠ Contenttypes migration: {e}")
    
    try:
        # Run migrations for auth
        call_command('migrate', 'auth', verbosity=1)
        print("✓ Auth migrations applied")
    except Exception as e:
        print(f"⚠ Auth migration: {e}")
    
    try:
        # Run migrations for admin
        call_command('migrate', 'admin', verbosity=1)
        print("✓ Admin migrations applied")
    except Exception as e:
        print(f"⚠ Admin migration: {e}")
    
    # Verify django_session exists
    print()
    if table_exists('django_session'):
        print("✅ django_session table exists!")
        print("You can now log in!")
    else:
        print("❌ django_session table still missing")
        print("Try running: python manage.py migrate sessions")
    
    print()
    print("=" * 70)

if __name__ == '__main__':
    try:
        create_all_django_tables()
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()

