"""
Quick script to add scheduled_end column to LiveClassSession table
Run with: python add_scheduled_end_column.py
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myProject.settings')
django.setup()

from django.db import connection

def add_scheduled_end_column():
    table_name = 'myApp_liveclasssession'
    
    with connection.cursor() as cursor:
        # Check if column exists
        if 'postgresql' in connection.vendor:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_schema = 'public'
                    AND LOWER(table_name) = LOWER(%s) 
                    AND LOWER(column_name) = 'scheduled_end'
                );
            """, [table_name])
            column_exists = cursor.fetchone()[0]
            
            if column_exists:
                print(f"✓ Column scheduled_end already exists in {table_name}")
                return
            
            # Get actual table name (case-sensitive)
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND LOWER(table_name) = LOWER(%s);
            """, [table_name])
            result = cursor.fetchone()
            
            if not result:
                print(f"✗ Table {table_name} does not exist!")
                return
            
            actual_table_name = result[0]
            quoted_table = connection.ops.quote_name(actual_table_name)
            
            print(f"Adding scheduled_end column to {actual_table_name}...")
            cursor.execute(f"""
                ALTER TABLE {quoted_table}
                ADD COLUMN scheduled_end TIMESTAMP WITH TIME ZONE NULL;
            """)
            print(f"✓ Successfully added scheduled_end column to {actual_table_name}")
        else:
            # SQLite
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'scheduled_end' in columns:
                print(f"✓ Column scheduled_end already exists in {table_name}")
                return
            
            print(f"Adding scheduled_end column to {table_name}...")
            cursor.execute(f"""
                ALTER TABLE {table_name}
                ADD COLUMN scheduled_end DATETIME NULL;
            """)
            print(f"✓ Successfully added scheduled_end column to {table_name}")

if __name__ == '__main__':
    try:
        add_scheduled_end_column()
        print("\n✅ Done!")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

