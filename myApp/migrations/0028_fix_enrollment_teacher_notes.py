# Generated manually to fix teacher_notes NOT NULL constraint

from django.db import migrations, models
from django.db import connection


def backfill_teacher_notes(apps, schema_editor):
    """Set empty string for any NULL teacher_notes values - only if table exists"""
    try:
        with connection.cursor() as cursor:
            # Check if table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'myapp_enrollment'
                );
            """)
            table_exists = cursor.fetchone()[0]
            
            if table_exists:
                # Check if column exists
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_schema = 'public' 
                        AND table_name = 'myapp_enrollment'
                        AND column_name = 'teacher_notes'
                    );
                """)
                column_exists = cursor.fetchone()[0]
                
                if column_exists:
                    # Backfill NULL values
                    cursor.execute("""
                        UPDATE myapp_enrollment 
                        SET teacher_notes = '' 
                        WHERE teacher_notes IS NULL;
                    """)
                    
                    # Set database default
                    cursor.execute("""
                        ALTER TABLE myapp_enrollment 
                        ALTER COLUMN teacher_notes SET DEFAULT '';
                    """)
    except Exception:
        # If anything fails, just skip - field might not exist yet
        pass


def reverse_backfill(apps, schema_editor):
    """Reverse operation - not needed but required for migration"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('myApp', '0027_add_teacher_photo_url'),
    ]

    operations = [
        # Use SeparateDatabaseAndState because field exists in DB but not in Django state
        migrations.SeparateDatabaseAndState(
            # Database operations - update the actual database
            database_operations=[
                migrations.RunPython(backfill_teacher_notes, reverse_backfill),
            ],
            # State operations - update Django's migration state
            state_operations=[
                migrations.AddField(
                    model_name='enrollment',
                    name='teacher_notes',
                    field=models.TextField(blank=True, default='', help_text='Teacher notes (internal)'),
                ),
            ],
        ),
    ]

