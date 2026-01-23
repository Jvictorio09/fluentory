"""
Apply the whatsapp_number migration safely
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myProject.settings')
django.setup()

from django.db import connection
from django.core.management import call_command

def apply_migration():
    """Apply the migration for whatsapp_number"""
    print("=" * 70)
    print("Applying WhatsApp Number Migration")
    print("=" * 70)
    
    try:
        # Check if column already exists
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = 'myApp_sitesettings'
                AND column_name = 'whatsapp_number';
            """)
            exists = cursor.fetchone() is not None
            
            if exists:
                print("\n✓ whatsapp_number column already exists")
            else:
                print("\n⚠ whatsapp_number column does not exist - applying migration...")
                # Try to apply migration
                try:
                    call_command('migrate', 'myApp', verbosity=2)
                    print("\n✓ Migration applied successfully")
                except Exception as e:
                    print(f"\n⚠ Migration failed: {e}")
                    print("\nTrying to add column manually...")
                    try:
                        cursor.execute("""
                            ALTER TABLE "myApp_sitesettings" 
                            ADD COLUMN whatsapp_number VARCHAR(20) DEFAULT '' NOT NULL;
                        """)
                        print("✓ Column added manually")
                    except Exception as e2:
                        print(f"✗ Failed to add column: {e2}")
                        return False
        
        # Verify column exists
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = 'myApp_sitesettings'
                AND column_name = 'whatsapp_number';
            """)
            exists = cursor.fetchone() is not None
            if exists:
                print("\n✓ Verification: whatsapp_number column exists")
                return True
            else:
                print("\n✗ Verification failed: column still missing")
                return False
                
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False

if __name__ == '__main__':
    apply_migration()

