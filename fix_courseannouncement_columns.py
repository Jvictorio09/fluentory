"""
Fix missing columns in myApp_courseannouncement table
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myProject.settings')
django.setup()

from django.db import connection

def fix_columns():
    """Add missing columns to CourseAnnouncement"""
    cursor = connection.cursor()
    vendor = connection.vendor
    
    print("=" * 70)
    print("Fixing myApp_courseannouncement table")
    print("=" * 70)
    
    try:
        if 'postgresql' in vendor:
            # Get current columns
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = 'myApp_courseannouncement'
                ORDER BY ordinal_position;
            """)
            existing_cols = [row[0] for row in cursor.fetchall()]
            print(f"\nExisting columns: {', '.join(existing_cols)}")
            
            # Add is_pinned
            if 'is_pinned' not in existing_cols:
                print("\nAdding is_pinned column...")
                cursor.execute('ALTER TABLE "myApp_courseannouncement" ADD COLUMN is_pinned BOOLEAN DEFAULT FALSE;')
                print("  [OK] is_pinned added")
            else:
                print("  [OK] is_pinned already exists")
            
            # Add send_to_all_students
            if 'send_to_all_students' not in existing_cols:
                print("\nAdding send_to_all_students column...")
                cursor.execute('ALTER TABLE "myApp_courseannouncement" ADD COLUMN send_to_all_students BOOLEAN DEFAULT TRUE;')
                print("  [OK] send_to_all_students added")
            else:
                print("  [OK] send_to_all_students already exists")
            
            # Add updated_at
            if 'updated_at' not in existing_cols:
                print("\nAdding updated_at column...")
                cursor.execute('ALTER TABLE "myApp_courseannouncement" ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;')
                print("  [OK] updated_at added")
            else:
                print("  [OK] updated_at already exists")
            
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
    fix_columns()



