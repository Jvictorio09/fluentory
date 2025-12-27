"""
Fix ALL missing columns in myApp_studentmessage to match the StudentMessage model
Model expects: teacher_id, student_id, message (not content), subject, etc.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myProject.settings')
django.setup()

from django.db import connection

def fix_all_columns():
    """Add all missing columns to match the StudentMessage model"""
    cursor = connection.cursor()
    vendor = connection.vendor
    
    print("=" * 70)
    print("Fixing ALL columns in myApp_studentmessage table")
    print("=" * 70)
    
    try:
        if 'postgresql' in vendor:
            # Get current columns
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = 'myApp_studentmessage'
                ORDER BY ordinal_position;
            """)
            existing_cols = [row[0] for row in cursor.fetchall()]
            print(f"\nExisting columns: {', '.join(existing_cols)}")
            
            # Required columns per model:
            # teacher_id (ForeignKey to Teacher) - already added
            # student_id (ForeignKey to User)
            # course_id (ForeignKey to Course, nullable) - already exists
            # subject (CharField)
            # message (TextField) - table has 'content' but model expects 'message'
            # is_read (BooleanField) - already exists
            # read_at (DateTimeField, nullable) - already exists
            # reply_to_id (ForeignKey to self, nullable)
            # created_at (DateTimeField) - already exists
            
            # 1. Add student_id if missing (table might have recipient_id)
            if 'student_id' not in existing_cols:
                print("\nAdding student_id column...")
                cursor.execute('ALTER TABLE "myApp_studentmessage" ADD COLUMN student_id INTEGER;')
                cursor.execute("""
                    ALTER TABLE "myApp_studentmessage" 
                    ADD CONSTRAINT myApp_studentmessage_student_id_fkey 
                    FOREIGN KEY (student_id) REFERENCES "auth_user"(id) ON DELETE CASCADE;
                """)
                cursor.execute('CREATE INDEX IF NOT EXISTS myApp_studentmessage_student_id_idx ON "myApp_studentmessage"(student_id);')
                print("  [OK] student_id added")
            else:
                print("  [OK] student_id already exists")
            
            # 2. Add message column if missing (table has 'content')
            if 'message' not in existing_cols:
                print("\nAdding message column...")
                if 'content' in existing_cols:
                    # Copy data from content to message
                    cursor.execute('ALTER TABLE "myApp_studentmessage" ADD COLUMN message TEXT;')
                    cursor.execute('UPDATE "myApp_studentmessage" SET message = content WHERE content IS NOT NULL;')
                    print("  [OK] message column added (data copied from content)")
                else:
                    cursor.execute('ALTER TABLE "myApp_studentmessage" ADD COLUMN message TEXT;')
                    print("  [OK] message column added")
            else:
                print("  [OK] message column already exists")
            
            # 3. Add subject if missing
            if 'subject' not in existing_cols:
                print("\nAdding subject column...")
                cursor.execute('ALTER TABLE "myApp_studentmessage" ADD COLUMN subject VARCHAR(200) DEFAULT \'\';')
                print("  [OK] subject column added")
            else:
                print("  [OK] subject column already exists")
            
            # 4. Add reply_to_id if missing
            if 'reply_to_id' not in existing_cols:
                print("\nAdding reply_to_id column...")
                cursor.execute('ALTER TABLE "myApp_studentmessage" ADD COLUMN reply_to_id BIGINT;')
                cursor.execute("""
                    ALTER TABLE "myApp_studentmessage" 
                    ADD CONSTRAINT myApp_studentmessage_reply_to_id_fkey 
                    FOREIGN KEY (reply_to_id) REFERENCES "myApp_studentmessage"(id) ON DELETE SET NULL;
                """)
                cursor.execute('CREATE INDEX IF NOT EXISTS myApp_studentmessage_reply_to_id_idx ON "myApp_studentmessage"(reply_to_id);')
                print("  [OK] reply_to_id added")
            else:
                print("  [OK] reply_to_id already exists")
            
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


