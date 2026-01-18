"""
Fix missing columns in database to match models
This will add any missing columns that exist in models but not in database
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myProject.settings')
django.setup()

from django.db import connection

def fix_missing_columns():
    """Add missing columns to match models"""
    
    print("=" * 70)
    print("FIXING MISSING COLUMNS")
    print("=" * 70)
    print()
    
    with connection.cursor() as cursor:
        # Fix Teacher table - add permission_level if missing
        print("Checking Teacher table...")
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'myapp_teacher'
            AND column_name = 'permission_level';
        """)
        if not cursor.fetchone():
            print("  Adding permission_level column...")
            try:
                cursor.execute("""
                    ALTER TABLE myapp_teacher 
                    ADD COLUMN permission_level VARCHAR(20) DEFAULT 'standard' NOT NULL;
                """)
                print("  ✓ Added permission_level column")
            except Exception as e:
                print(f"  ⚠ Error: {e}")
                # Try with quoted table name
                try:
                    cursor.execute("""
                        ALTER TABLE "myApp_teacher" 
                        ADD COLUMN permission_level VARCHAR(20) DEFAULT 'standard' NOT NULL;
                    """)
                    print("  ✓ Added permission_level column (with quoted table)")
                except Exception as e2:
                    print(f"  ✗ Failed: {e2}")
        else:
            print("  ✓ permission_level column already exists")
        
        # Fix UserProfile table - add force_password_reset if missing
        print("\nChecking UserProfile table...")
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND (table_name = 'myapp_userprofile' OR table_name = 'myApp_userprofile')
            AND column_name = 'force_password_reset';
        """)
        if not cursor.fetchone():
            print("  Adding force_password_reset column...")
            try:
                # Try lowercase first
                cursor.execute("""
                    ALTER TABLE myapp_userprofile 
                    ADD COLUMN force_password_reset BOOLEAN DEFAULT FALSE NOT NULL;
                """)
                print("  ✓ Added force_password_reset column")
            except Exception as e:
                print(f"  ⚠ Error: {e}")
                # Try with quoted table name
                try:
                    cursor.execute("""
                        ALTER TABLE "myApp_userprofile" 
                        ADD COLUMN force_password_reset BOOLEAN DEFAULT FALSE NOT NULL;
                    """)
                    print("  ✓ Added force_password_reset column (with quoted table)")
                except Exception as e2:
                    print(f"  ✗ Failed: {e2}")
        else:
            print("  ✓ force_password_reset column already exists")
    
    print()
    print("=" * 70)
    print("DONE!")
    print("=" * 70)
    print()
    print("Now run: python manage.py makemigrations")
    print("Then: python manage.py migrate")

if __name__ == '__main__':
    fix_missing_columns()

