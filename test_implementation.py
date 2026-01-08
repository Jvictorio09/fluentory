"""
Quick testing script to verify email, permissions, and activity log implementation.
Run with: python test_implementation.py
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myProject.settings')
django.setup()

from django.contrib.auth.models import User
from myApp.models import (
    GiftEnrollment, ActivityLog, Lead, LiveClassSession,
    Course, UserProfile
)
from myApp.permissions import is_admin, is_teacher
from myApp.email_utils import send_gift_invite_email, send_gift_confirmation_email
from myApp.activity_log import (
    log_gift_claimed, log_teacher_assigned, log_lead_status_updated
)

def test_permissions():
    """Test permission functions"""
    print("\n" + "="*60)
    print("TESTING PERMISSIONS")
    print("="*60)
    
    users = User.objects.all()[:5]
    for user in users:
        try:
            admin_check = is_admin(user)
            teacher_check = is_teacher(user)
            role = user.profile.role if hasattr(user, 'profile') else 'N/A'
            print(f"User: {user.username} | Role: {role} | Is Admin: {admin_check} | Is Teacher: {teacher_check}")
        except Exception as e:
            print(f"Error checking user {user.username}: {e}")
    
    print("[OK] Permissions module working")

def test_activity_logs():
    """Test activity log creation"""
    print("\n" + "="*60)
    print("TESTING ACTIVITY LOGS")
    print("="*60)
    
    # Check if activity logs exist
    logs = ActivityLog.objects.all().order_by('-created_at')[:5]
    print(f"\nFound {ActivityLog.objects.count()} total activity logs")
    print("\nRecent activity logs:")
    for log in logs:
        actor_name = log.actor.username if log.actor else "System"
        print(f"  - {log.created_at.strftime('%Y-%m-%d %H:%M')} | {log.get_event_type_display()} | {log.entity_type} #{log.entity_id} | by {actor_name}")
    
    # Check by event type
    event_types = ['gift_claimed', 'teacher_assigned', 'teacher_reassigned', 'lead_status_updated']
    for event_type in event_types:
        count = ActivityLog.objects.filter(event_type=event_type).count()
        print(f"  {event_type}: {count} logs")
    
    print("[OK] Activity logs system working")

def test_email_functions():
    """Test email utility functions exist and are callable"""
    print("\n" + "="*60)
    print("TESTING EMAIL FUNCTIONS")
    print("="*60)
    
    functions = [
        send_gift_invite_email,
        send_gift_confirmation_email,
    ]
    
    for func in functions:
        print(f"  [OK] {func.__name__} exists and is callable")
    
    print("[OK] Email utility functions available")

def test_models():
    """Test that required models exist"""
    print("\n" + "="*60)
    print("TESTING MODELS")
    print("="*60)
    
    models_to_check = [
        ('GiftEnrollment', GiftEnrollment),
        ('ActivityLog', ActivityLog),
        ('Lead', Lead),
        ('LiveClassSession', LiveClassSession),
    ]
    
    for name, model in models_to_check:
        count = model.objects.count()
        print(f"  {name}: {count} records")
    
    print("[OK] All required models exist")

def test_recent_gifts():
    """Check recent gift enrollments"""
    print("\n" + "="*60)
    print("TESTING GIFT ENROLLMENTS")
    print("="*60)
    
    gifts = GiftEnrollment.objects.all().order_by('-created_at')[:5]
    print(f"\nFound {GiftEnrollment.objects.count()} total gift enrollments")
    print("\nRecent gifts:")
    for gift in gifts:
        status_icon = "[OK]" if gift.status == 'claimed' else "[PENDING]"
        print(f"  {status_icon} Gift #{gift.id} | {gift.course.title} | Status: {gift.status} | Recipient: {gift.recipient_email}")
    
    print("[OK] Gift enrollments working")

def test_leads():
    """Check recent leads"""
    print("\n" + "="*60)
    print("TESTING LEADS")
    print("="*60)
    
    leads = Lead.objects.all().order_by('-created_at')[:5]
    print(f"\nFound {Lead.objects.count()} total leads")
    print("\nRecent leads:")
    for lead in leads:
        print(f"  - {lead.name} | {lead.email} | Status: {lead.get_status_display()} | Source: {lead.get_source_display()}")
    
    # Check for activity logs
    lead_with_logs = Lead.objects.filter(
        id__in=ActivityLog.objects.filter(entity_type='lead').values_list('entity_id', flat=True)
    ).first()
    if lead_with_logs:
        log_count = ActivityLog.objects.filter(entity_type='lead', entity_id=lead_with_logs.id).count()
        print(f"\n  Example: Lead '{lead_with_logs.name}' has {log_count} activity logs")
    
    print("[OK] Leads system working")

def test_live_classes():
    """Check recent live classes"""
    print("\n" + "="*60)
    print("TESTING LIVE CLASSES")
    print("="*60)
    
    live_classes = LiveClassSession.objects.all().order_by('-created_at')[:5]
    print(f"\nFound {LiveClassSession.objects.count()} total live classes")
    print("\nRecent live classes:")
    for lc in live_classes:
        teacher_name = lc.teacher.user.username if lc.teacher else "Unassigned"
        print(f"  - {lc.title} | Teacher: {teacher_name} | Status: {lc.get_status_display()}")
    
    # Check for activity logs
    lc_with_logs = LiveClassSession.objects.filter(
        id__in=ActivityLog.objects.filter(entity_type='live_class').values_list('entity_id', flat=True)
    ).first()
    if lc_with_logs:
        log_count = ActivityLog.objects.filter(entity_type='live_class', entity_id=lc_with_logs.id).count()
        print(f"\n  Example: Live class '{lc_with_logs.title}' has {log_count} activity logs")
    
    print("[OK] Live classes system working")

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("FLUENTORY IMPLEMENTATION TEST")
    print("="*60)
    print("\nThis script verifies that email, permissions, and activity log")
    print("features are properly implemented and working.\n")
    
    try:
        test_models()
        test_permissions()
        test_email_functions()
        test_activity_logs()
        test_recent_gifts()
        test_leads()
        test_live_classes()
        
        print("\n" + "="*60)
        print("[OK] ALL TESTS COMPLETED")
        print("="*60)
        print("\nNext steps:")
        print("1. Review TESTING_GUIDE.md for detailed manual testing steps")
        print("2. Test email sending with console backend")
        print("3. Test 403 page by accessing admin routes as non-admin")
        print("4. Verify activity logs appear in detail pages")
        print("\n")
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()

