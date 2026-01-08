"""
Diagnostic script to check GiftEnrollment records and email configuration
Run: python check_gift_enrollments.py
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myProject.settings')
django.setup()

from myApp.models import GiftEnrollment, Payment
from django.conf import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print("=" * 60)
print("GIFT ENROLLMENT DIAGNOSTIC")
print("=" * 60)

# 1. Check if GiftEnrollment records exist
print("\n1. CHECKING GIFT ENROLLMENT RECORDS")
print("-" * 60)
total_gifts = GiftEnrollment.objects.count()
print(f"Total GiftEnrollment records: {total_gifts}")

if total_gifts > 0:
    print("\nRecent gifts:")
    recent_gifts = GiftEnrollment.objects.select_related('buyer', 'course').order_by('-created_at')[:5]
    for gift in recent_gifts:
        print(f"  - ID: {gift.id}")
        print(f"    Buyer: {gift.buyer.email}")
        print(f"    Recipient: {gift.recipient_email}")
        print(f"    Course: {gift.course.title}")
        print(f"    Status: {gift.status}")
        print(f"    Created: {gift.created_at}")
        print(f"    Claimed: {gift.claimed_at if gift.claimed_at else 'Not claimed'}")
        print()
    
    # Check status breakdown
    pending = GiftEnrollment.objects.filter(status='pending_claim').count()
    claimed = GiftEnrollment.objects.filter(status='claimed').count()
    print(f"Status breakdown: {pending} pending, {claimed} claimed")
else:
    print("❌ NO GIFT ENROLLMENT RECORDS FOUND")
    print("   This means either:")
    print("   - No gifts have been purchased yet")
    print("   - Gifts are being saved to a different database")
    print("   - Migration hasn't been run")

# 2. Check email configuration
print("\n2. CHECKING EMAIL CONFIGURATION")
print("-" * 60)
email_backend = getattr(settings, 'EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
print(f"EMAIL_BACKEND: {email_backend}")

if email_backend == 'django.core.mail.backends.console.EmailBackend':
    print("⚠️  Using console backend - emails will only appear in console/logs")
elif email_backend == 'django.core.mail.backends.smtp.EmailBackend':
    print("[OK] Using SMTP backend")
    email_host = getattr(settings, 'EMAIL_HOST', 'NOT SET')
    email_port = getattr(settings, 'EMAIL_PORT', 'NOT SET')
    email_user = getattr(settings, 'EMAIL_HOST_USER', 'NOT SET')
    email_use_tls = getattr(settings, 'EMAIL_USE_TLS', False)
    print(f"  EMAIL_HOST: {email_host}")
    print(f"  EMAIL_PORT: {email_port}")
    print(f"  EMAIL_HOST_USER: {email_user}")
    print(f"  EMAIL_USE_TLS: {email_use_tls}")
else:
    print(f"Using custom backend: {email_backend}")

from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or getattr(settings, 'SERVER_EMAIL', 'NOT SET')
print(f"DEFAULT_FROM_EMAIL: {from_email}")

# 3. Check related Payment records
print("\n3. CHECKING RELATED PAYMENT RECORDS")
print("-" * 60)
if total_gifts > 0:
    gifts_with_payments = GiftEnrollment.objects.exclude(payment__isnull=True).count()
    print(f"Gifts with payment records: {gifts_with_payments} / {total_gifts}")
    
    # Check for gifts without payments
    gifts_without_payments = GiftEnrollment.objects.filter(payment__isnull=True).count()
    if gifts_without_payments > 0:
        print(f"⚠️  {gifts_without_payments} gifts without payment records")

# 4. Check database connection
print("\n4. DATABASE INFORMATION")
print("-" * 60)
from django.db import connection
db_name = connection.settings_dict.get('NAME', 'Unknown')
db_engine = connection.settings_dict.get('ENGINE', 'Unknown')
print(f"Database: {db_name}")
print(f"Engine: {db_engine}")

print("\n" + "=" * 60)
print("DIAGNOSTIC COMPLETE")
print("=" * 60)

