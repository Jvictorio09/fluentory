# Generated manually to add reminder_sent field to LiveClassSession model
# This migration is idempotent: it does NOT create the column (already exists in DB), only backfills data and sets defaults

from django.db import migrations, models


def ensure_reminder_sent_default(apps, schema_editor):
    """Backfill NULL values and ensure database-level default for existing reminder_sent column"""
    # Use Django ORM for data updates to avoid SQL quoting issues
    LiveClassSession = apps.get_model('myApp', 'LiveClassSession')
    
    # Step 1: Backfill any NULL values to False using Django ORM
    try:
        # Use raw SQL with proper quoting for case-sensitive table name
        from django.db import connection
        with connection.cursor() as cursor:
            # Backfill NULL values
            cursor.execute('UPDATE "myApp_liveclasssession" SET reminder_sent = FALSE WHERE reminder_sent IS NULL;')
            
            # Set database-level default to False (idempotent)
            cursor.execute('ALTER TABLE "myApp_liveclasssession" ALTER COLUMN reminder_sent SET DEFAULT FALSE;')
            
            # Ensure NOT NULL constraint exists (idempotent)
            cursor.execute('ALTER TABLE "myApp_liveclasssession" ALTER COLUMN "reminder_sent" SET NOT NULL;')
    except Exception as e:
        # If column doesn't exist or operation fails, log but don't crash
        # The column should exist, but be graceful if it doesn't
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Migration 0022: Could not update reminder_sent column: {e}")
        # Don't re-raise - allow migration to continue


def reverse_ensure_reminder_sent_default(apps, schema_editor):
    """Reverse migration - no action needed"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('myApp', '0021_fix_current_attendees_column'),
    ]

    operations = [
        # Step 1: Backfill data and set database defaults (database operations only)
        migrations.RunPython(
            ensure_reminder_sent_default,
            reverse_ensure_reminder_sent_default
        ),
        # Step 2: Update Django's state to know about the reminder_sent field
        # Use SeparateDatabaseAndState so we ONLY update Django's state, NO database schema changes
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='liveclasssession',
                    name='reminder_sent',
                    field=models.BooleanField(
                        default=False,
                        help_text='Whether reminder notification has been sent to attendees'
                    ),
                ),
            ],
            database_operations=[
                # NO database operations - column already exists, we just updated data/defaults above
                # This is purely a state change so Django knows about the field
            ],
        ),
    ]

