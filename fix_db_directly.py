"""
Direct database fix script - run this to fix the column name immediately
Run: python fix_db_directly.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myProject.settings')
django.setup()

from django.db import connection

def fix_database():
    """Fix the can_host_live -> can_create_live_classes column name"""
    with connection.cursor() as cursor:
        vendor = connection.vendor
        print(f"Database: {vendor}")
        
        if 'postgresql' in vendor:
            # Simple, direct SQL to fix the issue
            try:
                # Check if table exists and has can_host_live
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_schema = 'public' 
                    AND LOWER(table_name) = 'myapp_courseteacher'
                    AND column_name = 'can_host_live';
                """)
                
                if cursor.fetchone():
                    # Table exists and has the wrong column - rename it
                    print("Found 'can_host_live' column - renaming to 'can_create_live_classes'...")
                    cursor.execute("""
                        DO $$
                        BEGIN
                            IF EXISTS (
                                SELECT 1 FROM information_schema.columns 
                                WHERE table_schema = 'public' 
                                AND LOWER(table_name) = 'myapp_courseteacher'
                                AND column_name = 'can_host_live'
                            ) THEN
                                ALTER TABLE myapp_courseteacher 
                                RENAME COLUMN can_host_live TO can_create_live_classes;
                                RAISE NOTICE 'Column renamed successfully';
                            END IF;
                        END $$;
                    """)
                    print("✓ Fixed! Column renamed to 'can_create_live_classes'")
                else:
                    print("✓ Column 'can_host_live' not found - schema is correct")
            except Exception as e:
                print(f"Error: {e}")
        else:
            print(f"Unsupported database: {vendor}")

if __name__ == '__main__':
    fix_database()


