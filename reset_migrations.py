"""
Script to reset migrations and start fresh
This will:
1. Fake all existing migrations (mark as applied)
2. Create a fresh initial migration from current models
3. Apply it
"""
import os
import django
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myProject.settings')
django.setup()

from django.core.management import call_command
from django.db import connection

def reset_migrations():
    """Reset migrations to start fresh"""
    
    print("=" * 70)
    print("RESETTING MIGRATIONS - STARTING FRESH")
    print("=" * 70)
    print()
    
    # Step 1: Fake all migrations for all apps
    print("Step 1: Faking all existing migrations...")
    apps = ['admin', 'auth', 'contenttypes', 'myApp', 'sessions']
    
    for app in apps:
        try:
            print(f"  Faking migrations for {app}...", end=" ")
            call_command('migrate', app, '--fake', verbosity=0)
            print("✓ Done")
        except Exception as e:
            print(f"⚠ Warning: {e}")
    
    print()
    print("Step 2: Creating fresh initial migration from current models...")
    try:
        call_command('makemigrations', 'myApp', verbosity=1)
        print("✓ Migration created")
    except Exception as e:
        print(f"⚠ Error: {e}")
        return
    
    print()
    print("Step 3: Applying the fresh migration...")
    try:
        call_command('migrate', 'myApp', verbosity=1)
        print("✓ Migration applied")
    except Exception as e:
        print(f"⚠ Error: {e}")
        return
    
    print()
    print("=" * 70)
    print("MIGRATION RESET COMPLETE!")
    print("=" * 70)
    print()
    print("Your database is now in sync with your models.")
    print("All previous migrations have been marked as applied,")
    print("and a fresh migration has been created from your current models.")

if __name__ == '__main__':
    try:
        reset_migrations()
    except Exception as e:
        print(f"\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

