"""
Test email configuration and send a test email
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myProject.settings')
django.setup()

from django.conf import settings
from django.core.mail import send_mail

def test_email_config():
    """Test email configuration"""
    
    print("=" * 70)
    print("TESTING EMAIL CONFIGURATION")
    print("=" * 70)
    print()
    
    # Check configuration
    print("Email Configuration:")
    print(f"  EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
    print(f"  EMAIL_HOST: {settings.EMAIL_HOST}")
    print(f"  EMAIL_PORT: {settings.EMAIL_PORT}")
    print(f"  EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
    print(f"  EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
    print(f"  EMAIL_HOST_PASSWORD: {'SET' if settings.EMAIL_HOST_PASSWORD else 'NOT SET'}")
    print(f"  DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
    print()
    
    # Check environment variables
    print("Environment Variables:")
    resend_key = os.getenv('RESEND_API_KEY', '').strip()
    resend_from = os.getenv('RESEND_FROM', '').strip()
    print(f"  RESEND_API_KEY: {'SET' if resend_key else 'NOT SET'}")
    print(f"  RESEND_FROM: {resend_from or 'NOT SET'}")
    print(f"  DEFAULT_FROM_EMAIL: {os.getenv('DEFAULT_FROM_EMAIL', 'NOT SET')}")
    print()
    
    # Test sending email
    test_email = input("Enter your email address to send a test email (or press Enter to skip): ").strip()
    
    if test_email:
        print(f"\nSending test email to {test_email}...")
        try:
            result = send_mail(
                subject='Test Email from Fluentory',
                message='This is a test email to verify email configuration.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[test_email],
                fail_silently=False,
            )
            if result == 1:
                print(f"✓ Test email sent successfully!")
                print(f"  Check your inbox at {test_email}")
            else:
                print(f"✗ Email send returned {result} (expected 1)")
        except Exception as e:
            print(f"✗ Error sending email: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("Skipping test email send.")
    
    print()
    print("=" * 70)

if __name__ == '__main__':
    test_email_config()

