"""
SYNC DATABASE WITH MODELS - One-time fix
This script will add ALL missing columns to match your models.
Run this ONCE, then your database will be in sync.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myProject.settings')
django.setup()

from django.db import connection

def get_actual_table_name(model_name):
    """Get actual table name from database (case-insensitive search)"""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND LOWER(table_name) = LOWER(%s)
            LIMIT 1;
        """, [f'myapp_{model_name.lower()}'])
        result = cursor.fetchone()
        return result[0] if result else None

def column_exists(table_name, column_name):
    """Check if column exists"""
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

def add_column(table_name, column_name, sql_type, default=None, not_null=False):
    """Add column to table"""
    try:
        with connection.cursor() as cursor:
            # Quote table name properly
            quoted_table = connection.ops.quote_name(table_name)
            quoted_column = connection.ops.quote_name(column_name)
            
            # Build SQL statement
            sql_parts = [f'ALTER TABLE {quoted_table} ADD COLUMN {quoted_column} {sql_type}']
            
            if default is not None:
                sql_parts.append(f'DEFAULT {default}')
            
            if not_null:
                sql_parts.append('NOT NULL')
            
            sql = ' '.join(sql_parts)
            cursor.execute(sql)
            return True, None
    except Exception as e:
        return False, str(e)

def sync_all_columns():
    """Sync all missing columns"""
    
    print("=" * 70)
    print("SYNCING DATABASE WITH MODELS")
    print("=" * 70)
    print()
    
    added = []
    errors = []
    
    # 1. Teacher table - ALL fields
    teacher_table = get_actual_table_name('teacher')
    if teacher_table:
        print(f"Checking {teacher_table}...")
        
        # Define all Teacher model fields that might be missing
        teacher_fields = [
            ('permission_level', 'VARCHAR(20)', "'standard'", True),
            ('online_status_updated_at', 'TIMESTAMP', None, False),
            ('photo_url', 'VARCHAR(200)', None, False),  # URLField, nullable
        ]
        
        for field_name, sql_type, default, not_null in teacher_fields:
            if not column_exists(teacher_table, field_name):
                success, error = add_column(teacher_table, field_name, sql_type, default, not_null)
                if success:
                    print(f"  ✓ Added {field_name}")
                    added.append(f"{teacher_table}.{field_name}")
                else:
                    print(f"  ✗ Failed to add {field_name}: {error}")
                    errors.append(f"{teacher_table}.{field_name}: {error}")
            else:
                print(f"  ✓ {field_name} exists")
    else:
        print("  ⚠ Teacher table not found")
    
    # 2. UserProfile table
    profile_table = get_actual_table_name('userprofile')
    if profile_table:
        print(f"\nChecking {profile_table}...")
        
        # force_password_reset
        if not column_exists(profile_table, 'force_password_reset'):
            success, error = add_column(profile_table, 'force_password_reset', 'BOOLEAN', 'FALSE', True)
            if success:
                print("  ✓ Added force_password_reset")
                added.append(f"{profile_table}.force_password_reset")
            else:
                print(f"  ✗ Failed: {error}")
                errors.append(f"{profile_table}.force_password_reset: {error}")
        else:
            print("  ✓ force_password_reset exists")
    else:
        print("  ⚠ UserProfile table not found")
    
    # Summary
    print()
    print("=" * 70)
    if added:
        print(f"SUCCESS! Added {len(added)} column(s):")
        for col in added:
            print(f"  ✓ {col}")
    else:
        print("All columns already exist!")
    
    if errors:
        print(f"\nERRORS ({len(errors)}):")
        for err in errors:
            print(f"  ✗ {err}")
    
    print("=" * 70)
    print()
    
    if added:
        print("✅ Database is now synced with your models!")
        print("You can now:")
        print("  1. Try logging in again")
        print("  2. Run: python manage.py makemigrations (to create migration for these changes)")
        print("  3. Run: python manage.py migrate (to mark migrations as applied)")
    else:
        print("✅ Database already matches your models!")

if __name__ == '__main__':
    try:
        sync_all_columns()
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()

