"""
Fix the StudentMessage table to match the model
The table has wrong column names - need to add teacher_id and student_id
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myProject.settings')
django.setup()

from django.db import connection

def fix_studentmessage_table():
    """Add missing columns to myApp_studentmessage table"""
    cursor = connection.cursor()
    vendor = connection.vendor
    
    print("=" * 70)
    print("Fixing myApp_studentmessage table structure")
    print("=" * 70)
    
    try:
        if 'postgresql' in vendor:
            # Check if teacher_id exists
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = 'myApp_studentmessage' 
                AND column_name = 'teacher_id';
            """)
            if not cursor.fetchone():
                print("\nAdding teacher_id column...")
                cursor.execute("""
                    ALTER TABLE "myApp_studentmessage" ADD COLUMN teacher_id BIGINT;
                """)
                
                # Add foreign key constraint
                cursor.execute("""
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = 'myApp_teacher';
                """)
                if cursor.fetchone():
                    # Drop existing constraint if it exists (catch error if it doesn't)
                    try:
                        cursor.execute('ALTER TABLE "myApp_studentmessage" DROP CONSTRAINT IF EXISTS myApp_studentmessage_teacher_id_fkey;')
                    except:
                        pass
                    
                    cursor.execute("""
                        ALTER TABLE "myApp_studentmessage" 
                        ADD CONSTRAINT myApp_studentmessage_teacher_id_fkey 
                        FOREIGN KEY (teacher_id) REFERENCES "myApp_teacher"(id) ON DELETE CASCADE;
                    """)
                    
                    # Create index
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS myApp_studentmessage_teacher_id_idx 
                        ON "myApp_studentmessage"(teacher_id);
                    """)
                print("  [OK] teacher_id column added with foreign key")
            else:
                print("  [OK] teacher_id column already exists")
            
            # Check if student_id exists (model uses student, not recipient)
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = 'myApp_studentmessage' 
                AND column_name = 'student_id';
            """)
            if not cursor.fetchone():
                # Check if it's called recipient_id
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_schema = 'public' 
                    AND table_name = 'myApp_studentmessage' 
                    AND column_name = 'recipient_id';
                """)
                if cursor.fetchone():
                    print("\n  [INFO] Table uses recipient_id (old structure)")
                    print("  [INFO] Migration expects student_id - this may cause issues")
            
            # Check if message column exists (model uses message, not content)
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = 'myApp_studentmessage' 
                AND column_name = 'message';
            """)
            if not cursor.fetchone():
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_schema = 'public' 
                    AND table_name = 'myApp_studentmessage' 
                    AND column_name = 'content';
                """)
                if cursor.fetchone():
                    print("\n  [INFO] Table uses 'content' column, model expects 'message'")
                    
        connection.commit()
        print("\n" + "=" * 70)
        print("[SUCCESS] Fix completed!")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        connection.rollback()
        raise
    finally:
        cursor.close()

if __name__ == '__main__':
    fix_studentmessage_table()



