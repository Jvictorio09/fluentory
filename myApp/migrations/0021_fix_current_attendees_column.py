# Generated manually to fix current_attendees column mapping and default
# This migration is idempotent: it does NOT create the column, only backfills data and sets defaults

from django.db import migrations, models


def ensure_current_attendees_default(apps, schema_editor):
    """Backfill NULL values and ensure database-level default for existing current_attendees column"""
    # Use Django ORM for data updates to avoid SQL quoting issues
    LiveClassSession = apps.get_model('myApp', 'LiveClassSession')
    
    # Step 1: Backfill any NULL values to 0 using Django ORM
    # Note: Since seats_taken maps to current_attendees via db_column, we can update directly
    try:
        # Use raw SQL with proper quoting for case-sensitive table name
        from django.db import connection
        with connection.cursor() as cursor:
            # Backfill NULL values
            cursor.execute('UPDATE "myApp_liveclasssession" SET current_attendees = 0 WHERE current_attendees IS NULL;')
            
            # Set database-level default to 0 (idempotent)
            cursor.execute('ALTER TABLE "myApp_liveclasssession" ALTER COLUMN current_attendees SET DEFAULT 0;')
            
            # Ensure NOT NULL constraint exists (idempotent)
            cursor.execute('ALTER TABLE "myApp_liveclasssession" ALTER COLUMN "current_attendees" SET NOT NULL;')
    except Exception as e:
        # If column doesn't exist or operation fails, log but don't crash
        # The column should exist, but be graceful if it doesn't
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Migration 0021: Could not update current_attendees column: {e}")
        # Don't re-raise - allow migration to continue


def reverse_ensure_current_attendees_default(apps, schema_editor):
    """Reverse migration - no action needed"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('myApp', '0020_add_unique_constraints_to_liveclassbooking'),
    ]

    operations = [
        # Step 1: Backfill data and set database defaults (database operations only)
        migrations.RunPython(
            ensure_current_attendees_default,
            reverse_ensure_current_attendees_default
        ),
        # Step 2: Update Django's state to know that seats_taken maps to current_attendees
        # Use SeparateDatabaseAndState so we ONLY update Django's state, NO database schema changes
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name='liveclasssession',
                    name='seats_taken',
                    field=models.PositiveIntegerField(
                        default=0,
                        help_text='Cached count of confirmed bookings (updated via signal)',
                        db_column='current_attendees'
                    ),
                ),
            ],
            database_operations=[
                # NO database operations - column already exists, we just updated data/defaults above
                # This is purely a state change so Django knows about the db_column mapping
            ],
        ),
    ]

