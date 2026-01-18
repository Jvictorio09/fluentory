"""
Comprehensive fix for all missing columns
This will add any missing columns that exist in models but not in database
Run this to sync your database with your models
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myProject.settings')
django.setup()

from django.db import connection

def get_table_name(model_name):
    """Get actual table name (handles case sensitivity)"""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND LOWER(table_name) = LOWER(%s)
            LIMIT 1;
        """, [f'myapp_{model_name.lower()}'])
        result = cursor.fetchone()
        if result:
            return result[0]
        return None

def column_exists(table_name, column_name):
    """Check if column exists in table"""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND LOWER(table_name) = LOWER(%s)
                AND LOWER(column_name) = LOWER(%s)
            );
        """, [table_name, column_name])
        return cursor.fetchone()[0]

def add_column_safe(table_name, column_name, column_type, default_value=None, nullable=True):
    """Safely add column if it doesn't exist"""
    if column_exists(table_name, column_name):
        return False, "Column already exists"
    
    try:
        with connection.cursor() as cursor:
            # Build ALTER TABLE statement
            sql = f'ALTER TABLE {connection.ops.quote_name(table_name)} ADD COLUMN {connection.ops.quote_name(column_name)} {column_type}'
            
            if default_value is not None:
                sql += f' DEFAULT {default_value}'
            
            if not nullable:
                sql += ' NOT NULL'
            
            cursor.execute(sql)
            return True, "Column added successfully"
    except Exception as e:
        return False, str(e)

def fix_all_missing_columns():
    """Fix all missing columns"""
    
    print("=" * 70)
    print("FIXING ALL MISSING COLUMNS")
    print("=" * 70)
    print()
    
    fixes = []
    
    # Fix Teacher table
    teacher_table = get_table_name('teacher')
    if teacher_table:
        print(f"Fixing {teacher_table}...")
        
        # permission_level
        if not column_exists(teacher_table, 'permission_level'):
            success, msg = add_column_safe(teacher_table, 'permission_level', 'VARCHAR(20)', "'standard'", False)
            if success:
                print(f"  ✓ Added permission_level")
                fixes.append(f"{teacher_table}.permission_level")
            else:
                print(f"  ✗ Failed to add permission_level: {msg}")
        else:
            print(f"  ✓ permission_level already exists")
        
        # online_status_updated_at
        if not column_exists(teacher_table, 'online_status_updated_at'):
            success, msg = add_column_safe(teacher_table, 'online_status_updated_at', 'TIMESTAMP', None, True)
            if success:
                print(f"  ✓ Added online_status_updated_at")
                fixes.append(f"{teacher_table}.online_status_updated_at")
            else:
                print(f"  ✗ Failed to add online_status_updated_at: {msg}")
        else:
            print(f"  ✓ online_status_updated_at already exists")
    
    # Fix UserProfile table
    profile_table = get_table_name('userprofile')
    if profile_table:
        print(f"\nFixing {profile_table}...")
        
        # force_password_reset
        if not column_exists(profile_table, 'force_password_reset'):
            success, msg = add_column_safe(profile_table, 'force_password_reset', 'BOOLEAN', 'FALSE', False)
            if success:
                print(f"  ✓ Added force_password_reset")
                fixes.append(f"{profile_table}.force_password_reset")
            else:
                print(f"  ✗ Failed to add force_password_reset: {msg}")
        else:
            print(f"  ✓ force_password_reset already exists")
    
    print()
    print("=" * 70)
    if fixes:
        print(f"SUCCESS! Added {len(fixes)} column(s):")
        for fix in fixes:
            print(f"  - {fix}")
    else:
        print("All columns already exist!")
    print("=" * 70)
    print()
    print("Your database should now match your models.")
    print("Try logging in again!")

if __name__ == '__main__':
    try:
        fix_all_missing_columns()
    except Exception as e:
        print(f"\nFatal error: {e}")
        import traceback
        traceback.print_exc()

