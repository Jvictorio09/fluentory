"""
Script to fake all migrations for myApp
This marks all migrations as applied without actually running them.
Use this when your database schema is already in sync with the migrations.
"""
import os
import django
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myProject.settings')
django.setup()

from django.core.management import call_command
from django.db import connection

def fake_all_migrations():
    """Fake all migrations for myApp"""
    
    # List of all migrations for myApp (in order)
    migrations = [
        '0001_initial',
        '0002_media',
        '0003_sitesettings_ai_tutor_image_and_more',
        '0004_teacher_studentmessage_liveclasssession_and_more',
        '0005_fix_all_missing_teacher_fields',
        '0006_aitutorsettings',
        '0007_add_course_pricing',
        '0008_add_course_type',
        '0009_add_booking_system',
        '0010_enhance_teacher_availability',
    ]
    
    print("=" * 60)
    print("Faking all myApp migrations...")
    print("=" * 60)
    print()
    
    for migration in migrations:
        try:
            print(f"Faking migration: {migration}...", end=" ")
            call_command('migrate', 'myApp', migration, '--fake', verbosity=0)
            print("✓ Done")
        except Exception as e:
            error_msg = str(e)
            # If migration is already applied, that's okay - try to continue
            if 'already applied' in error_msg.lower():
                print("✓ Already applied (skipped)")
            else:
                print(f"⚠ Warning: {error_msg}")
                # Continue with next migration
                continue
    
    print()
    print("=" * 60)
    print("Migration faking completed!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Check migration status: python manage.py showmigrations myApp")
    print("2. If you want to re-run migrations, you'll need to:")
    print("   - Unapply migrations: python manage.py migrate myApp zero --fake")
    print("   - Then re-apply: python manage.py migrate myApp")
    print()
    print("OR if you want to create fresh migrations:")
    print("1. Delete migration files (except __init__.py)")
    print("2. Create new migrations: python manage.py makemigrations")
    print("3. Apply them: python manage.py migrate")

if __name__ == '__main__':
    try:
        fake_all_migrations()
    except Exception as e:
        print(f"\nFatal error: {e}")
        sys.exit(1)

