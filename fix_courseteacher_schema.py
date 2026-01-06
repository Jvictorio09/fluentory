"""
Fix CourseTeacher table schema mismatch
The database might have 'can_host_live' but the model expects 'can_create_live_classes'
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myProject.settings')
django.setup()

from django.db import connection

def fix_courseteacher_schema():
    """Fix schema mismatch between database and model"""
    cursor = connection.cursor()
    vendor = connection.vendor
    
    print(f"Database vendor: {vendor}")
    
    try:
        if 'postgresql' in vendor:
            # Check what columns exist
            cursor.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'myapp_courseteacher'
                ORDER BY column_name;
            """)
            columns = cursor.fetchall()
            print("\nCurrent columns in myapp_courseteacher:")
            for col in columns:
                print(f"  - {col[0]} ({col[1]}, nullable: {col[2]})")
            
            # Check if can_host_live exists
            cursor.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'myapp_courseteacher'
                AND column_name = 'can_host_live';
            """)
            has_can_host_live = cursor.fetchone() is not None
            
            # Check if can_create_live_classes exists
            cursor.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'myapp_courseteacher'
                AND column_name = 'can_create_live_classes';
            """)
            has_can_create_live_classes = cursor.fetchone() is not None
            
            print(f"\ncan_host_live exists: {has_can_host_live}")
            print(f"can_create_live_classes exists: {has_can_create_live_classes}")
            
            if has_can_host_live and not has_can_create_live_classes:
                # Rename can_host_live to can_create_live_classes
                print("\nRenaming can_host_live to can_create_live_classes...")
                cursor.execute("""
                    ALTER TABLE myapp_courseteacher
                    RENAME COLUMN can_host_live TO can_create_live_classes;
                """)
                print("✓ Column renamed successfully!")
            elif has_can_host_live and has_can_create_live_classes:
                # Both exist - copy data and drop old column
                print("\nBoth columns exist. Copying data and dropping can_host_live...")
                cursor.execute("""
                    UPDATE myapp_courseteacher
                    SET can_create_live_classes = can_host_live
                    WHERE can_create_live_classes IS NULL OR can_create_live_classes = FALSE;
                """)
                cursor.execute("""
                    ALTER TABLE myapp_courseteacher
                    DROP COLUMN can_host_live;
                """)
                print("✓ Data copied and old column dropped!")
            elif not has_can_host_live and not has_can_create_live_classes:
                # Neither exists - add can_create_live_classes
                print("\nAdding can_create_live_classes column...")
                cursor.execute("""
                    ALTER TABLE myapp_courseteacher
                    ADD COLUMN can_create_live_classes BOOLEAN DEFAULT FALSE NOT NULL;
                """)
                print("✓ Column added successfully!")
            else:
                print("\nSchema looks correct - can_create_live_classes exists")
                
        elif 'sqlite' in vendor:
            # SQLite doesn't support RENAME COLUMN in old versions
            # Need to recreate table
            print("\nSQLite detected - checking schema...")
            cursor.execute("PRAGMA table_info(myapp_courseteacher);")
            columns = cursor.fetchall()
            print("\nCurrent columns:")
            for col in columns:
                print(f"  - {col[1]} ({col[2]})")
            
            column_names = [col[1] for col in columns]
            
            if 'can_host_live' in column_names and 'can_create_live_classes' not in column_names:
                print("\n⚠ SQLite: Manual intervention needed to rename column")
                print("  You may need to recreate the table or use a migration")
        else:
            print(f"\n⚠ Unsupported database vendor: {vendor}")
            
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        connection.close()

if __name__ == '__main__':
    fix_courseteacher_schema()


