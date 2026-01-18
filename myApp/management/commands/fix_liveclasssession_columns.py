"""
Django management command to add missing columns to LiveClassSession table
Run with: python manage.py fix_liveclasssession_columns
"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Add missing columns to LiveClassSession table'

    def handle(self, *args, **options):
        # Get actual table name from model (handles case sensitivity)
        from myApp.models import LiveClassSession
        table_name = LiveClassSession._meta.db_table
        
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
                    self.stdout.write(self.style.WARNING(f'Table {table_name} does not exist. Skipping.'))
                    return
                
                # Get actual table name (might be different case)
                actual_table_name = result[0]
                self.stdout.write(self.style.SUCCESS(f'Found table: {actual_table_name}'))
                
                # Use quoted table name for PostgreSQL (handles case sensitivity)
                quoted_table = connection.ops.quote_name(actual_table_name)
                
                # Check and add scheduled_end
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns 
                        WHERE table_schema = 'public'
                        AND LOWER(table_name) = LOWER(%s) 
                        AND LOWER(column_name) = 'scheduled_end'
                    );
                """, [table_name])
                column_exists = cursor.fetchone()[0]
                
                if not column_exists:
                    self.stdout.write(f'Adding scheduled_end column to {actual_table_name}...')
                    cursor.execute(f"""
                        ALTER TABLE {quoted_table}
                        ADD COLUMN scheduled_end TIMESTAMP WITH TIME ZONE NULL;
                    """)
                    self.stdout.write(self.style.SUCCESS('✓ Added scheduled_end column'))
                else:
                    self.stdout.write('✓ scheduled_end column already exists')
                
                # Check and add other potentially missing columns
                columns_to_check = [
                    ('start_at_utc', 'TIMESTAMP WITH TIME ZONE NULL'),
                    ('end_at_utc', 'TIMESTAMP WITH TIME ZONE NULL'),
                    ('timezone_snapshot', 'VARCHAR(50) DEFAULT \'\''),
                    ('meeting_provider', 'VARCHAR(20) DEFAULT \'zoom\''),
                    ('meeting_passcode', 'VARCHAR(50) DEFAULT \'\''),
                    ('total_seats', 'INTEGER NOT NULL DEFAULT 10'),
                    ('seats_taken', 'INTEGER NOT NULL DEFAULT 0'),
                    ('enable_waitlist', 'BOOLEAN NOT NULL DEFAULT FALSE'),
                    ('reminder_sent', 'BOOLEAN NOT NULL DEFAULT FALSE'),
                ]
                
                for col_name, col_type in columns_to_check:
                    cursor.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.columns 
                            WHERE table_schema = 'public'
                            AND LOWER(table_name) = LOWER(%s) 
                            AND LOWER(column_name) = %s
                        );
                    """, [table_name, col_name])
                    column_exists = cursor.fetchone()[0]
                    
                    if not column_exists:
                        self.stdout.write(f'Adding {col_name} column to {actual_table_name}...')
                        try:
                            cursor.execute(f"""
                                ALTER TABLE {quoted_table}
                                ADD COLUMN {col_name} {col_type};
                            """)
                            self.stdout.write(self.style.SUCCESS(f'✓ Added {col_name} column'))
                        except Exception as e:
                            self.stdout.write(self.style.WARNING(f'Could not add {col_name}: {e}'))
                    else:
                        self.stdout.write(f'✓ {col_name} column already exists')
                    
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
                
                if 'scheduled_end' not in columns:
                    self.stdout.write(f'Adding scheduled_end column to {table_name}...')
                    cursor.execute(f"""
                        ALTER TABLE {table_name}
                        ADD COLUMN scheduled_end DATETIME NULL;
                    """)
                    self.stdout.write(self.style.SUCCESS('✓ Added scheduled_end column'))
                else:
                    self.stdout.write('✓ scheduled_end column already exists')
        
        self.stdout.write(self.style.SUCCESS('\n✅ LiveClassSession table columns fixed!'))

