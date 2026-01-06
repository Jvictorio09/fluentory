# Generated manually to fix column name mismatch
from django.db import migrations


def fix_column_name(apps, schema_editor):
    """
    Fix CourseTeacher table: rename can_host_live to can_create_live_classes
    Only runs if table exists - safely handles case where table doesn't exist yet
    """
    from django.db import connection
    
    try:
        vendor = connection.vendor
        
        if 'postgresql' in vendor:
            # Use DO block to safely check and rename without errors if table doesn't exist
            with connection.cursor() as cursor:
                cursor.execute("""
                    DO $$ 
                    DECLARE
                        tbl_name TEXT;
                        has_old_col BOOLEAN;
                        has_new_col BOOLEAN;
                    BEGIN
                        -- Find table (case-insensitive)
                        SELECT table_name INTO tbl_name
                        FROM information_schema.tables
                        WHERE table_schema = 'public'
                        AND LOWER(table_name) = LOWER('myapp_courseteacher')
                        LIMIT 1;
                        
                        -- Only proceed if table exists
                        IF tbl_name IS NOT NULL THEN
                            -- Check if can_host_live exists
                            SELECT EXISTS (
                                SELECT 1 FROM information_schema.columns
                                WHERE table_schema = 'public'
                                AND table_name = tbl_name
                                AND column_name = 'can_host_live'
                            ) INTO has_old_col;
                            
                            -- Check if can_create_live_classes exists
                            SELECT EXISTS (
                                SELECT 1 FROM information_schema.columns
                                WHERE table_schema = 'public'
                                AND table_name = tbl_name
                                AND column_name = 'can_create_live_classes'
                            ) INTO has_new_col;
                            
                            IF has_old_col AND NOT has_new_col THEN
                                -- Rename the column
                                EXECUTE format('ALTER TABLE %I RENAME COLUMN can_host_live TO can_create_live_classes;', tbl_name);
                            ELSIF has_old_col AND has_new_col THEN
                                -- Both exist - copy data and drop old
                                EXECUTE format('UPDATE %I SET can_create_live_classes = can_host_live WHERE can_create_live_classes IS NULL OR can_create_live_classes = FALSE;', tbl_name);
                                EXECUTE format('ALTER TABLE %I DROP COLUMN can_host_live;', tbl_name);
                            END IF;
                        END IF;
                    END $$;
                """)
    except Exception:
        # Silently fail if table doesn't exist - that's fine
        pass


def reverse_fix(apps, schema_editor):
    """Reverse migration"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('myApp', '0013_create_teacheravailability_table'),
    ]

    operations = [
        migrations.RunPython(fix_column_name, reverse_fix),
    ]


