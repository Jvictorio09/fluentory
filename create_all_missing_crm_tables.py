"""
Create all missing CRM-related tables (Lead, GiftEnrollment, etc.)
This fixes the broken migration state
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myProject.settings')
django.setup()

from django.db import connection

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

def create_all_tables():
    """Create all missing CRM tables"""
    
    print("=" * 70)
    print("CREATING ALL MISSING CRM TABLES")
    print("=" * 70)
    print()
    
    tables_to_create = [
        ('myApp_lead', create_lead_table),
        ('myApp_leadtimelineevent', create_leadtimelineevent_table),
        ('myApp_giftenrollment', create_giftenrollment_table),
        ('myApp_giftenrollmentleadlink', create_giftenrollmentleadlink_table),
        ('myApp_enrollmentleadlink', create_enrollmentleadlink_table),
    ]
    
    for table_name, create_func in tables_to_create:
        if not check_table_exists(table_name):
            print(f"Creating {table_name}...")
            try:
                create_func()
                print(f"  ✓ {table_name} created")
            except Exception as e:
                print(f"  ✗ Error: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"  ✓ {table_name} already exists")
    
    print()
    print("=" * 70)
    print("DONE!")
    print("=" * 70)

def create_lead_table():
    """Create Lead table with all fields including Infobip fields"""
    with connection.cursor() as cursor:
        # Check if auth_user exists
        auth_user_exists = check_table_exists('auth_user')
        
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
                "created_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                "updated_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                "owner_id" INTEGER NULL,
                "linked_user_id" INTEGER NULL
            );
        """)
        
        # Add foreign keys if auth_user exists
        if auth_user_exists:
            try:
                cursor.execute("""
                    ALTER TABLE "myApp_lead" 
                    ADD CONSTRAINT IF NOT EXISTS "myApp_lead_owner_id_fk" 
                    FOREIGN KEY ("owner_id") REFERENCES "auth_user"("id") ON DELETE SET NULL;
                """)
                cursor.execute("""
                    ALTER TABLE "myApp_lead" 
                    ADD CONSTRAINT IF NOT EXISTS "myApp_lead_linked_user_id_fk" 
                    FOREIGN KEY ("linked_user_id") REFERENCES "auth_user"("id") ON DELETE SET NULL;
                """)
            except Exception:
                pass  # Constraints might already exist
        
        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS "myApp_lead_email_e18cd5_idx" ON "myApp_lead" ("email");
            CREATE INDEX IF NOT EXISTS "myApp_lead_status_a865aa_idx" ON "myApp_lead" ("status");
            CREATE INDEX IF NOT EXISTS "myApp_lead_source_7ebbd2_idx" ON "myApp_lead" ("source");
        """)

def create_leadtimelineevent_table():
    """Create LeadTimelineEvent table"""
    with connection.cursor() as cursor:
        # Check dependencies
        lead_exists = check_table_exists('myApp_lead')
        auth_user_exists = check_table_exists('auth_user')
        
        if not lead_exists:
            raise Exception("myApp_lead table must exist first")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS "myApp_leadtimelineevent" (
                "id" BIGSERIAL NOT NULL PRIMARY KEY,
                "event_type" VARCHAR(50) NOT NULL,
                "summary" TEXT NOT NULL,
                "metadata" JSONB NOT NULL DEFAULT '{}',
                "created_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                "lead_id" BIGINT NOT NULL,
                "actor_id" INTEGER NULL
            );
        """)
        
        # Add foreign keys
        cursor.execute("""
            ALTER TABLE "myApp_leadtimelineevent" 
            ADD CONSTRAINT IF NOT EXISTS "myApp_leadtimelineevent_lead_id_fk" 
            FOREIGN KEY ("lead_id") REFERENCES "myApp_lead"("id") ON DELETE CASCADE;
        """)
        
        if auth_user_exists:
            try:
                cursor.execute("""
                    ALTER TABLE "myApp_leadtimelineevent" 
                    ADD CONSTRAINT IF NOT EXISTS "myApp_leadtimelineevent_actor_id_fk" 
                    FOREIGN KEY ("actor_id") REFERENCES "auth_user"("id") ON DELETE SET NULL;
                """)
            except Exception:
                pass
        
        # Create index
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS "myApp_leadt_lead_id_b8f59a_idx" 
            ON "myApp_leadtimelineevent" ("lead_id", "created_at" DESC);
        """)

def create_giftenrollment_table():
    """Create GiftEnrollment table"""
    with connection.cursor() as cursor:
        # Check dependencies
        fk_tables = {
            'auth_user': check_table_exists('auth_user'),
            'myApp_course': check_table_exists('myApp_course'),
            'myApp_enrollment': check_table_exists('myApp_enrollment'),
            'myApp_payment': check_table_exists('myApp_payment'),
        }
        
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
        # Check dependencies
        if not check_table_exists('myApp_giftenrollment'):
            raise Exception("myApp_giftenrollment table must exist first")
        if not check_table_exists('myApp_lead'):
            raise Exception("myApp_lead table must exist first")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS "myApp_giftenrollmentleadlink" (
                "id" BIGSERIAL NOT NULL PRIMARY KEY,
                "created_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                "gift_enrollment_id" BIGINT NOT NULL,
                "lead_id" BIGINT NOT NULL,
                "created_by_id" INTEGER NULL
            );
        """)
        
        # Add foreign keys
        cursor.execute("""
            ALTER TABLE "myApp_giftenrollmentleadlink" 
            ADD CONSTRAINT IF NOT EXISTS "myApp_giftenrollmentleadlink_gift_enrollment_id_fk" 
            FOREIGN KEY ("gift_enrollment_id") REFERENCES "myApp_giftenrollment"("id") ON DELETE CASCADE;
        """)
        
        cursor.execute("""
            ALTER TABLE "myApp_giftenrollmentleadlink" 
            ADD CONSTRAINT IF NOT EXISTS "myApp_giftenrollmentleadlink_lead_id_fk" 
            FOREIGN KEY ("lead_id") REFERENCES "myApp_lead"("id") ON DELETE CASCADE;
        """)
        
        if check_table_exists('auth_user'):
            cursor.execute("""
                ALTER TABLE "myApp_giftenrollmentleadlink" 
                ADD CONSTRAINT IF NOT EXISTS "myApp_giftenrollmentleadlink_created_by_id_fk" 
                FOREIGN KEY ("created_by_id") REFERENCES "auth_user"("id") ON DELETE SET NULL;
            """)
        
        # Add unique constraint
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS "myApp_giftenrollmentleadlink_unique" 
            ON "myApp_giftenrollmentleadlink" ("gift_enrollment_id", "lead_id");
        """)

def create_enrollmentleadlink_table():
    """Create EnrollmentLeadLink table"""
    with connection.cursor() as cursor:
        # Check dependencies
        if not check_table_exists('myApp_enrollment'):
            raise Exception("myApp_enrollment table must exist first")
        if not check_table_exists('myApp_lead'):
            raise Exception("myApp_lead table must exist first")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS "myApp_enrollmentleadlink" (
                "id" BIGSERIAL NOT NULL PRIMARY KEY,
                "created_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                "enrollment_id" BIGINT NOT NULL,
                "lead_id" BIGINT NOT NULL,
                "created_by_id" INTEGER NULL
            );
        """)
        
        # Add foreign keys
        cursor.execute("""
            ALTER TABLE "myApp_enrollmentleadlink" 
            ADD CONSTRAINT IF NOT EXISTS "myApp_enrollmentleadlink_enrollment_id_fk" 
            FOREIGN KEY ("enrollment_id") REFERENCES "myApp_enrollment"("id") ON DELETE CASCADE;
        """)
        
        cursor.execute("""
            ALTER TABLE "myApp_enrollmentleadlink" 
            ADD CONSTRAINT IF NOT EXISTS "myApp_enrollmentleadlink_lead_id_fk" 
            FOREIGN KEY ("lead_id") REFERENCES "myApp_lead"("id") ON DELETE CASCADE;
        """)
        
        if check_table_exists('auth_user'):
            cursor.execute("""
                ALTER TABLE "myApp_enrollmentleadlink" 
                ADD CONSTRAINT IF NOT EXISTS "myApp_enrollmentleadlink_created_by_id_fk" 
                FOREIGN KEY ("created_by_id") REFERENCES "auth_user"("id") ON DELETE SET NULL;
            """)
        
        # Add unique constraint
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS "myApp_enrollmentleadlink_unique" 
            ON "myApp_enrollmentleadlink" ("enrollment_id", "lead_id");
        """)

if __name__ == '__main__':
    try:
        create_all_tables()
        print()
        print("Now try running: python manage.py migrate --fake")
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()

