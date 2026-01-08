"""
Activity logging utility for Fluentory.
Logs key events: gift claimed, teacher assignments, lead status changes.
"""
import logging
from django.utils import timezone
from .models import ActivityLog

logger = logging.getLogger(__name__)


def log_activity(entity_type, entity_id, event_type, summary, actor=None, metadata=None):
    """
    Create an activity log entry.
    
    Args:
        entity_type: One of 'gift', 'live_class', 'lead', 'enrollment', 'teacher'
        entity_id: ID of the related entity
        event_type: One of 'gift_claimed', 'teacher_assigned', 'teacher_unassigned', 
                    'teacher_reassigned', 'lead_status_updated'
        summary: Human-readable summary of the event
        actor: User who performed the action (None for system actions)
        metadata: Additional structured data (dict)
    
    Returns:
        ActivityLog instance or None if creation failed
    """
    try:
        activity = ActivityLog.objects.create(
            entity_type=entity_type,
            entity_id=entity_id,
            event_type=event_type,
            summary=summary,
            actor=actor,
            metadata=metadata or {}
        )
        logger.info(f"Activity logged: {event_type} for {entity_type} #{entity_id} by {actor.username if actor else 'System'}")
        return activity
    except Exception as e:
        logger.error(f"Failed to create activity log: {str(e)}", exc_info=True)
        return None


def log_gift_claimed(gift_enrollment, enrollment, actor=None):
    """Log when a gift is claimed"""
    return log_activity(
        entity_type='gift',
        entity_id=gift_enrollment.id,
        event_type='gift_claimed',
        summary=f"Gift for {gift_enrollment.course.title} claimed by {enrollment.user.get_full_name() or enrollment.user.username}",
        actor=actor,
        metadata={
            'gift_id': gift_enrollment.id,
            'enrollment_id': enrollment.id,
            'course_id': gift_enrollment.course.id,
            'recipient_email': gift_enrollment.recipient_email,
        }
    )


def log_teacher_assigned(live_class, teacher, assigned_by, reason=None):
    """Log when a teacher is assigned to a live class"""
    return log_activity(
        entity_type='live_class',
        entity_id=live_class.id,
        event_type='teacher_assigned',
        summary=f"Teacher {teacher.user.get_full_name() or teacher.user.username} assigned to live class '{live_class.title}'",
        actor=assigned_by,
        metadata={
            'live_class_id': live_class.id,
            'teacher_id': teacher.id,
            'course_id': live_class.course.id if live_class.course else None,
            'reason': reason,
        }
    )


def log_teacher_unassigned(live_class, teacher, unassigned_by, reason=None):
    """Log when a teacher is unassigned from a live class"""
    return log_activity(
        entity_type='live_class',
        entity_id=live_class.id,
        event_type='teacher_unassigned',
        summary=f"Teacher {teacher.user.get_full_name() or teacher.user.username} unassigned from live class '{live_class.title}'",
        actor=unassigned_by,
        metadata={
            'live_class_id': live_class.id,
            'teacher_id': teacher.id,
            'course_id': live_class.course.id if live_class.course else None,
            'reason': reason,
        }
    )


def log_teacher_reassigned(live_class, old_teacher, new_teacher, reassigned_by, reason=None):
    """Log when a teacher is reassigned (old → new)"""
    old_name = old_teacher.user.get_full_name() or old_teacher.user.username if old_teacher else "Unassigned"
    new_name = new_teacher.user.get_full_name() or new_teacher.user.username if new_teacher else "Unassigned"
    
    return log_activity(
        entity_type='live_class',
        entity_id=live_class.id,
        event_type='teacher_reassigned',
        summary=f"Live class '{live_class.title}' reassigned: {old_name} → {new_name}",
        actor=reassigned_by,
        metadata={
            'live_class_id': live_class.id,
            'old_teacher_id': old_teacher.id if old_teacher else None,
            'new_teacher_id': new_teacher.id if new_teacher else None,
            'course_id': live_class.course.id if live_class.course else None,
            'reason': reason,
        }
    )


def log_lead_status_updated(lead, old_status, new_status, actor=None):
    """Log when a lead status is updated"""
    return log_activity(
        entity_type='lead',
        entity_id=lead.id,
        event_type='lead_status_updated',
        summary=f"Lead '{lead.name}' status changed: {old_status} → {new_status}",
        actor=actor,
        metadata={
            'lead_id': lead.id,
            'old_status': old_status,
            'new_status': new_status,
            'lead_email': lead.email,
        }
    )

