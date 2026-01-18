"""
Force create django_session table
This will definitely create the table
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myProject.settings')
django.setup()

from django.db import connection

def force_create_session_table():
    """Force create django_session table"""
    
    print("=" * 70)
    print("FORCE CREATING DJANGO_SESSION TABLE")
    print("=" * 70)
    print()
    
    with connection.cursor() as cursor:
        # Check if exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND (table_name = 'django_session' OR table_name = 'Django_session')
            );
        """)
        exists = cursor.fetchone()[0]
        
        if exists:
            print("✓ django_session table already exists")
            return
        
        print("Creating django_session table...")
        
        try:
            # Drop if exists (just in case)
            cursor.execute('DROP TABLE IF EXISTS django_session CASCADE;')
            
            # Create table
            cursor.execute("""
                CREATE TABLE django_session (
                    session_key VARCHAR(40) NOT NULL PRIMARY KEY,
                    session_data TEXT NOT NULL,
                    expire_date TIMESTAMP WITH TIME ZONE NOT NULL
                );
            """)
            
            # Create index
            cursor.execute("""
                CREATE INDEX django_session_expire_date_a5c62663 
                ON django_session (expire_date);
            """)
            
            print("✓ Successfully created django_session table!")
            print("✓ Created index on expire_date")
            
        except Exception as e:
            print(f"✗ Error creating table: {e}")
            # Try without timezone
            try:
                cursor.execute("""
                    CREATE TABLE django_session (
                        session_key VARCHAR(40) NOT NULL PRIMARY KEY,
                        session_data TEXT NOT NULL,
                        expire_date TIMESTAMP NOT NULL
                    );
                """)
                cursor.execute("""
                    CREATE INDEX django_session_expire_date_a5c62663 
                    ON django_session (expire_date);
                """)
                print("✓ Successfully created django_session table (without timezone)!")
            except Exception as e2:
                print(f"✗ Failed again: {e2}")
                return
        
        # Verify
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'django_session'
            );
        """)
        if cursor.fetchone()[0]:
            print()
            print("=" * 70)
            print("✅ SUCCESS! django_session table created!")
            print("=" * 70)
            print()
            print("You can now try logging in!")
        else:
            print()
            print("⚠ Table creation may have failed. Check errors above.")

if __name__ == '__main__':
    force_create_session_table()

