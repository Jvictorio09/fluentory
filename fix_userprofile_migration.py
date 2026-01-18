"""
Quick fix to add missing force_password_reset column to UserProfile table
Run this if migrations are failing
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myProject.settings')
django.setup()

from django.db import connection

def add_force_password_reset_column():
    """Add force_password_reset column if it doesn't exist"""
    with connection.cursor() as cursor:
        # Check if column exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = 'myapp_userprofile'
                AND column_name = 'force_password_reset'
            );
        """)
        exists = cursor.fetchone()[0]
        
        if exists:
            print("✓ Column 'force_password_reset' already exists")
            return
        
        # Add the column
        try:
            cursor.execute("""
                ALTER TABLE myapp_userprofile 
                ADD COLUMN force_password_reset BOOLEAN DEFAULT FALSE NOT NULL;
            """)
            print("✓ Successfully added 'force_password_reset' column")
        except Exception as e:
            print(f"⚠ Error adding column: {e}")
            # Try with quoted table name
            try:
                cursor.execute("""
                    ALTER TABLE "myApp_userprofile" 
                    ADD COLUMN force_password_reset BOOLEAN DEFAULT FALSE NOT NULL;
                """)
                print("✓ Successfully added 'force_password_reset' column (with quoted table)")
            except Exception as e2:
                print(f"⚠ Error with quoted table: {e2}")

if __name__ == '__main__':
    add_force_password_reset_column()

