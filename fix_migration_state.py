"""
Fix broken migration state by creating missing tables directly
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myProject.settings')
django.setup()

from django.db import connection
from django.core.management import call_command

def check_table_exists(table_name):
    """Check if a table exists"""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND LOWER(table_name) = LOWER(%s)
            );
        """, [table_name])
        return cursor.fetchone()[0]

def create_missing_tables():
    """Create all missing tables that are causing migration issues"""
    
    print("=" * 70)
    print("FIXING MIGRATION STATE - CREATING MISSING TABLES")
    print("=" * 70)
    print()
    
    missing_tables = []
    
    # Check critical tables
    critical_tables = [
        'myApp_lead',
        'myApp_giftenrollment',
        'myApp_leadtimelineevent',
        'myApp_giftenrollmentleadlink',
        'myApp_enrollmentleadlink',
        'django_session',
    ]
    
    print("Checking tables...")
    for table in critical_tables:
        exists = check_table_exists(table)
        if not exists:
            missing_tables.append(table)
            print(f"  ✗ {table} - MISSING")
        else:
            print(f"  ✓ {table} - EXISTS")
    
    print()
    
    if not missing_tables:
        print("All critical tables exist!")
        return
    
    print(f"Found {len(missing_tables)} missing tables")
    print()
    
    # Create tables in order (respecting dependencies)
    creation_order = [
        'myApp_lead',
        'myApp_leadtimelineevent',
        'myApp_giftenrollment',
        'myApp_giftenrollmentleadlink',
        'myApp_enrollmentleadlink',
    ]
    
    for table in creation_order:
        if table in missing_tables:
            print(f"Creating {table}...")
            try:
                if table == 'myApp_lead':
                    create_lead_table()
                elif table == 'myApp_leadtimelineevent':
                    create_leadtimelineevent_table()
                elif table == 'myApp_giftenrollment':
                    create_giftenrollment_table()
                elif table == 'myApp_giftenrollmentleadlink':
                    create_giftenrollmentleadlink_table()
                elif table == 'myApp_enrollmentleadlink':
                    create_enrollmentleadlink_table()
                print(f"  ✓ {table} created")
            except Exception as e:
                print(f"  ✗ Error creating {table}: {e}")
                import traceback
                traceback.print_exc()
    
    print()
    print("=" * 70)
    print("DONE!")
    print("=" * 70)

def create_lead_table():
    """Create Lead table"""
    with connection.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS "myApp_lead" (
                "id" BIGSERIAL NOT NULL PRIMARY KEY,
                "name" VARCHAR(200) NOT NULL,
                "email" VARCHAR(254) NULL,
                "phone" VARCHAR(20) NOT NULL DEFAULT '',
                "source" VARCHAR(20) NOT NULL DEFAULT 'other',
                "status" VARCHAR(20) NOT NULL DEFAULT 'new',
                "notes" TEXT NOT NULL DEFAULT '',
                "last_contact_date" TIMESTAMP WITH TIME ZONE NULL,
                "infobip_profile_id" VARCHAR(100) NULL,
                "infobip_last_synced_at" TIMESTAMP WITH TIME ZONE NULL,
                "infobip_channel" VARCHAR(20) NOT NULL DEFAULT '',
                "owner_id" INTEGER NULL REFERENCES "auth_user"("id") ON DELETE SET NULL,
                "linked_user_id" INTEGER NULL REFERENCES "auth_user"("id") ON DELETE SET NULL,
                "created_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                "updated_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            );
            
            CREATE INDEX IF NOT EXISTS "myApp_lead_email_idx" ON "myApp_lead" ("email");
            CREATE INDEX IF NOT EXISTS "myApp_lead_status_idx" ON "myApp_lead" ("status");
            CREATE INDEX IF NOT EXISTS "myApp_lead_source_idx" ON "myApp_lead" ("source");
        """)

def create_leadtimelineevent_table():
    """Create LeadTimelineEvent table"""
    with connection.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS "myApp_leadtimelineevent" (
                "id" BIGSERIAL NOT NULL PRIMARY KEY,
                "event_type" VARCHAR(50) NOT NULL,
                "summary" TEXT NOT NULL,
                "metadata" JSONB NOT NULL DEFAULT '{}',
                "created_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                "lead_id" BIGINT NOT NULL REFERENCES "myApp_lead"("id") ON DELETE CASCADE,
                "actor_id" INTEGER NULL REFERENCES "auth_user"("id") ON DELETE SET NULL
            );
            
            CREATE INDEX IF NOT EXISTS "myApp_leadtimelineevent_lead_created_idx" 
                ON "myApp_leadtimelineevent" ("lead_id", "created_at" DESC);
        """)

