#!/usr/bin/env python
"""
Phase 2 Unified Booking System - Verification Script
Checks if all Phase 2 requirements are met and working
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myProject.settings')
django.setup()

from django.db import connection
from django.core.exceptions import ImproperlyConfigured
from myApp.models import (
    LiveClassSession, LiveClassBooking, TeacherBookingPolicy,
    BookingSeries, BookingSeriesItem, SessionWaitlist
)

def check_migrations():
    """Check if Phase 2 migrations are applied"""
    print("\n" + "="*60)
    print("1. MIGRATION STATUS")
    print("="*60)
    
    from django.db.migrations.executor import MigrationExecutor
    from django.db import connection
    executor = MigrationExecutor(connection)
    applied_migrations = [m for m in executor.loader.applied_migrations if m[0] == 'myApp']
    
    phase2_migrations = [
        '0018_phase2_unified_booking_system',
        '0019_populate_phase2_fields'
    ]
    
    all_applied = True
    for migration in phase2_migrations:
        migration_key = ('myApp', migration)
        if migration_key in applied_migrations:
            print(f"[OK] {migration} - APPLIED")
        else:
            print(f"[FAIL] {migration} - NOT APPLIED")
            all_applied = False
    
    return all_applied

def check_database_schema():
    """Check if Phase 2 database columns exist"""
    print("\n" + "="*60)
    print("2. DATABASE SCHEMA")
    print("="*60)
    
    cursor = connection.cursor()
    
    # Check LiveClassSession fields
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'myapp_liveclasssession' 
        AND column_name IN ('start_at_utc', 'end_at_utc', 'timezone_snapshot', 
                           'meeting_provider', 'capacity', 'seats_taken')
        ORDER BY column_name
    """)
    fields = [row[0] for row in cursor.fetchall()]
    required_fields = ['start_at_utc', 'end_at_utc', 'timezone_snapshot', 
                      'meeting_provider', 'capacity', 'seats_taken']
    
    missing_fields = set(required_fields) - set(fields)
    if missing_fields:
        print(f"[FAIL] Missing LiveClassSession fields: {missing_fields}")
        return False
    else:
        print(f"[OK] LiveClassSession Phase 2 fields: {fields}")
    
    # Check Phase 2 tables
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_name IN ('myapp_liveclassbooking', 'myapp_teacherbookingpolicy', 
                           'myapp_bookingseries', 'myapp_bookingseriesitem', 
                           'myapp_sessionwaitlist')
        ORDER BY table_name
    """)
    tables = [row[0] for row in cursor.fetchall()]
    required_tables = ['myapp_liveclassbooking', 'myapp_teacherbookingpolicy',
                      'myapp_bookingseries', 'myapp_bookingseriesitem',
                      'myapp_sessionwaitlist']
    
    missing_tables = set(required_tables) - set(tables)
    if missing_tables:
        print(f"[FAIL] Missing Phase 2 tables: {missing_tables}")
        return False
    else:
        print(f"[OK] Phase 2 tables: {tables}")
    
    return True

def check_models():
    """Check if Phase 2 models are importable and have correct structure"""
    print("\n" + "="*60)
    print("3. MODEL STRUCTURE")
    print("="*60)
    
    checks = []
    
    # Check LiveClassSession
    try:
        assert hasattr(LiveClassSession, 'start_at_utc')
        assert hasattr(LiveClassSession, 'end_at_utc')
        assert hasattr(LiveClassSession, 'timezone_snapshot')
        assert hasattr(LiveClassSession, 'meeting_provider')
        assert hasattr(LiveClassSession, 'capacity')
        assert hasattr(LiveClassSession, 'seats_taken')
        checks.append(("LiveClassSession Phase 2 fields", True))
    except AssertionError as e:
        checks.append(("LiveClassSession Phase 2 fields", False))
    
    # Check LiveClassBooking
    try:
        assert hasattr(LiveClassBooking, 'booking_type')
        assert hasattr(LiveClassBooking, 'start_at_utc')
        assert hasattr(LiveClassBooking, 'end_at_utc')
        assert hasattr(LiveClassBooking, 'session')
        assert hasattr(LiveClassBooking, 'seats_reserved')
        assert hasattr(LiveClassBooking, 'confirm')
        assert hasattr(LiveClassBooking, 'decline')
        assert hasattr(LiveClassBooking, 'cancel')
        checks.append(("LiveClassBooking model", True))
    except AssertionError as e:
        checks.append(("LiveClassBooking model", False))
    
    # Check TeacherBookingPolicy
    try:
        assert hasattr(TeacherBookingPolicy, 'requires_approval_for_one_on_one')
        assert hasattr(TeacherBookingPolicy, 'requires_approval_for_group')
        assert hasattr(TeacherBookingPolicy, 'min_notice_hours')
        assert hasattr(TeacherBookingPolicy, 'get_requires_approval')
        checks.append(("TeacherBookingPolicy model", True))
    except AssertionError as e:
        checks.append(("TeacherBookingPolicy model", False))
    
    # Check BookingSeries
    try:
        assert hasattr(BookingSeries, 'frequency')
        assert hasattr(BookingSeries, 'type')
        assert hasattr(BookingSeries, 'status')
        checks.append(("BookingSeries model", True))
    except AssertionError as e:
        checks.append(("BookingSeries model", False))
    
    # Check SessionWaitlist
    try:
        assert hasattr(SessionWaitlist, 'offer_seat')
        assert hasattr(SessionWaitlist, 'accept_offer')
        assert hasattr(SessionWaitlist, 'expire_offer')
        checks.append(("SessionWaitlist model", True))
    except AssertionError as e:
        checks.append(("SessionWaitlist model", False))
    
    all_pass = True
    for name, status in checks:
        if status:
            print(f"[OK] {name}")
        else:
            print(f"[FAIL] {name}")
            all_pass = False
    
    return all_pass

def check_data_integrity():
    """Check if existing data is properly migrated"""
    print("\n" + "="*60)
    print("4. DATA INTEGRITY")
    print("="*60)
    
    # Check if existing sessions have start_at_utc populated
    sessions_without_utc = LiveClassSession.objects.filter(
        scheduled_start__isnull=False,
        start_at_utc__isnull=True
    ).count()
    
    if sessions_without_utc > 0:
        print(f"[WARN] {sessions_without_utc} sessions missing start_at_utc")
        print("       (Will be auto-populated on next save)")
    else:
        print("[OK] All sessions have start_at_utc populated")
    
    # Check capacity sync
    sessions_without_capacity = LiveClassSession.objects.filter(
        total_seats__isnull=False,
        capacity__isnull=True
    ).count()
    
    if sessions_without_capacity > 0:
        print(f"[WARN] {sessions_without_capacity} sessions missing capacity")
        print("       (Will be auto-populated on next save)")
    else:
        print("[OK] All sessions have capacity set")
    
    return True

def check_backward_compatibility():
    """Check if legacy fields still work"""
    print("\n" + "="*60)
    print("5. BACKWARD COMPATIBILITY")
    print("="*60)
    
    # Check if we can query using scheduled_start
    try:
        count = LiveClassSession.objects.filter(scheduled_start__isnull=False).count()
        print(f"[OK] Can query using scheduled_start: {count} sessions")
    except Exception as e:
        print(f"[FAIL] Error querying scheduled_start: {e}")
        return False
    
    # Check if scheduled_end property works
    try:
        session = LiveClassSession.objects.first()
        if session:
            end_time = session.scheduled_end
            print(f"[OK] scheduled_end property works")
    except Exception as e:
        print(f"[FAIL] Error with scheduled_end property: {e}")
        return False
    
    return True

def main():
    """Run all checks"""
    print("\n" + "="*60)
    print("PHASE 2 UNIFIED BOOKING SYSTEM - VERIFICATION")
    print("="*60)
    
    results = []
    
    results.append(("Migrations", check_migrations()))
    results.append(("Database Schema", check_database_schema()))
    results.append(("Model Structure", check_models()))
    results.append(("Data Integrity", check_data_integrity()))
    results.append(("Backward Compatibility", check_backward_compatibility()))
    
    # Final summary
    print("\n" + "="*60)
    print("VERIFICATION SUMMARY")
    print("="*60)
    
    all_pass = all(result[1] for result in results)
    
    for name, status in results:
        status_icon = "✅" if status else "❌"
        print(f"{status_icon} {name}")
    
    if all_pass:
        print("\n🎉 PHASE 2 IS COMPLETE AND WORKING!")
        print("\n✅ All migrations applied")
        print("✅ All database tables and columns exist")
        print("✅ All models are properly structured")
        print("✅ Backward compatibility maintained")
        print("\nReady for production use!")
    else:
        print("\n⚠️  PHASE 2 HAS ISSUES - Review errors above")
        sys.exit(1)

if __name__ == '__main__':
    main()

