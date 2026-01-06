# Generated manually to populate Phase 2 fields from existing data

from django.db import migrations
from django.utils import timezone
from datetime import timedelta


def populate_phase2_fields(apps, schema_editor):
    """Populate start_at_utc, end_at_utc, capacity, and timezone_snapshot from existing data"""
    LiveClassSession = apps.get_model('myApp', 'LiveClassSession')
    
    for session in LiveClassSession.objects.all():
        # Populate start_at_utc from scheduled_start
        if not session.start_at_utc and session.scheduled_start:
            session.start_at_utc = session.scheduled_start
            session.save(update_fields=['start_at_utc'])
        
        # Populate end_at_utc from start_at_utc + duration
        if session.start_at_utc and not session.end_at_utc:
            duration_minutes = session.duration_minutes or 60
            session.end_at_utc = session.start_at_utc + timedelta(minutes=duration_minutes)
            session.save(update_fields=['end_at_utc'])
        
        # Populate capacity from total_seats
        if session.capacity is None and session.total_seats:
            session.capacity = session.total_seats
            session.save(update_fields=['capacity'])
        
        # Populate timezone_snapshot (default to UTC if not set)
        if not session.timezone_snapshot:
            session.timezone_snapshot = 'UTC'
            session.save(update_fields=['timezone_snapshot'])
        
        # Populate seats_taken from confirmed bookings count
        if session.seats_taken == 0:
            # Count confirmed bookings (use legacy Booking model for now)
            Booking = apps.get_model('myApp', 'Booking')
            confirmed_count = Booking.objects.filter(
                session=session,
                status__in=['confirmed', 'attended']
            ).count()
            if confirmed_count > 0:
                session.seats_taken = confirmed_count
                session.save(update_fields=['seats_taken'])


def reverse_populate_phase2_fields(apps, schema_editor):
    """Reverse migration - no action needed"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('myApp', '0018_phase2_unified_booking_system'),
    ]

    operations = [
        migrations.RunPython(populate_phase2_fields, reverse_populate_phase2_fields),
    ]




