"""
Fix ALL missing columns in myApp_liveclasssession to match the LiveClassSession model
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myProject.settings')
django.setup()

from django.db import connection

def fix_all_columns():
    """Add all missing columns to match the LiveClassSession model"""
    cursor = connection.cursor()
    vendor = connection.vendor
    
    print("=" * 70)
    print("Fixing ALL columns in myApp_liveclasssession table")
    print("=" * 70)
    
    try:
        if 'postgresql' in vendor:
            # Get current columns
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = 'myApp_liveclasssession'
                ORDER BY ordinal_position;
            """)
            existing_cols = [row[0] for row in cursor.fetchall()]
            print(f"\nExisting columns: {', '.join(existing_cols)}")
            
            # Required columns per model:
            # duration_minutes (PositiveIntegerField, default=60)
            # zoom_link (URLField, blank=True)
            # google_meet_link (URLField, blank=True)
            # max_attendees (PositiveIntegerField, nullable) - table has max_capacity
            # started_at (DateTimeField, nullable) - table has actual_start
            # ended_at (DateTimeField, nullable) - table has actual_end
            
            # 1. Add duration_minutes
            if 'duration_minutes' not in existing_cols:
                print("\nAdding duration_minutes column...")
                cursor.execute('ALTER TABLE "myApp_liveclasssession" ADD COLUMN duration_minutes INTEGER DEFAULT 60;')
                print("  [OK] duration_minutes added")
            else:
                print("  [OK] duration_minutes already exists")
            
            # 2. Add zoom_link
            if 'zoom_link' not in existing_cols:
                print("\nAdding zoom_link column...")
                if 'meeting_url' in existing_cols:
                    # Copy data from meeting_url if it exists
                    cursor.execute('ALTER TABLE "myApp_liveclasssession" ADD COLUMN zoom_link VARCHAR(200);')
                    cursor.execute('UPDATE "myApp_liveclasssession" SET zoom_link = meeting_url WHERE meeting_url IS NOT NULL;')
                    print("  [OK] zoom_link added (data copied from meeting_url)")
                else:
                    cursor.execute('ALTER TABLE "myApp_liveclasssession" ADD COLUMN zoom_link VARCHAR(200);')
                    print("  [OK] zoom_link added")
            else:
                print("  [OK] zoom_link already exists")
            
            # 3. Add google_meet_link
            if 'google_meet_link' not in existing_cols:
                print("\nAdding google_meet_link column...")
                cursor.execute('ALTER TABLE "myApp_liveclasssession" ADD COLUMN google_meet_link VARCHAR(200);')
                print("  [OK] google_meet_link added")
            else:
                print("  [OK] google_meet_link already exists")
            
            # 4. Add max_attendees (table has max_capacity)
            if 'max_attendees' not in existing_cols:
                print("\nAdding max_attendees column...")
                if 'max_capacity' in existing_cols:
                    # Copy data from max_capacity
                    cursor.execute('ALTER TABLE "myApp_liveclasssession" ADD COLUMN max_attendees INTEGER;')
                    cursor.execute('UPDATE "myApp_liveclasssession" SET max_attendees = max_capacity WHERE max_capacity IS NOT NULL;')
                    print("  [OK] max_attendees added (data copied from max_capacity)")
                else:
                    cursor.execute('ALTER TABLE "myApp_liveclasssession" ADD COLUMN max_attendees INTEGER;')
                    print("  [OK] max_attendees added")
            else:
                print("  [OK] max_attendees already exists")
            
            # 5. Add started_at (table has actual_start)
            if 'started_at' not in existing_cols:
                print("\nAdding started_at column...")
                if 'actual_start' in existing_cols:
                    # Copy data from actual_start
                    cursor.execute('ALTER TABLE "myApp_liveclasssession" ADD COLUMN started_at TIMESTAMP;')
                    cursor.execute('UPDATE "myApp_liveclasssession" SET started_at = actual_start WHERE actual_start IS NOT NULL;')
                    print("  [OK] started_at added (data copied from actual_start)")
                else:
                    cursor.execute('ALTER TABLE "myApp_liveclasssession" ADD COLUMN started_at TIMESTAMP;')
                    print("  [OK] started_at added")
            else:
                print("  [OK] started_at already exists")
            
            # 6. Add ended_at (table has actual_end)
            if 'ended_at' not in existing_cols:
                print("\nAdding ended_at column...")
                if 'actual_end' in existing_cols:
                    # Copy data from actual_end
                    cursor.execute('ALTER TABLE "myApp_liveclasssession" ADD COLUMN ended_at TIMESTAMP;')
                    cursor.execute('UPDATE "myApp_liveclasssession" SET ended_at = actual_end WHERE actual_end IS NOT NULL;')
                    print("  [OK] ended_at added (data copied from actual_end)")
                else:
                    cursor.execute('ALTER TABLE "myApp_liveclasssession" ADD COLUMN ended_at TIMESTAMP;')
                    print("  [OK] ended_at added")
            else:
                print("  [OK] ended_at already exists")
            
        connection.commit()
        print("\n" + "=" * 70)
        print("[SUCCESS] All columns fixed!")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        connection.rollback()
        raise
    finally:
        cursor.close()

if __name__ == '__main__':
    fix_all_columns()


