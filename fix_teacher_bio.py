"""
Quick fix script to add missing columns to tables from migration 0004
Run this with: python fix_teacher_bio.py
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myProject.settings')
django.setup()

from django.db import connection

def add_missing_columns():
    """Add missing columns to tables if they don't exist"""
    cursor = connection.cursor()
    fixes_applied = []
    
    try:
        vendor = connection.vendor
        
        if 'postgresql' in vendor:
            print("Checking PostgreSQL database...")
            
            # Fix 1: Add bio to myapp_teacher
            cursor.execute("""
                DO $$ 
                BEGIN 
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_schema = 'public'
                        AND table_name='myapp_teacher' AND column_name='bio'
                    ) THEN
                        ALTER TABLE myapp_teacher ADD COLUMN bio TEXT;
                        RAISE NOTICE 'Column myapp_teacher.bio added successfully';
                    END IF;
                END $$;
            """)
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_schema = 'public'
                    AND table_name='myapp_teacher' AND column_name='bio'
                );
            """)
            if cursor.fetchone()[0]:
                fixes_applied.append("✓ myapp_teacher.bio column exists")
            else:
                fixes_applied.append("✓ myapp_teacher.bio column added")
            
            # Fix 2: Add can_create_live_classes to myapp_courseteacher
            cursor.execute("""
                DO $$ 
                BEGIN 
                    IF EXISTS (
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'myapp_courseteacher'
                    ) THEN
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_schema = 'public'
                            AND table_name='myapp_courseteacher' AND column_name='can_create_live_classes'
                        ) THEN
                            ALTER TABLE myapp_courseteacher ADD COLUMN can_create_live_classes BOOLEAN DEFAULT FALSE;
                            RAISE NOTICE 'Column myapp_courseteacher.can_create_live_classes added successfully';
                        END IF;
                    END IF;
                END $$;
            """)
            fixes_applied.append("✓ myapp_courseteacher.can_create_live_classes checked")
            
        elif 'sqlite' in vendor:
            print("Checking SQLite database...")
            
            # Fix 1: Add bio to myapp_teacher
            cursor.execute("PRAGMA table_info(myapp_teacher);")
            teacher_columns = [row[1] for row in cursor.fetchall()]
            
            if 'bio' not in teacher_columns:
                cursor.execute("ALTER TABLE myapp_teacher ADD COLUMN bio TEXT;")
                fixes_applied.append("✓ myapp_teacher.bio column added")
            else:
                fixes_applied.append("✓ myapp_teacher.bio column already exists")
            
            # Fix 2: Add can_create_live_classes to myapp_courseteacher
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='myapp_courseteacher';")
            if cursor.fetchone():
                cursor.execute("PRAGMA table_info(myapp_courseteacher);")
                courseteacher_columns = [row[1] for row in cursor.fetchall()]
                
                if 'can_create_live_classes' not in courseteacher_columns:
                    cursor.execute("ALTER TABLE myapp_courseteacher ADD COLUMN can_create_live_classes BOOLEAN DEFAULT 0;")
                    fixes_applied.append("✓ myapp_courseteacher.can_create_live_classes column added")
                else:
                    fixes_applied.append("✓ myapp_courseteacher.can_create_live_classes column already exists")
            
        else:
            print(f"Database vendor: {vendor}")
            # Generic approach
            try:
                cursor.execute("ALTER TABLE myapp_teacher ADD COLUMN bio TEXT;")
                fixes_applied.append("✓ myapp_teacher.bio column added")
            except Exception as e:
                if 'already exists' in str(e).lower() or 'duplicate' in str(e).lower():
                    fixes_applied.append("✓ myapp_teacher.bio column already exists")
            
            try:
                cursor.execute("ALTER TABLE myapp_courseteacher ADD COLUMN can_create_live_classes BOOLEAN DEFAULT FALSE;")
                fixes_applied.append("✓ myapp_courseteacher.can_create_live_classes column added")
            except Exception as e:
                if 'already exists' in str(e).lower() or 'duplicate' in str(e).lower():
                    fixes_applied.append("✓ myapp_courseteacher.can_create_live_classes column already exists")
                    
    except Exception as e:
        print(f"✗ Error: {e}")
        raise
    finally:
        cursor.close()
    
    return fixes_applied

if __name__ == '__main__':
    print("=" * 60)
    print("Fixing Missing Database Columns")
    print("=" * 60)
    try:
        fixes = add_missing_columns()
        print("\nResults:")
        for fix in fixes:
            print(f"  {fix}")
        print("=" * 60)
        print("✓ Fix completed successfully!")
        print("=" * 60)
    except Exception as e:
        print("=" * 60)
        print(f"✗ Fix failed: {e}")
        print("=" * 60)
        exit(1)

