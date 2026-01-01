"""
Check what tables actually exist in the database
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myProject.settings')
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    # Check what tables exist
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name LIKE 'myapp_%'
        ORDER BY table_name;
    """)
    
    tables = [row[0] for row in cursor.fetchall()]
    
    print("Existing myApp tables in database:")
    if tables:
        for table in tables:
            print(f"  ✓ {table}")
    else:
        print("  ❌ No myApp tables found in database!")
    
    # Check specifically for teacher table
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name IN ('myapp_teacher', 'myApp_teacher');
    """)
    
    teacher_table = cursor.fetchone()
    if teacher_table:
        print(f"\n✓ Teacher table exists: {teacher_table[0]}")
        
        # Check columns in teacher table
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = %s
            ORDER BY column_name;
        """, [teacher_table[0]])
        
        columns = [row[0] for row in cursor.fetchall()]
        print(f"\nColumns in {teacher_table[0]}:")
        for col in columns:
            print(f"  - {col}")
            
        if 'online_status_updated_at' in columns:
            print("\n✅ online_status_updated_at column EXISTS")
        else:
            print("\n❌ online_status_updated_at column MISSING")
    else:
        print("\n❌ Teacher table does NOT exist!")

