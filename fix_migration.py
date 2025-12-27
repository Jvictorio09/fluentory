"""
Script to fake the migration if tables already exist
Run this if you get "relation already exists" errors
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myProject.settings')
django.setup()

from django.core.management import call_command
from django.db import connection

# Check which tables exist
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name LIKE 'myapp_%'
        ORDER BY table_name;
    """)
    existing_tables = [row[0] for row in cursor.fetchall()]
    
print("Existing tables:", existing_tables)

# Check if the problematic tables exist
required_tables = [
    'myapp_teacher',
    'myapp_courseteacher', 
    'myapp_liveclasssession',
    'myapp_courseannouncement',
    'myapp_studentmessage'
]

all_exist = all(table in existing_tables for table in required_tables)

if all_exist:
    print("\nAll required tables exist. Faking migration 0004...")
    try:
        call_command('migrate', 'myApp', '0004', '--fake')
        print("Migration 0004 faked successfully!")
    except Exception as e:
        print(f"Error: {e}")
else:
    print("\nNot all tables exist. Missing tables:")
    for table in required_tables:
        if table not in existing_tables:
            print(f"  - {table}")
    print("\nYou may need to run the migration normally or fix table structure.")





