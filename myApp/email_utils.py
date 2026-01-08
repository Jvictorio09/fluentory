"""
Email utility module for Fluentory with comprehensive logging and error handling.
"""
import logging
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse
from django.utils import timezone

logger = logging.getLogger(__name__)


def get_support_url():
    """Get support URL from settings or default"""
    return getattr(settings, 'SUPPORT_URL', '/help/')


def get_site_url(request=None):
    """Get site URL for building absolute URLs"""
    if request:
        return request.build_absolute_uri('/')
    try:
        from django.contrib.sites.models import Site
        site = Site.objects.get_current()
        protocol = 'https' if not settings.DEBUG else 'http'
        return f"{protocol}://{site.domain}"
    except:
        domain = getattr(settings, 'ALLOWED_HOSTS', ['localhost'])[0] if hasattr(settings, 'ALLOWED_HOSTS') and settings.ALLOWED_HOSTS else 'localhost:8000'
        protocol = 'https' if not settings.DEBUG else 'http'
        return f"{protocol}://{domain}"


def send_email_with_logging(subject, recipient_list, html_template, text_template, context, from_email=None, fail_silently=False):
    """
    Send email with comprehensive logging.
    
    Args:
        subject: Email subject
        recipient_list: List of recipient email addresses
        html_template: Path to HTML template
        text_template: Path to plain text template (optional)
        context: Template context dictionary
        from_email: Sender email (defaults to DEFAULT_FROM_EMAIL)
        fail_silently: If True, don't raise exceptions on failure
    
    Returns:
        Number of emails sent (0 or 1)
    """
    if not recipient_list:
        logger.error("Email send attempted with empty recipient_list")
        return 0
    
    from_email = from_email or getattr(settings, 'DEFAULT_FROM_EMAIL', None) or getattr(settings, 'SERVER_EMAIL', 'noreply@fluentory.com')
    
    # Add common context variables
    context['current_year'] = timezone.now().year
    context['support_url'] = get_support_url()
    
    # Render templates
    try:
        html_message = render_to_string(html_template, context)
        message = render_to_string(text_template, context) if text_template else None
    except Exception as e:
        logger.error(f"Email template rendering failed: {str(e)}", exc_info=True)
        if not fail_silently:
            raise
        return 0
    
    # Log email configuration
    email_backend = getattr(settings, 'EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
    logger.info(f"Email send attempt: subject='{subject}', recipient={recipient_list}, from={from_email}, backend={email_backend}")
    
    if email_backend == 'django.core.mail.backends.console.EmailBackend':
        logger.warning("Using console email backend - emails will only appear in console/logs")
    
    # Send email
    try:
        result = send_mail(
            subject=subject,
            message=message or html_message,
            from_email=from_email,
            recipient_list=recipient_list,
            html_message=html_message,
            fail_silently=fail_silently,
        )
        
        if result == 1:
            logger.info(f"Email sent successfully: subject='{subject}', recipient={recipient_list[0]}")
        else:
            logger.error(f"Email send returned {result} (expected 1) - email may not have been sent: subject='{subject}', recipient={recipient_list[0]}")
        
        return result
    except Exception as e:
        logger.error(f"Email send exception: {str(e)}", exc_info=True)
        if not fail_silently:
            raise
        return 0


def send_gift_invite_email(gift_enrollment, request=None):
    """
    Send gift invite email to recipient.
    Triggered: Immediately after GiftEnrollment is created and payment is confirmed.
    """
    if not gift_enrollment.recipient_email:
        logger.error(f"Gift {gift_enrollment.id}: recipient_email is empty!")
        return False
    
    # Build claim URL
    if request:
        claim_url = request.build_absolute_uri(
            reverse('claim_gift', kwargs={'gift_token': str(gift_enrollment.gift_token)})
        )
    else:
        site_url = get_site_url()
        claim_url = f"{site_url}{reverse('claim_gift', kwargs={'gift_token': str(gift_enrollment.gift_token)})}"
    
    context = {
        'recipient_name': gift_enrollment.recipient_name,
        'recipient_email': gift_enrollment.recipient_email,
        'sender_name': gift_enrollment.sender_name,
        'gift_message': gift_enrollment.gift_message,
        'course_title': gift_enrollment.course.title,
        'course_description': gift_enrollment.course.description[:200] if gift_enrollment.course.description else None,
        'claim_url': claim_url,
    }
    
    subject = f"You've been gifted a course: {gift_enrollment.course.title}"
    
    return send_email_with_logging(
        subject=subject,
        recipient_list=[gift_enrollment.recipient_email],
        html_template='emails/gift_invite.html',
        text_template=None,  # Can add text version later
        context=context,
    )


def send_gift_confirmation_email(gift_enrollment, request=None):
    """
    Send gift confirmation email to buyer.
    Triggered: After payment confirmed and gift record created.
    """
    if not gift_enrollment.buyer or not gift_enrollment.buyer.email:
        logger.error(f"Gift {gift_enrollment.id}: buyer email is empty!")
        return False
    
    payment_reference = f"GIFT-{gift_enrollment.id}"
    if gift_enrollment.payment:
        payment_reference = gift_enrollment.payment.transaction_id or payment_reference
    
    context = {
        'buyer_name': gift_enrollment.buyer.get_full_name() or gift_enrollment.buyer.username,
        'recipient_email': gift_enrollment.recipient_email,
        'course_title': gift_enrollment.course.title,
        'payment_reference': payment_reference,
        'purchase_date': gift_enrollment.created_at.strftime('%B %d, %Y at %I:%M %p'),
    }
    
    subject = f"Gift Sent: {gift_enrollment.course.title}"
    
    return send_email_with_logging(
        subject=subject,
        recipient_list=[gift_enrollment.buyer.email],
        html_template='emails/gift_confirmation.html',
        text_template=None,
        context=context,
    )


def send_claim_success_email(gift_enrollment, enrollment, request=None, notify_buyer=True):
    """
    Send claim success email to recipient and optionally to buyer.
    Triggered: When recipient successfully claims gift and enrollment is created.
    
    Args:
        gift_enrollment: The GiftEnrollment object
        enrollment: The created Enrollment object
        request: Django request object (optional)
        notify_buyer: Whether to notify the buyer (default: True)
    """
    if not enrollment or not enrollment.user or not enrollment.user.email:
        logger.error(f"Claim success email: enrollment user email is empty!")
        return False
    
    # Build course URL
    if request:
        course_url = request.build_absolute_uri(
            reverse('student_course_player_enrollment', kwargs={'enrollment_id': enrollment.id})
        )
    else:
        site_url = get_site_url()
        course_url = f"{site_url}/student/player/{enrollment.id}/"
    
    # Email to recipient
    context = {
        'recipient_name': enrollment.user.get_full_name() or enrollment.user.username,
        'course_title': enrollment.course.title,
        'course_url': course_url,
    }
    
    subject = f"Welcome to {enrollment.course.title}!"
    
    recipient_result = send_email_with_logging(
        subject=subject,
        recipient_list=[enrollment.user.email],
        html_template='emails/claim_success.html',
        text_template=None,
        context=context,
    )
    
    # Optional: Email to buyer
    buyer_result = 0
    if notify_buyer and gift_enrollment.buyer and gift_enrollment.buyer.email:
        buyer_context = {
            'buyer_name': gift_enrollment.buyer.get_full_name() or gift_enrollment.buyer.username,
            'recipient_email': gift_enrollment.recipient_email,
            'recipient_name': gift_enrollment.recipient_name or gift_enrollment.recipient_email,
            'course_title': gift_enrollment.course.title,
            'claimed_date': gift_enrollment.claimed_at.strftime('%B %d, %Y at %I:%M %p') if gift_enrollment.claimed_at else timezone.now().strftime('%B %d, %Y at %I:%M %p'),
        }
        
        buyer_subject = f"Your gift was claimed: {gift_enrollment.course.title}"
        
        buyer_result = send_email_with_logging(
            subject=buyer_subject,
            recipient_list=[gift_enrollment.buyer.email],
            html_template='emails/gift_claimed_notification.html',
            text_template=None,
            context=buyer_context,
        )
    
    return recipient_result + buyer_result

