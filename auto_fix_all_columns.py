"""
AUTOMATIC FIX FOR ALL MISSING COLUMNS
This script automatically detects and adds ALL missing columns by comparing
your Django models with the actual database schema.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myProject.settings')
django.setup()

from django.db import connection
from myApp.models import Teacher, UserProfile

def get_table_name(model):
    """Get actual database table name"""
    return model._meta.db_table

def get_db_columns(table_name):
    """Get all columns that exist in database"""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND LOWER(table_name) = LOWER(%s)
        """, [table_name])
        return {row[0].lower() for row in cursor.fetchall()}

def get_model_columns(model):
    """Get all column names from model"""
    columns = set()
    for field in model._meta.get_fields():
        if hasattr(field, 'column'):
            columns.add(field.column.lower())
        elif hasattr(field, 'attname'):
            columns.add(field.attname.lower())
    return columns

def get_field_sql_type(field):
    """Convert Django field to SQL type"""
    from django.db import models
    
    if isinstance(field, models.CharField):
        return f'VARCHAR({field.max_length})'
    elif isinstance(field, models.TextField):
        return 'TEXT'
    elif isinstance(field, models.BooleanField):
        return 'BOOLEAN'
    elif isinstance(field, models.IntegerField):
        return 'INTEGER'
    elif isinstance(field, models.PositiveIntegerField):
        return 'INTEGER'
    elif isinstance(field, models.DateTimeField):
        return 'TIMESTAMP'
    elif isinstance(field, models.DateField):
        return 'DATE'
    elif isinstance(field, models.URLField):
        return 'VARCHAR(200)'
    elif isinstance(field, models.EmailField):
        return 'VARCHAR(254)'
    elif isinstance(field, models.DecimalField):
        return f'DECIMAL({field.max_digits},{field.decimal_places})'
    elif isinstance(field, models.JSONField):
        return 'JSONB'
    elif isinstance(field, models.UUIDField):
        return 'UUID'
    else:
        return 'TEXT'  # Default fallback

def add_missing_column(table_name, field):
    """Add a single missing column"""
    try:
        with connection.cursor() as cursor:
            quoted_table = connection.ops.quote_name(table_name)
            quoted_column = connection.ops.quote_name(field.column)
            sql_type = get_field_sql_type(field)
            
            sql = f'ALTER TABLE {quoted_table} ADD COLUMN {quoted_column} {sql_type}'
            
            # Add default if field has one
            if hasattr(field, 'default') and field.default is not None:
                if field.default != django.db.models.NOT_PROVIDED:
                    if callable(field.default):
                        # For callable defaults, use a reasonable value
                        if isinstance(field, models.BooleanField):
                            default_val = 'FALSE'
                        elif isinstance(field, models.IntegerField):
                            default_val = '0'
                        else:
                            default_val = "''"
                    else:
                        if isinstance(field.default, bool):
                            default_val = 'TRUE' if field.default else 'FALSE'
                        elif isinstance(field.default, (int, float)):
                            default_val = str(field.default)
                        else:
                            default_val = f"'{field.default}'"
                    sql += f' DEFAULT {default_val}'
            
            # Add NOT NULL if field is not nullable
            if not field.null:
                sql += ' NOT NULL'
            
            cursor.execute(sql)
            return True, None
    except Exception as e:
        return False, str(e)

def fix_model_columns(model):
    """Fix all missing columns for a model"""
    table_name = get_table_name(model)
    db_columns = get_db_columns(table_name)
    
    print(f"\nChecking {table_name}...")
    added = []
    errors = []
    
    for field in model._meta.get_fields():
        if not hasattr(field, 'column'):
            continue
        
        column_name = field.column.lower()
        if column_name not in db_columns:
            print(f"  Missing: {field.name} ({field.column})")
            success, error = add_missing_column(table_name, field)
            if success:
                print(f"    ✓ Added {field.column}")
                added.append(field.column)
            else:
                print(f"    ✗ Failed: {error}")
                errors.append(f"{field.column}: {error}")
        else:
            print(f"  ✓ {field.column} exists")
    
    return added, errors

def main():
    """Main function"""
    print("=" * 70)
    print("AUTOMATIC COLUMN FIX")
    print("=" * 70)
    print()
    print("This will add ALL missing columns to match your models...")
    print()
    
    all_added = []
    all_errors = []
    
    # Fix Teacher model
    print("=" * 70)
    print("FIXING TEACHER MODEL")
    print("=" * 70)
    added, errors = fix_model_columns(Teacher)
    all_added.extend(added)
    all_errors.extend(errors)
    
    # Fix UserProfile model
    print()
    print("=" * 70)
    print("FIXING USERPROFILE MODEL")
    print("=" * 70)
    added, errors = fix_model_columns(UserProfile)
    all_added.extend(added)
    all_errors.extend(errors)
    
    # Summary
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    if all_added:
        print(f"✓ Added {len(all_added)} column(s):")
        for col in all_added:
            print(f"  - {col}")
    else:
        print("✓ All columns already exist!")
    
    if all_errors:
        print(f"\n✗ {len(all_errors)} error(s):")
        for err in all_errors:
            print(f"  - {err}")
    
    print("=" * 70)
    print()
    if all_added:
        print("✅ Database is now synced!")
        print("Try logging in again.")
    else:
        print("✅ Database already matches models!")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()

