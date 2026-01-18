"""
Check email setup and test sending
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myProject.settings')
django.setup()

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

def check_email_setup():
    """Check email configuration"""
    
    print("=" * 70)
    print("EMAIL CONFIGURATION CHECK")
    print("=" * 70)
    print()
    
    # Check environment variables
    resend_key = os.getenv('RESEND_API_KEY', '').strip()
    resend_from = os.getenv('RESEND_FROM', '').strip().strip('"').strip("'")
    default_from = os.getenv('DEFAULT_FROM_EMAIL', '').strip()
    
    print("Environment Variables:")
    print(f"  RESEND_API_KEY: {'SET (' + resend_key[:10] + '...)' if resend_key else 'NOT SET'}")
    print(f"  RESEND_FROM: {resend_from or 'NOT SET'}")
    print(f"  DEFAULT_FROM_EMAIL: {default_from or 'NOT SET'}")
    print()
    
    # Check Django settings
    print("Django Settings:")
    print(f"  EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
    print(f"  EMAIL_HOST: {settings.EMAIL_HOST}")
    print(f"  EMAIL_PORT: {settings.EMAIL_PORT}")
    print(f"  EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
    print(f"  EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
    print(f"  EMAIL_HOST_PASSWORD: {'SET' if settings.EMAIL_HOST_PASSWORD else 'NOT SET'}")
    print(f"  DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
    print()
    
    # Check if Resend is configured
    if settings.EMAIL_HOST == 'smtp.resend.com':
        print("✓ Resend is configured!")
    else:
        print("⚠ Resend is NOT configured - using fallback SMTP")
        if not resend_key:
            print("  → Add RESEND_API_KEY to your .env file")
    print()
    
    # Check email template
    template_path = 'emails/teacher_account_created.html'
    try:
        # Try to render template (dry run)
        test_context = {
            'teacher_name': 'Test Teacher',
            'username': 'test_user',
            'email': 'test@example.com',
            'reset_url': 'https://example.com/reset',
            'profile_url': 'https://example.com/profile',
            'login_url': 'https://example.com/login',
            'is_approved': True,
            'permission_level': 'standard',
            'current_year': 2026,
            'support_url': '/help/',
        }
        render_to_string(template_path, test_context)
        print(f"✓ Email template exists: {template_path}")
    except Exception as e:
        print(f"✗ Email template error: {e}")
    
    print()
    print("=" * 70)
    print("To test sending an email, run:")
    print("  python test_email_config.py")
    print("=" * 70)

if __name__ == '__main__':
    check_email_setup()

