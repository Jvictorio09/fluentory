# Generated manually to fix missing online_status_updated_at column
# Migration 0010 was faked, so this column was never actually added to the database
# Note: Table name is "myApp_teacher" (with capital A and P), not "myapp_teacher"

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('myApp', '0010_enhance_teacher_availability'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'myApp_teacher') THEN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'myApp_teacher' 
                        AND column_name = 'online_status_updated_at'
                    ) THEN
                        ALTER TABLE "myApp_teacher" ADD COLUMN online_status_updated_at TIMESTAMP NULL;
                    END IF;
                END IF;
            END $$;
            """,
            reverse_sql="ALTER TABLE \"myApp_teacher\" DROP COLUMN IF EXISTS online_status_updated_at;",
        ),
    ]

