"""
Directly create the GiftEnrollment table using SQL
This bypasses migrations if they're not working
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myProject.settings')
django.setup()

from django.db import connection

def create_giftenrollment_table():
    """Create GiftEnrollment table directly"""
    
    print("=" * 70)
    print("CREATING GiftEnrollment TABLE DIRECTLY")
    print("=" * 70)
    print()
    
    with connection.cursor() as cursor:
        # Check if table already exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND LOWER(table_name) = LOWER('myApp_giftenrollment')
            );
        """)
        exists = cursor.fetchone()[0]
        
        if exists:
            print("✓ Table 'myApp_giftenrollment' already exists")
            return
        
        print("Creating table...")
        
        # Create the table
        create_sql = """
        CREATE TABLE "myApp_giftenrollment" (
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
            "buyer_id" INTEGER NOT NULL REFERENCES "auth_user"("id") ON DELETE CASCADE,
            "course_id" BIGINT NOT NULL REFERENCES "myApp_course"("id") ON DELETE CASCADE,
            "enrollment_id" BIGINT NULL REFERENCES "myApp_enrollment"("id") ON DELETE SET NULL,
            "payment_id" BIGINT NULL REFERENCES "myApp_payment"("id") ON DELETE SET NULL
        );
        
        CREATE INDEX "myApp_gifte_gift_to_4a3813_idx" ON "myApp_giftenrollment" ("gift_token");
        CREATE INDEX "myApp_gifte_recipie_2b8085_idx" ON "myApp_giftenrollment" ("recipient_email", "status");
        CREATE INDEX "myApp_gifte_status_bf7534_idx" ON "myApp_giftenrollment" ("status", "created_at");
        """
        
        try:
            cursor.execute(create_sql)
            print("✓ Table 'myApp_giftenrollment' created successfully")
            print("✓ Indexes created")
        except Exception as e:
            print(f"✗ Error creating table: {e}")
            # Try to create without foreign keys first
            print("\nTrying to create without foreign key constraints...")
            try:
                # Check which tables exist
                cursor.execute("""
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name IN ('auth_user', 'myApp_course', 'myApp_enrollment', 'myApp_payment')
                    ORDER BY table_name;
                """)
                existing_tables = [row[0] for row in cursor.fetchall()]
                print(f"  Existing tables: {existing_tables}")
                
                # Create table with only existing foreign keys
                create_sql_simple = """
                CREATE TABLE "myApp_giftenrollment" (
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
                """
                cursor.execute(create_sql_simple)
                print("✓ Table created (without foreign key constraints)")
                
                # Add foreign keys if tables exist
                if 'auth_user' in existing_tables:
                    cursor.execute('ALTER TABLE "myApp_giftenrollment" ADD CONSTRAINT "myApp_giftenrollment_buyer_id_fk" FOREIGN KEY ("buyer_id") REFERENCES "auth_user"("id") ON DELETE CASCADE;')
                    print("✓ Added foreign key to auth_user")
                
                if 'myApp_course' in existing_tables:
                    cursor.execute('ALTER TABLE "myApp_giftenrollment" ADD CONSTRAINT "myApp_giftenrollment_course_id_fk" FOREIGN KEY ("course_id") REFERENCES "myApp_course"("id") ON DELETE CASCADE;')
                    print("✓ Added foreign key to myApp_course")
                
                if 'myApp_enrollment' in existing_tables:
                    cursor.execute('ALTER TABLE "myApp_giftenrollment" ADD CONSTRAINT "myApp_giftenrollment_enrollment_id_fk" FOREIGN KEY ("enrollment_id") REFERENCES "myApp_enrollment"("id") ON DELETE SET NULL;')
                    print("✓ Added foreign key to myApp_enrollment")
                
                if 'myApp_payment' in existing_tables:
                    cursor.execute('ALTER TABLE "myApp_giftenrollment" ADD CONSTRAINT "myApp_giftenrollment_payment_id_fk" FOREIGN KEY ("payment_id") REFERENCES "myApp_payment"("id") ON DELETE SET NULL;')
                    print("✓ Added foreign key to myApp_payment")
                
                # Create indexes
                cursor.execute('CREATE INDEX "myApp_gifte_gift_to_4a3813_idx" ON "myApp_giftenrollment" ("gift_token");')
                cursor.execute('CREATE INDEX "myApp_gifte_recipie_2b8085_idx" ON "myApp_giftenrollment" ("recipient_email", "status");')
                cursor.execute('CREATE INDEX "myApp_gifte_status_bf7534_idx" ON "myApp_giftenrollment" ("status", "created_at");')
                print("✓ Indexes created")
                
            except Exception as e2:
                print(f"✗ Error: {e2}")
                import traceback
                traceback.print_exc()
    
    print()
    print("=" * 70)
    print("DONE!")
    print("=" * 70)

if __name__ == '__main__':
    create_giftenrollment_table()

