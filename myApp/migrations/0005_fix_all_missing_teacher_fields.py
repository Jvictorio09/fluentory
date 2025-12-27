# Generated manually to fix ALL missing fields from migration 0004
from django.db import migrations
from django.conf import settings


def add_all_missing_columns(apps, schema_editor):
    """
    Safely add ALL missing columns from migration 0004.
    Only adds if they don't exist.
    """
    from django.db import connection
    
    cursor = connection.cursor()
    
    try:
        vendor = connection.vendor
        
        if 'postgresql' in vendor:
            # 1. myapp_teacher.bio
            cursor.execute("""
                DO $$ 
                BEGIN 
                    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'myapp_teacher') THEN
                        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name='myapp_teacher' AND column_name='bio') THEN
                            ALTER TABLE myapp_teacher ADD COLUMN bio TEXT;
                        END IF;
                    END IF;
                END $$;
            """)
            
            # 2. myapp_courseteacher.can_create_live_classes
            cursor.execute("""
                DO $$ 
                BEGIN 
                    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'myapp_courseteacher') THEN
                        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name='myapp_courseteacher' AND column_name='can_create_live_classes') THEN
                            ALTER TABLE myapp_courseteacher ADD COLUMN can_create_live_classes BOOLEAN DEFAULT FALSE;
                        END IF;
                    END IF;
                END $$;
            """)
            
            # 3. myapp_studentmessage.teacher_id
            cursor.execute("""
                DO $$ 
                BEGIN 
                    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'myapp_studentmessage') THEN
                        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name='myapp_studentmessage' AND column_name='teacher_id') THEN
                            ALTER TABLE myapp_studentmessage ADD COLUMN teacher_id BIGINT;
                            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'myapp_teacher') THEN
                                ALTER TABLE myapp_studentmessage 
                                    ADD CONSTRAINT myapp_studentmessage_teacher_id_fkey 
                                    FOREIGN KEY (teacher_id) REFERENCES myapp_teacher(id) ON DELETE CASCADE;
                                CREATE INDEX IF NOT EXISTS myapp_studentmessage_teacher_id_idx ON myapp_studentmessage(teacher_id);
                            END IF;
                        END IF;
                    END IF;
                END $$;
            """)
        elif 'sqlite' in vendor:
            # 1. myapp_teacher.bio
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='myapp_teacher';")
            if cursor.fetchone():
                cursor.execute("PRAGMA table_info(myapp_teacher);")
                columns = [row[1] for row in cursor.fetchall()]
                if 'bio' not in columns:
                    cursor.execute("ALTER TABLE myapp_teacher ADD COLUMN bio TEXT;")
            
            # 2. myapp_courseteacher.can_create_live_classes
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='myapp_courseteacher';")
            if cursor.fetchone():
                cursor.execute("PRAGMA table_info(myapp_courseteacher);")
                columns = [row[1] for row in cursor.fetchall()]
                if 'can_create_live_classes' not in columns:
                    cursor.execute("ALTER TABLE myapp_courseteacher ADD COLUMN can_create_live_classes BOOLEAN DEFAULT 0;")
            
            # 3. myapp_studentmessage.teacher_id
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='myapp_studentmessage';")
            if cursor.fetchone():
                cursor.execute("PRAGMA table_info(myapp_studentmessage);")
                columns = [row[1] for row in cursor.fetchall()]
                if 'teacher_id' not in columns:
                    cursor.execute("ALTER TABLE myapp_studentmessage ADD COLUMN teacher_id INTEGER REFERENCES myapp_teacher(id);")
    except Exception as e:
        # Log but don't fail - columns might already exist
        print(f"Note: {e}")
    finally:
        cursor.close()


def reverse_add_missing_columns(apps, schema_editor):
    """Reverse migration - don't remove columns to avoid data loss"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('myApp', '0004_teacher_studentmessage_liveclasssession_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Use RunPython to safely add all missing columns
        migrations.RunPython(
            add_all_missing_columns,
            reverse_code=reverse_add_missing_columns,
        ),
    ]
