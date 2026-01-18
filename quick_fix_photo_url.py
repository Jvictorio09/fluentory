"""
Quick fix for photo_url column
Run this immediately to fix the login error
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myProject.settings')
django.setup()

from django.db import connection

def fix_photo_url():
    """Add photo_url column to teacher table"""
    with connection.cursor() as cursor:
        # Check if column exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND LOWER(table_name) = LOWER('myapp_teacher')
                AND LOWER(column_name) = LOWER('photo_url')
            );
        """)
        exists = cursor.fetchone()[0]
        
        if exists:
            print("✓ photo_url column already exists")
            return
        
        # Get actual table name
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND LOWER(table_name) = LOWER('myapp_teacher')
            LIMIT 1;
        """)
        result = cursor.fetchone()
        if not result:
            print("✗ Teacher table not found")
            return
        
        table_name = result[0]
        quoted_table = connection.ops.quote_name(table_name)
        
        # Add column
        try:
            cursor.execute(f'ALTER TABLE {quoted_table} ADD COLUMN photo_url VARCHAR(200)')
            print(f"✓ Successfully added photo_url column to {table_name}")
        except Exception as e:
            print(f"✗ Error: {e}")

if __name__ == '__main__':
    fix_photo_url()

