# Migration to create TeacherAvailability table if it doesn't exist
# This handles the case where migration 0009 was faked or the table was dropped

from django.db import migrations, models
import django.db.models.deletion


def create_teacheravailability_table(apps, schema_editor):
    """Create TeacherAvailability table if it doesn't exist"""
    from django.db import connection
    
    with connection.cursor() as cursor:
        # Check if table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'myApp_teacheravailability'
            );
        """)
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            # Create the table
            cursor.execute("""
                CREATE TABLE "myApp_teacheravailability" (
                    id BIGSERIAL PRIMARY KEY,
                    day_of_week INTEGER,
                    start_time TIME,
                    end_time TIME,
                    timezone VARCHAR(50) DEFAULT 'UTC',
                    valid_from DATE,
                    valid_until DATE,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    course_id BIGINT,
                    teacher_id BIGINT NOT NULL,
                    slot_type VARCHAR(20) DEFAULT 'recurring',
                    start_datetime TIMESTAMP WITH TIME ZONE,
                    end_datetime TIMESTAMP WITH TIME ZONE,
                    is_blocked BOOLEAN DEFAULT FALSE,
                    blocked_reason TEXT,
                    google_calendar_event_id VARCHAR(200),
                    CONSTRAINT myApp_teacheravailability_teacher_id_fkey 
                        FOREIGN KEY (teacher_id) REFERENCES "myApp_teacher"(id) ON DELETE CASCADE,
                    CONSTRAINT myApp_teacheravailability_course_id_fkey 
                        FOREIGN KEY (course_id) REFERENCES "myApp_course"(id) ON DELETE CASCADE
                );
            """)
            
            # Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS myApp_teacheravailability_teacher_id_idx 
                ON "myApp_teacheravailability"(teacher_id);
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS myApp_teacheravailability_course_id_idx 
                ON "myApp_teacheravailability"(course_id);
            """)


def reverse_create_table(apps, schema_editor):
    """Reverse migration - drop table"""
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute('DROP TABLE IF EXISTS "myApp_teacheravailability" CASCADE;')


class Migration(migrations.Migration):

    dependencies = [
        ('myApp', '0012_add_teacher_permission_level'),
    ]

    operations = [
        # Create table using raw SQL
        migrations.RunSQL(
            sql="""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'myApp_teacheravailability'
                    ) THEN
                        CREATE TABLE "myApp_teacheravailability" (
                            id BIGSERIAL PRIMARY KEY,
                            day_of_week INTEGER,
                            start_time TIME,
                            end_time TIME,
                            timezone VARCHAR(50) DEFAULT 'UTC',
                            valid_from DATE,
                            valid_until DATE,
                            is_active BOOLEAN DEFAULT TRUE,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                            course_id BIGINT,
                            teacher_id BIGINT NOT NULL,
                            slot_type VARCHAR(20) DEFAULT 'recurring',
                            start_datetime TIMESTAMP WITH TIME ZONE,
                            end_datetime TIMESTAMP WITH TIME ZONE,
                            is_blocked BOOLEAN DEFAULT FALSE,
                            blocked_reason TEXT,
                            google_calendar_event_id VARCHAR(200),
                            CONSTRAINT myApp_teacheravailability_teacher_id_fkey 
                                FOREIGN KEY (teacher_id) REFERENCES "myApp_teacher"(id) ON DELETE CASCADE,
                            CONSTRAINT myApp_teacheravailability_course_id_fkey 
                                FOREIGN KEY (course_id) REFERENCES "myApp_course"(id) ON DELETE CASCADE
                        );
                        
                        CREATE INDEX IF NOT EXISTS myApp_teacheravailability_teacher_id_idx 
                        ON "myApp_teacheravailability"(teacher_id);
                        
                        CREATE INDEX IF NOT EXISTS myApp_teacheravailability_course_id_idx 
                        ON "myApp_teacheravailability"(course_id);
                    END IF;
                END $$;
            """,
            reverse_sql='DROP TABLE IF EXISTS "myApp_teacheravailability" CASCADE;',
        ),
        # Update model state so Django knows about the table
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name='TeacherAvailability',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('slot_type', models.CharField(choices=[('recurring', 'Recurring (Weekly)'), ('one_time', 'One-Time Slot')], default='recurring', max_length=20)),
                        ('day_of_week', models.IntegerField(blank=True, choices=[(0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'), (3, 'Thursday'), (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday')], null=True)),
                        ('start_time', models.TimeField(blank=True, null=True)),
                        ('end_time', models.TimeField(blank=True, null=True)),
                        ('start_datetime', models.DateTimeField(blank=True, null=True)),
                        ('end_datetime', models.DateTimeField(blank=True, null=True)),
                        ('timezone', models.CharField(default='UTC', max_length=50)),
                        ('valid_from', models.DateField(blank=True, null=True)),
                        ('valid_until', models.DateField(blank=True, null=True)),
                        ('is_active', models.BooleanField(default=True)),
                        ('is_blocked', models.BooleanField(default=False, help_text='Block this time slot from being booked')),
                        ('blocked_reason', models.TextField(blank=True, help_text='Reason for blocking this slot')),
                        ('google_calendar_event_id', models.CharField(blank=True, max_length=200)),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                        ('updated_at', models.DateTimeField(auto_now=True)),
                        ('course', models.ForeignKey(blank=True, help_text='Leave blank for all courses', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='teacher_availability', to='myApp.course')),
                        ('teacher', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='availability_slots', to='myApp.teacher')),
                    ],
                    options={
                        'verbose_name_plural': 'Teacher Availabilities',
                        'ordering': ['day_of_week', 'start_time', 'start_datetime'],
                    },
                ),
            ],
        ),
    ]

