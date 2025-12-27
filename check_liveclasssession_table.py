"""
Check LiveClassSession table structure
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myProject.settings')
django.setup()

from django.db import connection
from myApp.models import LiveClassSession

print("=" * 70)
print("Checking LiveClassSession table...")
print("=" * 70)

# Get table name from model
print(f"\nModel table name: {LiveClassSession._meta.db_table}")

# Check actual columns in database
cursor = connection.cursor()
vendor = connection.vendor

if 'postgresql' in vendor:
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'myApp_liveclasssession'
        ORDER BY ordinal_position;
    """)
    print(f"\nActual columns in database:")
    for row in cursor.fetchall():
        print(f"  - {row[0]}")

# Check model fields
print(f"\nModel fields (from LiveClassSession._meta.get_fields()):")
for field in LiveClassSession._meta.get_fields():
    if hasattr(field, 'column'):
        print(f"  - {field.name} -> {field.column} ({field.__class__.__name__})")
    elif hasattr(field, 'related_model'):
        print(f"  - {field.name} -> {field.name}_id (ForeignKey to {field.related_model.__name__})")

cursor.close()