def create_giftenrollment_table():
    """Create GiftEnrollment table"""
    with connection.cursor() as cursor:
        # Check which FK tables exist
        fk_tables = {
            'auth_user': check_table_exists('auth_user'),
            'myApp_course': check_table_exists('myApp_course'),
            'myApp_enrollment': check_table_exists('myApp_enrollment'),
            'myApp_payment': check_table_exists('myApp_payment'),
        }
        
        # Create table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS "myApp_giftenrollment" (
                "id" BIGSERIAL NOT NULL PRIMARY KEY,
                "gift_token" UUID NOT NULL UNIQUE,
                "recipient_email" VARCHAR(254) NOT NULL,
                "recipient_name" VARCHAR(255) NOT NULL DEFAULT '',
                "sender_name" VARCHAR(255) NOT NULL DEFAULT '',
                "gift_message" TEXT NOT NULL DEFAULT '',
                "status" VARCHAR(20) NOT NULL DEFAULT 'pending_claim',
                "created_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                "claimed_at" TIMESTAMP WITH TIME ZONE NULL,
                "expires_at" TIMESTAMP WITH TIME ZONE NULL,
                "buyer_id" INTEGER NOT NULL,
                "course_id" BIGINT NOT NULL,
                "enrollment_id" BIGINT NULL,
                "payment_id" BIGINT NULL
            );
        """)
        
        # Add foreign keys if tables exist
        if fk_tables['auth_user']:
            cursor.execute("""
                ALTER TABLE "myApp_giftenrollment" 
                ADD CONSTRAINT IF NOT EXISTS "myApp_giftenrollment_buyer_id_fk" 
                FOREIGN KEY ("buyer_id") REFERENCES "auth_user"("id") ON DELETE CASCADE;
            """)
        
        if fk_tables['myApp_course']:
            cursor.execute("""
                ALTER TABLE "myApp_giftenrollment" 
                ADD CONSTRAINT IF NOT EXISTS "myApp_giftenrollment_course_id_fk" 
                FOREIGN KEY ("course_id") REFERENCES "myApp_course"("id") ON DELETE CASCADE;
            """)
        
        if fk_tables['myApp_enrollment']:
            cursor.execute("""
                ALTER TABLE "myApp_giftenrollment" 
                ADD CONSTRAINT IF NOT EXISTS "myApp_giftenrollment_enrollment_id_fk" 
                FOREIGN KEY ("enrollment_id") REFERENCES "myApp_enrollment"("id") ON DELETE SET NULL;
            """)
        
        if fk_tables['myApp_payment']:
            cursor.execute("""
                ALTER TABLE "myApp_giftenrollment" 
                ADD CONSTRAINT IF NOT EXISTS "myApp_giftenrollment_payment_id_fk" 
                FOREIGN KEY ("payment_id") REFERENCES "myApp_payment"("id") ON DELETE SET NULL;
            """)
        
        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS "myApp_gifte_gift_to_4a3813_idx" 
                ON "myApp_giftenrollment" ("gift_token");
            CREATE INDEX IF NOT EXISTS "myApp_gifte_recipie_2b8085_idx" 
                ON "myApp_giftenrollment" ("recipient_email", "status");
            CREATE INDEX IF NOT EXISTS "myApp_gifte_status_bf7534_idx" 
                ON "myApp_giftenrollment" ("status", "created_at");
        """)

def create_giftenrollmentleadlink_table():
    """Create GiftEnrollmentLeadLink table"""
    with connection.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS "myApp_giftenrollmentleadlink" (
                "id" BIGSERIAL NOT NULL PRIMARY KEY,
                "created_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                "gift_enrollment_id" BIGINT NOT NULL REFERENCES "myApp_giftenrollment"("id") ON DELETE CASCADE,
                "lead_id" BIGINT NOT NULL REFERENCES "myApp_lead"("id") ON DELETE CASCADE,
                "created_by_id" INTEGER NULL REFERENCES "auth_user"("id") ON DELETE SET NULL,
                UNIQUE ("gift_enrollment_id", "lead_id")
            );
        """)

def create_enrollmentleadlink_table():
    """Create EnrollmentLeadLink table"""
    with connection.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS "myApp_enrollmentleadlink" (
                "id" BIGSERIAL NOT NULL PRIMARY KEY,
                "created_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                "enrollment_id" BIGINT NOT NULL REFERENCES "myApp_enrollment"("id") ON DELETE CASCADE,
                "lead_id" BIGINT NOT NULL REFERENCES "myApp_lead"("id") ON DELETE CASCADE,
                "created_by_id" INTEGER NULL REFERENCES "auth_user"("id") ON DELETE SET NULL,
                UNIQUE ("enrollment_id", "lead_id")
            );
        """)

if __name__ == '__main__':
    try:
        create_missing_tables()
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()

