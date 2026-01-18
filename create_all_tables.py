"""
Create all missing Django tables
This will run migrations for ALL apps including Django's built-in apps
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myProject.settings')
django.setup()

from django.core.management import call_command

def create_all_tables():
    """Run migrations for all apps"""
    
    print("=" * 70)
    print("CREATING ALL DJANGO TABLES")
    print("=" * 70)
    print()
    print("This will create all missing tables including:")
    print("  - django_session (for user sessions)")
    print("  - auth_user, auth_group, etc. (for authentication)")
    print("  - django_admin_log (for admin actions)")
    print("  - contenttypes (for content types)")
    print("  - And all your app tables...")
    print()
    
    try:
        # Run migrations for all apps
        call_command('migrate', verbosity=2, interactive=False)
        print()
        print("=" * 70)
        print("✅ SUCCESS! All tables created.")
        print("=" * 70)
        print()
        print("You can now log in!")
    except Exception as e:
        print()
        print("=" * 70)
        print("❌ ERROR:")
        print("=" * 70)
        print(str(e))
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    create_all_tables()

