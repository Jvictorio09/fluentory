"""
Django management command to add missing columns to CourseTeacher table
Run with: python manage.py fix_courseteacher_columns
"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Add missing columns to CourseTeacher table'

    def handle(self, *args, **options):
        # Get actual table name from model (handles case sensitivity)
        from myApp.models import CourseTeacher
        table_name = CourseTeacher._meta.db_table
        
        with connection.cursor() as cursor:
            # Check if table exists (case-insensitive for PostgreSQL)
            if 'postgresql' in connection.vendor:
                # PostgreSQL: check with case-insensitive lookup
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND LOWER(table_name) = LOWER(%s);
                """, [table_name])
                result = cursor.fetchone()
                
                if not result:
                    self.stdout.write(self.style.WARNING(f'Table {table_name} does not exist. Creating it...'))
                    # Create the table with all required columns
                    from myApp.models import Course, Teacher
                    from django.contrib.auth import get_user_model
                    User = get_user_model()
                    
                    # Get foreign key table names
                    course_table = Course._meta.db_table
                    teacher_table = Teacher._meta.db_table
                    user_table = User._meta.db_table
                    
                    quoted_course = connection.ops.quote_name(course_table)
                    quoted_teacher = connection.ops.quote_name(teacher_table)
                    quoted_user = connection.ops.quote_name(user_table)
                    quoted_table = connection.ops.quote_name(table_name)
                    
                    cursor.execute(f"""
                        CREATE TABLE {quoted_table} (
                            id BIGSERIAL PRIMARY KEY,
                            permission_level VARCHAR(20) NOT NULL DEFAULT 'view_only',
                            can_create_live_classes BOOLEAN NOT NULL DEFAULT FALSE,
                            can_manage_schedule BOOLEAN NOT NULL DEFAULT FALSE,
                            requires_booking_approval BOOLEAN NULL,
                            assigned_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
                            course_id BIGINT NOT NULL REFERENCES {quoted_course}(id) ON DELETE CASCADE,
                            teacher_id BIGINT NOT NULL REFERENCES {quoted_teacher}(id) ON DELETE CASCADE,
                            assigned_by_id INTEGER NULL REFERENCES {quoted_user}(id) ON DELETE SET NULL,
                            UNIQUE(course_id, teacher_id)
                        );
                    """)
                    self.stdout.write(self.style.SUCCESS(f'✓ Created table {table_name} with all columns'))
                    actual_table_name = table_name
                else:
                    # Get actual table name (might be different case)
                    actual_table_name = result[0]
                    self.stdout.write(self.style.SUCCESS(f'Found table: {actual_table_name}'))
                
                # Use quoted table name for PostgreSQL (handles case sensitivity)
                quoted_table = connection.ops.quote_name(actual_table_name)
                
                # Check and add can_manage_schedule
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns 
                        WHERE table_schema = 'public'
                        AND LOWER(table_name) = LOWER(%s) 
                        AND LOWER(column_name) = 'can_manage_schedule'
                    );
                """, [table_name])
                column_exists = cursor.fetchone()[0]
                
                if not column_exists:
                    self.stdout.write(f'Adding can_manage_schedule column to {actual_table_name}...')
                    cursor.execute(f"""
                        ALTER TABLE {quoted_table}
                        ADD COLUMN can_manage_schedule BOOLEAN DEFAULT FALSE NOT NULL;
                    """)
                    self.stdout.write(self.style.SUCCESS('✓ Added can_manage_schedule column'))
                else:
                    self.stdout.write('✓ can_manage_schedule column already exists')
                
                # Check and add requires_booking_approval
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns 
                        WHERE table_schema = 'public'
                        AND LOWER(table_name) = LOWER(%s) 
                        AND LOWER(column_name) = 'requires_booking_approval'
                    );
                """, [table_name])
                column_exists = cursor.fetchone()[0]
                
                if not column_exists:
                    self.stdout.write(f'Adding requires_booking_approval column to {actual_table_name}...')
                    cursor.execute(f"""
                        ALTER TABLE {quoted_table}
                        ADD COLUMN requires_booking_approval BOOLEAN NULL;
                    """)
                    self.stdout.write(self.style.SUCCESS('✓ Added requires_booking_approval column'))
                else:
                    self.stdout.write('✓ requires_booking_approval column already exists')
                    
            else:
                # SQLite
                cursor.execute(f"""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='{table_name}';
                """)
                if not cursor.fetchone():
                    self.stdout.write(self.style.WARNING(f'Table {table_name} does not exist. Skipping.'))
                    return
                
                # Check columns
                cursor.execute(f"PRAGMA table_info({table_name});")
                columns = [row[1] for row in cursor.fetchall()]
                
                if 'can_manage_schedule' not in columns:
                    self.stdout.write(f'Adding can_manage_schedule column to {table_name}...')
                    cursor.execute(f"""
                        ALTER TABLE {table_name}
                        ADD COLUMN can_manage_schedule BOOLEAN DEFAULT 0 NOT NULL;
                    """)
                    self.stdout.write(self.style.SUCCESS('✓ Added can_manage_schedule column'))
                else:
                    self.stdout.write('✓ can_manage_schedule column already exists')
                
                if 'requires_booking_approval' not in columns:
                    self.stdout.write(f'Adding requires_booking_approval column to {table_name}...')
                    cursor.execute(f"""
                        ALTER TABLE {table_name}
                        ADD COLUMN requires_booking_approval BOOLEAN NULL;
                    """)
                    self.stdout.write(self.style.SUCCESS('✓ Added requires_booking_approval column'))
                else:
                    self.stdout.write('✓ requires_booking_approval column already exists')
        
        self.stdout.write(self.style.SUCCESS('\n✅ CourseTeacher table columns fixed!'))

