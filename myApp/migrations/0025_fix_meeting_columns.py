# Fix for meeting_link and meeting_url columns
# Database has both columns as NOT NULL, we need to ensure both are set

from django.db import migrations


def sync_meeting_columns(apps, schema_editor):
    """Sync meeting_url with meeting_link for existing rows"""
    from django.db import connection
    with connection.cursor() as cursor:
        # Set meeting_url = meeting_link for all rows where meeting_url is NULL
        cursor.execute('''
            UPDATE "myApp_liveclasssession" 
            SET "meeting_url" = COALESCE("meeting_link", '') 
            WHERE "meeting_url" IS NULL OR "meeting_url" = '';
        ''')
        # Set meeting_link = meeting_url for all rows where meeting_link is NULL
        cursor.execute('''
            UPDATE "myApp_liveclasssession" 
            SET "meeting_link" = COALESCE("meeting_url", '') 
            WHERE "meeting_link" IS NULL OR "meeting_link" = '';
        ''')


def reverse_sync_meeting_columns(apps, schema_editor):
    """Reverse migration - no action needed"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('myApp', '0024_alter_liveclasssession_meeting_link'),
    ]

    operations = [
        migrations.RunPython(
            sync_meeting_columns,
            reverse_sync_meeting_columns
        ),
        # Set defaults for all duplicate columns to ensure they're never NULL during INSERT
        migrations.RunSQL(
            sql='''
                -- Set defaults for meeting columns
                ALTER TABLE "myApp_liveclasssession" 
                ALTER COLUMN "meeting_link" SET DEFAULT '';
                ALTER TABLE "myApp_liveclasssession" 
                ALTER COLUMN "meeting_url" SET DEFAULT '';
                -- Set defaults for seats columns
                ALTER TABLE "myApp_liveclasssession" 
                ALTER COLUMN "seats_taken" SET DEFAULT 0;
                ALTER TABLE "myApp_liveclasssession" 
                ALTER COLUMN "current_attendees" SET DEFAULT 0;
                -- Sync existing data for meeting columns
                UPDATE "myApp_liveclasssession" 
                SET "meeting_url" = COALESCE("meeting_link", '') 
                WHERE "meeting_url" IS NULL;
                UPDATE "myApp_liveclasssession" 
                SET "meeting_link" = COALESCE("meeting_url", '') 
                WHERE "meeting_link" IS NULL;
                -- Sync existing data for seats columns
                UPDATE "myApp_liveclasssession" 
                SET "current_attendees" = COALESCE("seats_taken", 0) 
                WHERE "current_attendees" IS NULL;
                UPDATE "myApp_liveclasssession" 
                SET "seats_taken" = COALESCE("current_attendees", 0) 
                WHERE "seats_taken" IS NULL;
            ''',
            reverse_sql='''
                ALTER TABLE "myApp_liveclasssession" ALTER COLUMN "meeting_link" DROP DEFAULT;
                ALTER TABLE "myApp_liveclasssession" ALTER COLUMN "meeting_url" DROP DEFAULT;
                ALTER TABLE "myApp_liveclasssession" ALTER COLUMN "seats_taken" DROP DEFAULT;
                ALTER TABLE "myApp_liveclasssession" ALTER COLUMN "current_attendees" DROP DEFAULT;
            ''',
        ),
    ]

