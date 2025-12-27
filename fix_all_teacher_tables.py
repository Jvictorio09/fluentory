"""
Comprehensive fix script to add ALL missing columns from migration 0004
Run this with: python fix_all_teacher_tables.py
This fixes all Teacher-related tables at once.
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myProject.settings')
django.setup()

from django.db import connection

def fix_all_teacher_tables():
    """Add ALL missing columns to Teacher-related tables"""
    cursor = connection.cursor()
    fixes_applied = []
    errors = []
    
    try:
        vendor = connection.vendor
        
        if 'postgresql' in vendor:
            print("Checking PostgreSQL database for all missing columns...")
            
            # Fix 1: myapp_teacher.bio
            try:
                cursor.execute("""
                    DO $$ 
                    BEGIN 
                        IF EXISTS (
                            SELECT 1 FROM information_schema.tables 
                            WHERE table_schema = 'public' AND table_name = 'myapp_teacher'
                        ) THEN
                            IF NOT EXISTS (
                                SELECT 1 FROM information_schema.columns 
                                WHERE table_schema = 'public'
                                AND table_name='myapp_teacher' AND column_name='bio'
                            ) THEN
                                ALTER TABLE myapp_teacher ADD COLUMN bio TEXT;
                            END IF;
                        END IF;
                    END $$;
                """)
                fixes_applied.append("[OK] myapp_teacher.bio")
            except Exception as e:
                errors.append(f"✗ myapp_teacher.bio: {e}")
            
            # Fix 2: myapp_courseteacher.can_create_live_classes
            try:
                cursor.execute("""
                    DO $$ 
                    BEGIN 
                        IF EXISTS (
                            SELECT 1 FROM information_schema.tables 
                            WHERE table_schema = 'public' AND table_name = 'myapp_courseteacher'
                        ) THEN
                            IF NOT EXISTS (
                                SELECT 1 FROM information_schema.columns 
                                WHERE table_schema = 'public'
                                AND table_name='myapp_courseteacher' AND column_name='can_create_live_classes'
                            ) THEN
                                ALTER TABLE myapp_courseteacher ADD COLUMN can_create_live_classes BOOLEAN DEFAULT FALSE;
                            END IF;
                        END IF;
                    END $$;
                """)
                fixes_applied.append("[OK] myapp_courseteacher.can_create_live_classes")
            except Exception as e:
                errors.append(f"✗ myapp_courseteacher.can_create_live_classes: {e}")
            
            # Fix 3: myapp_studentmessage.teacher_id (ForeignKey column)
            try:
                cursor.execute("""
                    DO $$ 
                    BEGIN 
                        IF EXISTS (
                            SELECT 1 FROM information_schema.tables 
                            WHERE table_schema = 'public' AND table_name = 'myapp_studentmessage'
                        ) THEN
                            IF NOT EXISTS (
                                SELECT 1 FROM information_schema.columns 
                                WHERE table_schema = 'public'
                                AND table_name='myapp_studentmessage' AND column_name='teacher_id'
                            ) THEN
                                ALTER TABLE myapp_studentmessage ADD COLUMN teacher_id BIGINT;
                                ALTER TABLE myapp_studentmessage ADD CONSTRAINT myapp_studentmessage_teacher_id_fkey 
                                    FOREIGN KEY (teacher_id) REFERENCES myapp_teacher(id) ON DELETE CASCADE;
                                CREATE INDEX IF NOT EXISTS myapp_studentmessage_teacher_id_idx ON myapp_studentmessage(teacher_id);
                            END IF;
                        END IF;
                    END $$;
                """)
                fixes_applied.append("[OK] myapp_studentmessage.teacher_id")
            except Exception as e:
                errors.append(f"✗ myapp_studentmessage.teacher_id: {e}")
            
        elif 'sqlite' in vendor:
            print("Checking SQLite database for all missing columns...")
            
            # Fix 1: myapp_teacher.bio
            try:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='myapp_teacher';")
                if cursor.fetchone():
                    cursor.execute("PRAGMA table_info(myapp_teacher);")
                    columns = [row[1] for row in cursor.fetchall()]
                    if 'bio' not in columns:
                        cursor.execute("ALTER TABLE myapp_teacher ADD COLUMN bio TEXT;")
                        fixes_applied.append("[OK] myapp_teacher.bio added")
                    else:
                        fixes_applied.append("[OK] myapp_teacher.bio already exists")
            except Exception as e:
                errors.append(f"✗ myapp_teacher.bio: {e}")
            
            # Fix 2: myapp_courseteacher.can_create_live_classes
            try:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='myapp_courseteacher';")
                if cursor.fetchone():
                    cursor.execute("PRAGMA table_info(myapp_courseteacher);")
                    columns = [row[1] for row in cursor.fetchall()]
                    if 'can_create_live_classes' not in columns:
                        cursor.execute("ALTER TABLE myapp_courseteacher ADD COLUMN can_create_live_classes BOOLEAN DEFAULT 0;")
                        fixes_applied.append("[OK] myapp_courseteacher.can_create_live_classes added")
                    else:
                        fixes_applied.append("[OK] myapp_courseteacher.can_create_live_classes already exists")
            except Exception as e:
                errors.append(f"✗ myapp_courseteacher.can_create_live_classes: {e}")
            
            # Fix 3: myapp_studentmessage.teacher_id
            try:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='myapp_studentmessage';")
                if cursor.fetchone():
                    cursor.execute("PRAGMA table_info(myapp_studentmessage);")
                    columns = [row[1] for row in cursor.fetchall()]
                    if 'teacher_id' not in columns:
                        cursor.execute("ALTER TABLE myapp_studentmessage ADD COLUMN teacher_id INTEGER REFERENCES myapp_teacher(id) ON DELETE CASCADE;")
                        fixes_applied.append("[OK] myapp_studentmessage.teacher_id added")
                    else:
                        fixes_applied.append("[OK] myapp_studentmessage.teacher_id already exists")
            except Exception as e:
                errors.append(f"✗ myapp_studentmessage.teacher_id: {e}")
        else:
            print(f"Unsupported database vendor: {vendor}")
            errors.append(f"Unsupported database vendor: {vendor}")
                    
    except Exception as e:
        errors.append(f"✗ General error: {e}")
    finally:
        cursor.close()
    
    return fixes_applied, errors

if __name__ == '__main__':
    print("=" * 70)
    print("Fixing ALL Missing Database Columns from Migration 0004")
    print("=" * 70)
    print()
    try:
        fixes, errors = fix_all_teacher_tables()
        
        if fixes:
            print("Successfully fixed:")
            for fix in fixes:
                print(f"  {fix}")
            print()
        
        if errors:
            print("Errors encountered:")
            for error in errors:
                print(f"  {error}")
            print()
        
        print("=" * 70)
        if not errors:
            print("[SUCCESS] All fixes completed successfully!")
        else:
            print("[WARNING] Some errors occurred. Please review above.")
        print("=" * 70)
    except Exception as e:
        print("=" * 70)
        print(f"[ERROR] Fix failed: {e}")
        print("=" * 70)
        exit(1)

