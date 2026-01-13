"""
Custom Admin Dashboard Views
User-friendly workflows for content managers and admins.
This is separate from Django Admin which is for technical users.

Pattern:
- Django Admin (/django-admin/) → Technical/Developer tool
- Custom Dashboard (/dashboard/) → User-facing admin tool
- Both access the same database/models
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Sum, Q, Avg, F, Value, CharField, FloatField
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth, Coalesce
from django.utils import timezone
from datetime import timedelta
from collections import Counter, defaultdict
from django.views.decorators.http import require_POST, require_GET
from django.core.paginator import Paginator
from django.db import connection
from django.db.utils import OperationalError, DatabaseError
from django.urls import reverse

from .models import (
    User, UserProfile, Course, Enrollment, LessonProgress, QuizAttempt,
    Payment, Media, SiteSettings, PlacementTest, Teacher, CourseTeacher,
    Category, Review, TutorMessage, TutorConversation, CoursePricing, Partner,
    LiveClassSession, SecurityActionLog, LiveClassTeacherAssignment, TeacherAvailability,
    Lead, LeadTimelineEvent, GiftEnrollmentLeadLink, EnrollmentLeadLink, GiftEnrollment
)
from .views import role_required, get_or_create_profile
from django.http import JsonResponse
import json


# ============================================
# DASHBOARD OVERVIEW
# ============================================

@login_required
@role_required(['admin'])
def dashboard_overview(request):
    """
    Dashboard overview - User-friendly admin dashboard
    Shows KPIs, action items, and quick access to common workflows
    """
    try:
        connection.ensure_connection()
        
        today = timezone.now().date()
        month_start = today.replace(day=1)
        
        # KPIs
        new_students_today = User.objects.filter(date_joined__date=today).count()
        revenue_this_month = Payment.objects.filter(
            status='completed',
            created_at__date__gte=month_start
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Course completion rate
        total_enrollments = Enrollment.objects.count()
        completed_enrollments = Enrollment.objects.filter(status='completed').count()
        completion_rate = (completed_enrollments / total_enrollments * 100) if total_enrollments > 0 else 0
        
        # Active learners (last 24 hours)
        yesterday = timezone.now() - timezone.timedelta(hours=24)
        active_learners = LessonProgress.objects.filter(
            started_at__gte=yesterday
        ).values('enrollment__user').distinct().count()
        
        # Quiz pass rate
        total_attempts = QuizAttempt.objects.count()
        passed_attempts = QuizAttempt.objects.filter(passed=True).count()
        quiz_pass_rate = (passed_attempts / total_attempts * 100) if total_attempts > 0 else 0
        
        # Support flags (failed payments, stuck students)
        failed_payments = Payment.objects.filter(status='failed').count()
        stuck_students = Enrollment.objects.filter(
            status='active',
            progress_percentage__lt=25,
            enrolled_at__lt=timezone.now() - timezone.timedelta(days=14)
        ).count()
        
        # Course popularity
        popular_courses = Course.objects.filter(status='published').order_by('-enrolled_count')[:5]
        
        # Conversion funnel
        placement_tests_taken = PlacementTest.objects.count()
        purchases = Payment.objects.filter(status='completed').count()
        
        # Action items
        action_items = []
        
        if stuck_students > 0:
            try:
                users_url = reverse('dashboard:users') + '?status=stuck'
            except Exception:
                users_url = '/dashboard/users/?status=stuck'
            action_items.append({
                'type': 'warning',
                'title': f'{stuck_students} students stuck at early milestones',
                'description': 'Students with <25% progress after 2 weeks',
                'icon': 'fa-exclamation-triangle',
                'color': 'red',
                'url': users_url
            })
        
        if failed_payments > 0:
            try:
                payments_url = reverse('dashboard:payments') + '?status=failed'
            except Exception:
                payments_url = '/dashboard/payments/?status=failed'
            action_items.append({
                'type': 'warning',
                'title': f'{failed_payments} payment failures in queue',
                'description': 'Requires manual review',
                'icon': 'fa-credit-card',
                'color': 'orange',
                'url': payments_url
            })
        
        context = {
            'new_students_today': new_students_today,
            'revenue_this_month': revenue_this_month,
            'completion_rate': completion_rate,
            'active_learners': active_learners,
            'quiz_pass_rate': quiz_pass_rate,
            'support_flags': failed_payments + stuck_students,
            'popular_courses': popular_courses,
            'placement_tests_taken': placement_tests_taken,
            'purchases': purchases,
            'completions': completed_enrollments,
            'action_items': action_items,
        }
        return render(request, 'dashboard/overview.html', context)
    
    except (OperationalError, DatabaseError):
        connection.close()
        messages.error(request, 'Database connection error. Please try again.')
        context = {
            'new_students_today': 0,
            'revenue_this_month': 0,
            'completion_rate': 0,
            'active_learners': 0,
            'quiz_pass_rate': 0,
            'support_flags': 0,
            'popular_courses': [],
            'placement_tests_taken': 0,
            'purchases': 0,
            'completions': 0,
            'action_items': [],
        }
        return render(request, 'dashboard/overview.html', context)


# ============================================
# CONTENT MANAGEMENT (User-friendly workflows)
# ============================================

@login_required
@role_required(['admin'])
def dashboard_hero(request):
    """
    Edit hero section - User-friendly workflow
    (Django Admin can edit SiteSettings model directly)
    """
    settings = SiteSettings.get_settings()
    
    if request.method == 'POST':
        try:
            settings.hero_headline = request.POST.get('hero_headline', settings.hero_headline)
            settings.hero_subheadline = request.POST.get('hero_subheadline', settings.hero_subheadline)
            
            if request.FILES.get('hero_background_image'):
                settings.hero_background_image = request.FILES.get('hero_background_image')
            
            settings.save()
            messages.success(request, 'Hero section updated successfully!')
            return redirect('dashboard:hero')
        except Exception as e:
            messages.error(request, f'Error updating hero: {str(e)}')
    
    context = {
        'settings': settings,
    }
    return render(request, 'dashboard/hero.html', context)


@login_required
@role_required(['admin'])
def dashboard_site_images(request):
    """
    Manage site images - User-friendly workflow with image picker
    (Django Admin can edit SiteSettings model directly)
    """
    settings = SiteSettings.get_settings()
    
    if request.method == 'POST':
        try:
            # Update hero background
            if request.FILES.get('hero_background_image'):
                settings.hero_background_image = request.FILES.get('hero_background_image')
            
            # Update section images
            if request.FILES.get('how_it_works_image'):
                settings.how_it_works_image = request.FILES.get('how_it_works_image')
            if request.FILES.get('ai_tutor_image'):
                settings.ai_tutor_image = request.FILES.get('ai_tutor_image')
            if request.FILES.get('certificates_image'):
                settings.certificates_image = request.FILES.get('certificates_image')
            if request.FILES.get('pricing_image'):
                settings.pricing_image = request.FILES.get('pricing_image')
            if request.FILES.get('faq_video_thumbnail'):
                settings.faq_video_thumbnail = request.FILES.get('faq_video_thumbnail')
            
            settings.save()
            messages.success(request, 'Site images updated successfully!')
            return redirect('dashboard:site_images')
        except Exception as e:
            messages.error(request, f'Error updating images: {str(e)}')
    
    context = {
        'settings': settings,
    }
    return render(request, 'dashboard/site_images.html', context)


# ============================================
# MEDIA MANAGEMENT (User-friendly interface)
# ============================================

@login_required
@role_required(['admin'])
def dashboard_media(request):
    """
    Media library - User-friendly gallery interface
    (Django Admin can manage Media model directly)
    """
    media_list = Media.objects.select_related('created_by').order_by('-created_at')
    
    # Filters
    category = request.GET.get('category')
    media_type = request.GET.get('media_type')
    search = request.GET.get('search')
    
    if category:
        media_list = media_list.filter(category=category)
    if media_type:
        media_list = media_list.filter(media_type=media_type)
    if search:
        media_list = media_list.filter(
            Q(title__icontains=search) | 
            Q(description__icontains=search) | 
            Q(tags__icontains=search) |
            Q(alt_text__icontains=search)
        )
    
    paginator = Paginator(media_list, 24)
    page = request.GET.get('page', 1)
    media_list = paginator.get_page(page)
    
    context = {
        'media_list': media_list,
        'categories': Media.CATEGORY_CHOICES,
        'media_types': Media.MEDIA_TYPE_CHOICES,
        'current_category': category,
        'current_media_type': media_type,
        'current_search': search,
    }
    return render(request, 'dashboard/media.html', context)


@login_required
@role_required(['admin'])
def dashboard_media_add(request):
    """Add new media - User-friendly upload interface"""
    if request.method == 'POST':
        try:
            # Check if uploading from URL (Cloudinary)
            image_url = request.POST.get('image_url', '').strip()
            
            if image_url:
                # Upload from URL to Cloudinary
                try:
                    import requests
                    from django.core.files.base import ContentFile
                    from .cloudinary_helper import upload_image_from_url
                    
                    folder = f"media/{request.POST.get('category', 'general')}"
                    result = upload_image_from_url(image_url, folder=folder)
                    
                    if result['success']:
                        img_response = requests.get(result['secure_url'], timeout=30)
                        img_response.raise_for_status()
                        
                        media = Media(
                            title=request.POST.get('title', 'Image from URL'),
                            description=request.POST.get('description', ''),
                            media_type=request.POST.get('media_type', 'image'),
                            category=request.POST.get('category', 'general'),
                            alt_text=request.POST.get('alt_text', ''),
                            tags=request.POST.get('tags', ''),
                            created_by=request.user,
                            width=result.get('width'),
                            height=result.get('height'),
                            file_size=result.get('bytes'),
                        )
                        
                        file_extension = result.get('format', 'jpg')
                        img_file = ContentFile(img_response.content)
                        media.file.save(f"{media.title}.{file_extension}", img_file, save=False)
                        media.save()
                        
                        messages.success(request, f'Media "{media.title}" uploaded successfully!')
                    else:
                        messages.error(request, f'Error uploading from URL: {result.get("error")}')
                        return redirect('dashboard:media_add')
                except Exception as e:
                    messages.error(request, f'Error processing URL: {str(e)}')
                    return redirect('dashboard:media_add')
            else:
                # Regular file upload
                media = Media(
                    title=request.POST.get('title', ''),
                    description=request.POST.get('description', ''),
                    file=request.FILES.get('file'),
                    media_type=request.POST.get('media_type', 'image'),
                    category=request.POST.get('category', 'general'),
                    alt_text=request.POST.get('alt_text', ''),
                    tags=request.POST.get('tags', ''),
                    created_by=request.user
                )
                media.save()
                messages.success(request, f'Media "{media.title}" uploaded successfully!')
            
            return redirect('dashboard:media')
        except Exception as e:
            messages.error(request, f'Error uploading media: {str(e)}')
    
    context = {
        'categories': Media.CATEGORY_CHOICES,
        'media_types': Media.MEDIA_TYPE_CHOICES,
    }
    return render(request, 'dashboard/media_add.html', context)


@login_required
@role_required(['admin'])
def dashboard_media_edit(request, media_id):
    """Edit media details - User-friendly interface"""
    media = get_object_or_404(Media, id=media_id)
    
    if request.method == 'POST':
        try:
            media.title = request.POST.get('title', media.title)
            media.description = request.POST.get('description', media.description)
            media.media_type = request.POST.get('media_type', media.media_type)
            media.category = request.POST.get('category', media.category)
            media.alt_text = request.POST.get('alt_text', media.alt_text)
            media.tags = request.POST.get('tags', media.tags)
            
            if request.FILES.get('file'):
                media.file = request.FILES.get('file')
            
            media.save()
            messages.success(request, f'Media "{media.title}" updated successfully!')
            return redirect('dashboard:media')
        except Exception as e:
            messages.error(request, f'Error updating media: {str(e)}')
    
    context = {
        'media': media,
        'categories': Media.CATEGORY_CHOICES,
        'media_types': Media.MEDIA_TYPE_CHOICES,
    }
    return render(request, 'dashboard/media_edit.html', context)


@login_required
@role_required(['admin'])
@require_POST
def dashboard_media_delete(request, media_id):
    """Delete media"""
    media = get_object_or_404(Media, id=media_id)
    title = media.title
    
    try:
        if media.file:
            media.file.delete()
        media.delete()
        messages.success(request, f'Media "{title}" deleted successfully!')
    except Exception as e:
        messages.error(request, f'Error deleting media: {str(e)}')
    
    return redirect('dashboard:media')


# ============================================
# USER MANAGEMENT (User-friendly interface)
# ============================================

@login_required
@role_required(['admin'])
def dashboard_users(request):
    """
    User management - User-friendly interface
    (Django Admin can manage User model directly)
    """
    users = User.objects.select_related('profile').order_by('-date_joined')
    
    # Filters
    role = request.GET.get('role')
    status = request.GET.get('status')
    search = request.GET.get('search')
    
    if role:
        users = users.filter(profile__role=role)
    if status == 'active':
        users = users.filter(is_active=True)
    elif status == 'inactive':
        users = users.filter(is_active=False)
    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    
    paginator = Paginator(users, 20)
    page = request.GET.get('page', 1)
    users = paginator.get_page(page)
    
    context = {
        'users': users,
    }
    return render(request, 'dashboard/users.html', context)


# ============================================
# COURSE MANAGEMENT (User-friendly interface)
# ============================================

@login_required
@role_required(['admin'])
def dashboard_courses(request):
    """
    Course management - User-friendly interface
    """
    courses = Course.objects.select_related('category', 'instructor').order_by('-created_at')
    
    status = request.GET.get('status')
    course_type = request.GET.get('type')
    search = request.GET.get('search')
    
    if status:
        courses = courses.filter(status=status)
    if course_type:
        courses = courses.filter(course_type=course_type)
    if search:
        courses = courses.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search) |
            Q(slug__icontains=search)
        )
    
    paginator = Paginator(courses, 20)
    page = request.GET.get('page', 1)
    try:
        courses_page = paginator.get_page(page)
    except:
        courses_page = paginator.get_page(1)
    
    context = {
        'courses': courses_page,
        'status_filter': status,
        'type_filter': course_type,
        'search_query': search,
    }
    return render(request, 'dashboard/courses.html', context)


@login_required
@role_required(['admin'])
def dashboard_course_create(request):
    """Create new course"""
    from myApp.models import Category
    
    if request.method == 'POST':
        try:
            from django.utils.text import slugify
            from django.utils import timezone
            
            title = request.POST.get('title')
            slug = request.POST.get('slug') or slugify(title)
            
            # Ensure unique slug
            base_slug = slug
            counter = 1
            while Course.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            
            course = Course.objects.create(
                title=title,
                slug=slug,
                description=request.POST.get('description', ''),
                short_description=request.POST.get('short_description', '')[:300],
                outcome=request.POST.get('outcome', ''),
                category_id=request.POST.get('category') or None,
                level=request.POST.get('level', 'beginner'),
                course_type=request.POST.get('course_type', 'recorded'),
                language=request.POST.get('language', 'en'),
                price=request.POST.get('price', 0) or 0,
                currency=request.POST.get('currency', 'USD'),
                is_free=request.POST.get('is_free') == 'on',
                estimated_hours=request.POST.get('estimated_hours', 10) or 10,
                has_certificate=request.POST.get('has_certificate') == 'on',
                has_ai_tutor=request.POST.get('has_ai_tutor') == 'on',
                has_quizzes=request.POST.get('has_quizzes') == 'on',
                status=request.POST.get('status', 'draft'),
                instructor_id=request.POST.get('instructor') or None,
            )
            
            if course.status == 'published' and not course.published_at:
                course.published_at = timezone.now()
                course.save()
            
            messages.success(request, f'Course "{course.title}" created successfully!')
            return redirect('dashboard:course_edit', course_id=course.id)
        except Exception as e:
            messages.error(request, f'Error creating course: {str(e)}')
    
    categories = Category.objects.all()
    instructors = User.objects.filter(profile__role='instructor').select_related('profile')
    
    context = {
        'categories': categories,
        'instructors': instructors,
    }
    return render(request, 'dashboard/course_create.html', context)


@login_required
@role_required(['admin'])
def dashboard_course_edit(request, course_id):
    """Edit course"""
    course = get_object_or_404(Course, id=course_id)
    from myApp.models import Category
    
    if request.method == 'POST':
        try:
            from django.utils.text import slugify
            from django.utils import timezone
            
            course.title = request.POST.get('title')
            slug = request.POST.get('slug') or slugify(course.title)
            
            # Ensure unique slug (except for current course)
            if slug != course.slug:
                base_slug = slug
                counter = 1
                while Course.objects.filter(slug=slug).exclude(id=course.id).exists():
                    slug = f"{base_slug}-{counter}"
                    counter += 1
                course.slug = slug
            
            course.description = request.POST.get('description', '')
            course.short_description = request.POST.get('short_description', '')[:300]
            course.outcome = request.POST.get('outcome', '')
            course.category_id = request.POST.get('category') or None
            course.level = request.POST.get('level', 'beginner')
            course.course_type = request.POST.get('course_type', 'recorded')
            course.language = request.POST.get('language', 'en')
            course.price = request.POST.get('price', 0) or 0
            course.currency = request.POST.get('currency', 'USD')
            course.is_free = request.POST.get('is_free') == 'on'
            course.estimated_hours = request.POST.get('estimated_hours', 10) or 10
            course.has_certificate = request.POST.get('has_certificate') == 'on'
            course.has_ai_tutor = request.POST.get('has_ai_tutor') == 'on'
            course.has_quizzes = request.POST.get('has_quizzes') == 'on'
            
            old_status = course.status
            course.status = request.POST.get('status', 'draft')
            
            # Set published_at if publishing for first time
            if course.status == 'published' and old_status != 'published' and not course.published_at:
                course.published_at = timezone.now()
            
            course.instructor_id = request.POST.get('instructor') or None
            
            # Handle thumbnail upload
            if 'thumbnail' in request.FILES:
                course.thumbnail = request.FILES['thumbnail']
            
            course.save()
            
            messages.success(request, f'Course "{course.title}" updated successfully!')
            return redirect('dashboard:course_edit', course_id=course.id)
        except Exception as e:
            messages.error(request, f'Error updating course: {str(e)}')
    
    categories = Category.objects.all()
    instructors = User.objects.filter(profile__role='instructor').select_related('profile')
    
    context = {
        'course': course,
        'categories': categories,
        'instructors': instructors,
    }
    return render(request, 'dashboard/course_edit.html', context)


@login_required
@role_required(['admin'])
@require_POST
def dashboard_course_toggle_publish(request, course_id):
    """Toggle course publish/unpublish status"""
    from django.utils import timezone
    course = get_object_or_404(Course, id=course_id)
    
    if course.status == 'published':
        course.status = 'draft'
        messages.success(request, f'Course "{course.title}" unpublished')
    else:
        course.status = 'published'
        if not course.published_at:
            course.published_at = timezone.now()
        messages.success(request, f'Course "{course.title}" published')
    
    course.save()
    return redirect('dashboard:courses')


# ============================================
# LIVE CLASSES MANAGEMENT
# ============================================

@login_required
@role_required(['admin'])
def dashboard_live_classes(request):
    """Admin dashboard for managing live class sessions"""
    from django.utils import timezone
    from datetime import timedelta
    
    live_classes = LiveClassSession.objects.select_related('course', 'teacher__user').order_by('-scheduled_start')
    
    # Filters
    status = request.GET.get('status')
    course_id = request.GET.get('course')
    teacher_id = request.GET.get('teacher')
    date_filter = request.GET.get('date_filter')
    search = request.GET.get('search')
    
    if status:
        live_classes = live_classes.filter(status=status)
    if course_id:
        live_classes = live_classes.filter(course_id=course_id)
    if teacher_id:
        live_classes = live_classes.filter(teacher_id=teacher_id)
    if date_filter == 'today':
        today = timezone.now().date()
        live_classes = live_classes.filter(scheduled_start__date=today)
    elif date_filter == 'upcoming':
        live_classes = live_classes.filter(scheduled_start__gt=timezone.now())
    elif date_filter == 'past':
        live_classes = live_classes.filter(scheduled_start__lt=timezone.now())
    if search:
        live_classes = live_classes.filter(
            Q(title__icontains=search) |
            Q(course__title__icontains=search) |
            Q(teacher__user__username__icontains=search)
        )
    
    paginator = Paginator(live_classes, 20)
    page = request.GET.get('page', 1)
    try:
        live_classes_page = paginator.get_page(page)
    except:
        live_classes_page = paginator.get_page(1)
    
    # Get filter options
    courses = Course.objects.filter(course_type__in=['live', 'hybrid']).order_by('title')
    teachers = Teacher.objects.filter(is_approved=True).select_related('user').order_by('user__username')
    
    context = {
        'live_classes': live_classes_page,
        'status_filter': status,
        'course_filter': course_id,
        'teacher_filter': teacher_id,
        'date_filter': date_filter,
        'search_query': search,
        'courses': courses,
        'teachers': teachers,
    }
    return render(request, 'dashboard/live_classes.html', context)


@login_required
@role_required(['admin'])
def dashboard_live_class_create(request):
    """Create new live class session"""
    from django.utils import timezone
    from datetime import timedelta
    
    if request.method == 'POST':
        try:
            course_id = request.POST.get('course')
            teacher_id = request.POST.get('teacher', '').strip()
            title = request.POST.get('title')
            scheduled_start_str = request.POST.get('scheduled_start')
            duration_minutes = int(request.POST.get('duration_minutes', 60))
            meeting_link = request.POST.get('meeting_link', '').strip()
            total_seats = int(request.POST.get('total_seats', 10))
            
            course = get_object_or_404(Course, id=course_id)
            # Handle teacher assignment - make it non-blocking
            teacher = None
            if teacher_id:
                try:
                    teacher = Teacher.objects.get(id=teacher_id)
                except Teacher.DoesNotExist:
                    # Teacher not found - log but don't block creation
                    print(f"WARNING: Teacher with ID {teacher_id} not found. Creating live class without teacher assignment.")
                    messages.warning(request, f'Teacher with ID {teacher_id} not found. Live class will be created without a teacher assignment.')
            
            # Parse datetime - handle None/empty strings safely
            scheduled_start = None
            try:
                from django.utils.dateparse import parse_datetime
                if scheduled_start_str:
                    scheduled_start = parse_datetime(str(scheduled_start_str))
            except (ValueError, TypeError, AttributeError) as e:
                print(f"WARNING: Error parsing scheduled_start_str: {str(e)}")
                scheduled_start = None
            
            if not scheduled_start:
                # Try parsing as date + time separately
                date_str = request.POST.get('scheduled_date')
                time_str = request.POST.get('scheduled_time')
                if date_str and time_str:
                    try:
                        from datetime import datetime
                        scheduled_start = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                        scheduled_start = timezone.make_aware(scheduled_start)
                    except (ValueError, TypeError, AttributeError) as e:
                        print(f"WARNING: Error parsing date/time: {str(e)}")
                        scheduled_start = None
            
            if not scheduled_start:
                messages.error(request, 'Please provide a valid date and time for the live class.')
                return redirect('dashboard:live_class_create')
            
            # Compute scheduled_end safely
            try:
                scheduled_end = scheduled_start + timedelta(minutes=duration_minutes)
            except (TypeError, ValueError) as e:
                print(f"ERROR: Failed to compute scheduled_end: {str(e)}")
                messages.error(request, 'Invalid scheduled start time or duration.')
                return redirect('dashboard:live_class_create')
            
            # Check for conflicts if teacher is assigned (non-blocking - errors are ignored)
            teacher_conflict = False
            if teacher:
                try:
                    start_utc = scheduled_start
                    end_utc = scheduled_end
                    if hasattr(scheduled_start, 'tzinfo') and scheduled_start.tzinfo is None:
                        start_utc = timezone.make_aware(scheduled_start)
                    if hasattr(scheduled_end, 'tzinfo') and scheduled_end.tzinfo is None:
                        end_utc = timezone.make_aware(scheduled_end)
                    
                    conflict = LiveClassSession.objects.filter(
                        teacher=teacher,
                        status__in=['draft', 'scheduled', 'live'],
                    ).filter(
                        Q(start_at_utc__lt=end_utc, end_at_utc__gt=start_utc) |
                        Q(scheduled_start__lt=end_utc, scheduled_end__gt=start_utc)
                    ).exists()
                    
                    override_conflict = request.POST.get('override_conflict') == 'on'
                    if conflict and not override_conflict:
                        teacher_conflict = True
                        messages.warning(request, f'Teacher {teacher.user.username} has a conflicting session at this time. Live class will be created anyway. You can override conflicts if needed.')
                except Exception as e:
                    # Ignore conflict check errors - don't block creation
                    print(f"WARNING: Error checking teacher conflicts (non-blocking): {str(e)}")
                    teacher_conflict = False
            
            # Create session (always proceed, regardless of teacher assignment status)
            # Safely compute UTC times
            try:
                if hasattr(scheduled_start, 'tzinfo') and scheduled_start.tzinfo is None:
                    start_at_utc = timezone.make_aware(scheduled_start)
                else:
                    start_at_utc = scheduled_start
            except Exception as e:
                print(f"WARNING: Error making start timezone-aware (non-blocking): {str(e)}")
                start_at_utc = scheduled_start
            
            try:
                if hasattr(scheduled_end, 'tzinfo') and scheduled_end.tzinfo is None:
                    end_at_utc = timezone.make_aware(scheduled_end)
                else:
                    end_at_utc = scheduled_end
            except Exception as e:
                print(f"WARNING: Error making end timezone-aware (non-blocking): {str(e)}")
                end_at_utc = scheduled_end
            
            # Create the live class session
            try:
                live_class = LiveClassSession.objects.create(
                    course=course,
                    teacher=teacher,
                    title=title,
                    description=request.POST.get('description', ''),
                    scheduled_start=scheduled_start,
                    scheduled_end=scheduled_end,
                    start_at_utc=start_at_utc,
                    end_at_utc=end_at_utc,
                    duration_minutes=duration_minutes,
                    timezone_snapshot=request.POST.get('timezone', 'UTC'),
                    meeting_link=meeting_link or '',
                    meeting_provider=request.POST.get('meeting_provider', 'zoom'),
                    meeting_id=request.POST.get('meeting_id', ''),
                    meeting_passcode=request.POST.get('meeting_passcode', ''),
                    total_seats=total_seats,
                    seats_taken=0,
                    enable_waitlist=request.POST.get('enable_waitlist') == 'on',
                    status=request.POST.get('status', 'draft'),
                    reminder_sent=False,
                )
            except Exception as create_error:
                # If creation fails, try again with minimal fields (override model save method issues)
                import traceback
                print(f"WARNING: First creation attempt failed: {str(create_error)}")
                print(traceback.format_exc())
                try:
                    # Try creating with minimal required fields only
                    live_class = LiveClassSession(
                        course=course,
                        teacher=teacher,
                        title=title,
                        description=request.POST.get('description', ''),
                        scheduled_start=scheduled_start,
                        scheduled_end=scheduled_end,
                        duration_minutes=duration_minutes,
                        timezone_snapshot=request.POST.get('timezone', 'UTC'),
                        meeting_link=meeting_link or '',
                        meeting_provider=request.POST.get('meeting_provider', 'zoom'),
                        meeting_id=request.POST.get('meeting_id', ''),
                        meeting_passcode=request.POST.get('meeting_passcode', ''),
                        total_seats=total_seats,
                        seats_taken=0,
                        enable_waitlist=request.POST.get('enable_waitlist') == 'on',
                        status=request.POST.get('status', 'draft'),
                        reminder_sent=False,
                    )
                    # Try to set UTC fields separately to avoid save() method issues
                    try:
                        live_class.start_at_utc = start_at_utc
                        live_class.end_at_utc = end_at_utc
                    except Exception:
                        pass  # Ignore UTC field errors
                    live_class.save()
                except Exception as second_error:
                    # Last resort: re-raise with detailed error
                    raise Exception(f"Failed to create live class: {str(second_error)}. Original error: {str(create_error)}")
            
            # Create audit log entry if teacher assigned (non-blocking - errors are ignored)
            if teacher:
                try:
                    assignment = LiveClassTeacherAssignment.objects.create(
                        session=live_class,
                        assigned_by=request.user,
                        new_teacher=teacher,
                        reason=request.POST.get('assignment_reason', ''),
                        notes=request.POST.get('assignment_notes', ''),
                    )
                except Exception as e:
                    # Ignore assignment log errors - don't block creation
                    print(f"WARNING: Error creating teacher assignment log (non-blocking): {str(e)}")
                
                # Create activity log entry (non-blocking)
                try:
                    from myApp.activity_log import log_teacher_assigned
                    log_teacher_assigned(live_class, teacher, request.user, reason=request.POST.get('assignment_reason'))
                except Exception as e:
                    # Ignore activity log errors - don't block creation
                    print(f"WARNING: Error creating activity log (non-blocking): {str(e)}")
            
            messages.success(request, f'Live class "{live_class.title}" created successfully!')
            return redirect('dashboard:live_classes')
        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            print(f"ERROR creating live class: {str(e)}")
            print(f"Full traceback:\n{error_traceback}")
            messages.error(request, f'Error creating live class: {str(e)}')
    
    courses = Course.objects.filter(course_type__in=['live', 'hybrid']).order_by('title')
    teachers = Teacher.objects.filter(is_approved=True).select_related('user').order_by('user__username')
    
    context = {
        'courses': courses,
        'teachers': teachers,
    }
    return render(request, 'dashboard/live_class_create.html', context)


@login_required
@role_required(['admin'])
def dashboard_live_class_edit(request, session_id):
    """Edit live class session"""
    live_class = get_object_or_404(LiveClassSession, id=session_id)
    from django.utils import timezone
    from datetime import timedelta
    
    if request.method == 'POST':
        try:
            course_id = request.POST.get('course')
            teacher_id = request.POST.get('teacher')
            title = request.POST.get('title')
            scheduled_start_str = request.POST.get('scheduled_start')
            duration_minutes = int(request.POST.get('duration_minutes', 60))
            meeting_link = request.POST.get('meeting_link', '').strip()
            total_seats = int(request.POST.get('total_seats', 10))
            
            course = get_object_or_404(Course, id=course_id)
            new_teacher = get_object_or_404(Teacher, id=teacher_id) if teacher_id else None
            
            # Parse datetime
            from django.utils.dateparse import parse_datetime
            scheduled_start = parse_datetime(scheduled_start_str)
            if not scheduled_start:
                date_str = request.POST.get('scheduled_date')
                time_str = request.POST.get('scheduled_time')
                if date_str and time_str:
                    from datetime import datetime
                    scheduled_start = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                    scheduled_start = timezone.make_aware(scheduled_start)
            
            if not scheduled_start:
                raise ValueError("Invalid scheduled start time")
            
            scheduled_end = scheduled_start + timedelta(minutes=duration_minutes)
            
            # Check for conflicts if teacher is being changed
            old_teacher = live_class.teacher
            if new_teacher and new_teacher != old_teacher:
                start_utc = scheduled_start
                end_utc = scheduled_end
                if hasattr(scheduled_start, 'tzinfo') and scheduled_start.tzinfo is None:
                    start_utc = timezone.make_aware(scheduled_start)
                if hasattr(scheduled_end, 'tzinfo') and scheduled_end.tzinfo is None:
                    end_utc = timezone.make_aware(scheduled_end)
                
                conflict = LiveClassSession.objects.filter(
                    teacher=new_teacher,
                    status__in=['draft', 'scheduled', 'live'],
                ).exclude(id=live_class.id).filter(
                    Q(start_at_utc__lt=end_utc, end_at_utc__gt=start_utc) |
                    Q(scheduled_start__lt=end_utc, scheduled_end__gt=start_utc)
                ).exists()
                
                if conflict and request.POST.get('override_conflict') != 'on':
                    messages.error(request, f'Teacher {new_teacher.user.username} has a conflicting session at this time. Check "Override conflict" to proceed.')
                    return redirect('dashboard:live_class_edit', session_id=live_class.id)
            
            # Update session
            live_class.course = course
            live_class.title = title
            live_class.description = request.POST.get('description', '')
            live_class.scheduled_start = scheduled_start
            live_class.scheduled_end = scheduled_end
            live_class.start_at_utc = timezone.make_aware(scheduled_start) if hasattr(scheduled_start, 'tzinfo') and scheduled_start.tzinfo is None else scheduled_start
            live_class.end_at_utc = timezone.make_aware(scheduled_end) if hasattr(scheduled_end, 'tzinfo') and scheduled_end.tzinfo is None else scheduled_end
            live_class.duration_minutes = duration_minutes
            live_class.timezone_snapshot = request.POST.get('timezone', 'UTC')
            live_class.meeting_link = meeting_link or ''
            live_class.meeting_provider = request.POST.get('meeting_provider', 'zoom')
            live_class.meeting_id = request.POST.get('meeting_id', '')
            live_class.meeting_passcode = request.POST.get('meeting_passcode', '')
            live_class.total_seats = total_seats
            live_class.enable_waitlist = request.POST.get('enable_waitlist') == 'on'
            live_class.status = request.POST.get('status', 'draft')
            
            # Handle teacher assignment/reassignment
            if new_teacher != old_teacher:
                live_class.teacher = new_teacher
                # Create audit log entry
                assignment = LiveClassTeacherAssignment.objects.create(
                    session=live_class,
                    assigned_by=request.user,
                    old_teacher=old_teacher,
                    new_teacher=new_teacher,
                    reason=request.POST.get('assignment_reason', ''),
                    notes=request.POST.get('assignment_notes', ''),
                )
                # Create activity log entry
                try:
                    from myApp.activity_log import log_teacher_reassigned, log_teacher_assigned, log_teacher_unassigned
                    if old_teacher and new_teacher:
                        log_teacher_reassigned(live_class, old_teacher, new_teacher, request.user, reason=request.POST.get('assignment_reason'))
                    elif new_teacher:
                        log_teacher_assigned(live_class, new_teacher, request.user, reason=request.POST.get('assignment_reason'))
                    elif old_teacher:
                        log_teacher_unassigned(live_class, old_teacher, request.user, reason=request.POST.get('assignment_reason'))
                except Exception:
                    pass
            
            live_class.save()
            
            messages.success(request, f'Live class "{live_class.title}" updated successfully!')
            return redirect('dashboard:live_class_detail', session_id=live_class.id)
        except Exception as e:
            messages.error(request, f'Error updating live class: {str(e)}')
    
    courses = Course.objects.filter(course_type__in=['live', 'hybrid']).order_by('title')
    teachers = Teacher.objects.filter(is_approved=True).select_related('user').order_by('user__username')
    
    # Get assignment history
    assignment_history = LiveClassTeacherAssignment.objects.filter(session=live_class).select_related('assigned_by', 'old_teacher__user', 'new_teacher__user').order_by('-created_at')
    
    context = {
        'live_class': live_class,
        'courses': courses,
        'teachers': teachers,
        'assignment_history': assignment_history,
    }
    return render(request, 'dashboard/live_class_edit.html', context)


@login_required
@role_required(['admin'])
def dashboard_live_class_detail(request, session_id):
    """View live class session details"""
    live_class = get_object_or_404(LiveClassSession.objects.select_related('course', 'teacher__user'), id=session_id)
    
    # Get assignment history
    assignment_history = LiveClassTeacherAssignment.objects.filter(session=live_class).select_related('assigned_by', 'old_teacher__user', 'new_teacher__user').order_by('-created_at')
    
    # Get activity logs
    from myApp.models import ActivityLog
    activity_logs = ActivityLog.objects.filter(
        entity_type='live_class',
        entity_id=live_class.id
    ).select_related('actor').order_by('-created_at')
    
    # Get bookings
    from myApp.models import LiveClassBooking
    bookings = LiveClassBooking.objects.filter(
        course=live_class.course,
        start_at_utc=live_class.start_at_utc
    ).select_related('student_user').order_by('-created_at')[:10]
    
    context = {
        'live_class': live_class,
        'assignment_history': assignment_history,
        'activity_logs': activity_logs,
        'bookings': bookings,
    }
    return render(request, 'dashboard/live_class_detail.html', context)


@login_required
@role_required(['admin'])
@require_GET
def dashboard_check_teacher_availability(request):
    """API endpoint to check teacher availability and conflicts"""
    from django.http import JsonResponse
    from django.utils import timezone
    from datetime import timedelta
    import json
    
    teacher_id = request.GET.get('teacher_id')
    start_time_str = request.GET.get('start_time')
    end_time_str = request.GET.get('end_time')
    exclude_session_id = request.GET.get('exclude_session_id')
    
    if not teacher_id:
        return JsonResponse({'error': 'Missing required parameter: teacher_id'}, status=400)
    
    try:
        teacher = Teacher.objects.get(id=teacher_id)
        
        # Get upcoming sessions count (always available)
        upcoming_sessions_count = LiveClassSession.objects.filter(
            teacher=teacher,
            status__in=['draft', 'scheduled', 'live'],
            scheduled_start__gt=timezone.now()
        ).count()
        
        # If start_time and end_time are not provided, just return the count
        if not start_time_str or not end_time_str:
            return JsonResponse({
                'upcoming_sessions_count': upcoming_sessions_count,
                'has_conflict': False,
                'has_availability': None,
                'conflicts': [],
            })
        
        # Parse datetime strings
        from django.utils.dateparse import parse_datetime
        start_time = parse_datetime(start_time_str)
        end_time = parse_datetime(end_time_str)
        
        if not start_time or not end_time:
            return JsonResponse({'error': 'Invalid datetime format'}, status=400)
        
        # Make timezone-aware if needed
        if hasattr(start_time, 'tzinfo') and start_time.tzinfo is None:
            start_time = timezone.make_aware(start_time)
        if hasattr(end_time, 'tzinfo') and end_time.tzinfo is None:
            end_time = timezone.make_aware(end_time)
        
        # Check for conflicts
        conflicting_sessions = LiveClassSession.objects.filter(
            teacher=teacher,
            status__in=['draft', 'scheduled', 'live'],
        )
        if exclude_session_id:
            conflicting_sessions = conflicting_sessions.exclude(id=exclude_session_id)
        
        conflicts = conflicting_sessions.filter(
            Q(start_at_utc__lt=end_time, end_at_utc__gt=start_time) |
            Q(scheduled_start__lt=end_time, scheduled_end__gt=start_time)
        )
        
        # Check availability slots
        session_day = start_time.weekday()
        session_time = start_time.time()
        
        # Check if teacher has availability for this time
        availability_slots = TeacherAvailability.objects.filter(
            teacher=teacher,
            is_active=True,
            is_blocked=False,
        )
        
        # Check recurring slots
        recurring_match = availability_slots.filter(
            slot_type='recurring',
            day_of_week=session_day,
            start_time__lte=session_time,
            end_time__gte=session_time,
        )
        
        # Check one-time slots
        one_time_match = availability_slots.filter(
            slot_type='one_time',
            start_datetime__lte=start_time,
            end_datetime__gte=end_time,
        )
        
        has_availability = recurring_match.exists() or one_time_match.exists()
        
        conflicts_list = []
        for c in conflicts[:5]:
            conflict_data = {
                'id': c.id,
                'title': c.title or 'Untitled Session',
            }
            # Safely handle datetime serialization
            if c.scheduled_start:
                try:
                    conflict_data['start'] = c.scheduled_start.isoformat()
                except (AttributeError, TypeError):
                    conflict_data['start'] = None
            else:
                conflict_data['start'] = None
            
            if c.scheduled_end:
                try:
                    conflict_data['end'] = c.scheduled_end.isoformat()
                except (AttributeError, TypeError):
                    conflict_data['end'] = None
            else:
                conflict_data['end'] = None
            
            conflicts_list.append(conflict_data)
        
        return JsonResponse({
            'has_conflict': conflicts.exists(),
            'has_availability': has_availability,
            'conflicts': conflicts_list,
            'upcoming_sessions_count': upcoming_sessions_count,
        })
    except Teacher.DoesNotExist:
        return JsonResponse({'error': 'Teacher not found'}, status=404)
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        print(f"ERROR in check_teacher_availability: {str(e)}")
        print(f"Full traceback:\n{error_traceback}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@role_required(['admin'])
@require_POST
def dashboard_create_course_api(request):
    """API endpoint to create a course (returns JSON)"""
    from django.http import JsonResponse
    from django.utils.text import slugify
    from django.utils import timezone
    from myApp.models import Category
    import json
    
    try:
        # Handle JSON request body
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
        
        title = data.get('title', '').strip()
        if not title:
            return JsonResponse({'error': 'Course title is required'}, status=400)
        
        # Generate slug
        slug = data.get('slug', '').strip() or slugify(title)
        base_slug = slug
        counter = 1
        while Course.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        # Get price and currency
        price = data.get('price', 0)
        if price:
            try:
                price = float(price)
            except (ValueError, TypeError):
                price = 0
        else:
            price = 0
        
        currency = data.get('currency', 'USD')
        is_free = data.get('is_free') == True or data.get('is_free') == 'true' or price == 0
        
        # Create course with minimal required fields
        course = Course.objects.create(
            title=title,
            slug=slug,
            description=data.get('description', ''),
            short_description=data.get('short_description', '')[:300],
            course_type=data.get('course_type', 'live'),  # Default to 'live' for live classes
            level=data.get('level', 'beginner'),
            price=price,
            currency=currency,
            is_free=is_free,
            status='draft',
        )
        
        return JsonResponse({
            'success': True,
            'course': {
                'id': course.id,
                'title': course.title,
                'slug': course.slug,
                'description': course.description,
                'course_type': course.course_type,
                'level': course.level,
                'price': float(course.price),
                'currency': course.currency,
                'is_free': course.is_free,
            }
        }, status=201)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@role_required(['admin'])
def dashboard_get_course_api(request, course_id):
    """API endpoint to get course data (returns JSON)"""
    from django.http import JsonResponse
    
    try:
        course = get_object_or_404(Course, id=course_id)
        return JsonResponse({
            'success': True,
            'course': {
                'id': course.id,
                'title': course.title,
                'description': course.description,
                'course_type': course.course_type,
                'level': course.level,
                'price': float(course.price),
                'currency': course.currency,
                'is_free': course.is_free,
            }
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@role_required(['admin'])
@require_POST
def dashboard_update_course_api(request, course_id):
    """API endpoint to update a course (returns JSON)"""
    from django.http import JsonResponse
    import json
    
    try:
        course = get_object_or_404(Course, id=course_id)
        
        # Handle JSON request body
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
        
        # Update course fields
        title = data.get('title', '').strip()
        if title:
            course.title = title
        
        if 'description' in data:
            course.description = data.get('description', '')
        
        if 'course_type' in data:
            course.course_type = data.get('course_type', course.course_type)
        
        if 'level' in data:
            course.level = data.get('level', course.level)
        
        # Get price and currency
        if 'price' in data:
            price = data.get('price', 0)
            if price:
                try:
                    price = float(price)
                except (ValueError, TypeError):
                    price = course.price
            else:
                price = 0
            course.price = price
        
        if 'currency' in data:
            course.currency = data.get('currency', course.currency)
        
        if 'is_free' in data:
            is_free = data.get('is_free') == True or data.get('is_free') == 'true'
            course.is_free = is_free
            if is_free:
                course.price = 0
        
        course.save()
        
        return JsonResponse({
            'success': True,
            'course': {
                'id': course.id,
                'title': course.title,
                'slug': course.slug,
                'description': course.description,
                'course_type': course.course_type,
                'level': course.level,
                'price': float(course.price),
                'currency': course.currency,
                'is_free': course.is_free,
            }
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ============================================
# CRM - LEAD TRACKER
# ============================================

@login_required
@role_required(['admin'])
def dashboard_leads(request):
    """CRM Lead list page"""
    leads = Lead.objects.select_related('owner', 'linked_user').prefetch_related(
        'gift_enrollments__gift_enrollment__course',
        'enrollments__enrollment__course'
    ).order_by('-updated_at')
    
    # Filters
    status = request.GET.get('status')
    source = request.GET.get('source')
    owner_id = request.GET.get('owner')
    search = request.GET.get('search')
    sort = request.GET.get('sort', 'updated')
    
    if status:
        leads = leads.filter(status=status)
    if source:
        leads = leads.filter(source=source)
    if owner_id:
        leads = leads.filter(owner_id=owner_id)
    if search:
        leads = leads.filter(
            Q(name__icontains=search) |
            Q(email__icontains=search) |
            Q(phone__icontains=search)
        )
    
    # Sorting
    if sort == 'updated':
        leads = leads.order_by('-updated_at')
    elif sort == 'contact':
        leads = leads.order_by('-last_contact_date', '-updated_at')
    elif sort == 'created':
        leads = leads.order_by('-created_at')
    elif sort == 'name':
        leads = leads.order_by('name')
    
    paginator = Paginator(leads, 20)
    page = request.GET.get('page', 1)
    try:
        leads_page = paginator.get_page(page)
    except:
        leads_page = paginator.get_page(1)
    
    # Get filter options
    owners = User.objects.filter(profile__role__in=['admin', 'staff']).select_related('profile').order_by('username')
    
    context = {
        'leads': leads_page,
        'status_filter': status,
        'source_filter': source,
        'owner_filter': owner_id,
        'search_query': search,
        'sort': sort,
        'owners': owners,
    }
    return render(request, 'dashboard/leads.html', context)


@login_required
@role_required(['admin'])
def dashboard_lead_detail(request, lead_id):
    """CRM Lead detail page (read-only)"""
    lead = get_object_or_404(Lead.objects.select_related('owner', 'linked_user'), id=lead_id)
    
    # Get timeline events
    timeline_events = LeadTimelineEvent.objects.filter(lead=lead).select_related('actor').order_by('-created_at')
    
    # Get activity logs
    from myApp.models import ActivityLog
    activity_logs = ActivityLog.objects.filter(
        entity_type='lead',
        entity_id=lead.id
    ).select_related('actor').order_by('-created_at')
    
    # Get linked records
    gift_enrollments = GiftEnrollmentLeadLink.objects.filter(lead=lead).select_related('gift_enrollment__course', 'gift_enrollment__buyer').order_by('-created_at')
    enrollments = EnrollmentLeadLink.objects.filter(lead=lead).select_related('enrollment__course', 'enrollment__user').order_by('-created_at')
    
    # Get all users for linking
    users = User.objects.all().order_by('username')
    
    context = {
        'lead': lead,
        'timeline_events': timeline_events,
        'activity_logs': activity_logs,
        'gift_enrollments': gift_enrollments,
        'enrollments': enrollments,
        'users': users,
    }
    return render(request, 'dashboard/lead_detail.html', context)


@login_required
@role_required(['admin'])
def dashboard_lead_create(request):
    """Create new lead"""
    if request.method == 'POST':
        try:
            lead = Lead.objects.create(
                name=request.POST.get('name'),
                email=request.POST.get('email') or None,
                phone=request.POST.get('phone', ''),
                source=request.POST.get('source', 'other'),
                status=request.POST.get('status', 'new'),
                notes=request.POST.get('notes', ''),
                owner_id=request.POST.get('owner') or None,
            )
            
            # Create timeline event
            LeadTimelineEvent.objects.create(
                lead=lead,
                event_type='LEAD_CREATED',
                actor=request.user,
                summary=f"Lead created by {request.user.get_full_name() or request.user.username}",
                metadata={'source': lead.source}
            )
            
            messages.success(request, f'Lead "{lead.name}" created successfully!')
            return redirect('dashboard:lead_detail', lead_id=lead.id)
        except Exception as e:
            messages.error(request, f'Error creating lead: {str(e)}')
    
    owners = User.objects.filter(profile__role__in=['admin', 'staff']).select_related('profile').order_by('username')
    
    context = {
        'owners': owners,
    }
    return render(request, 'dashboard/lead_create.html', context)


@login_required
@role_required(['admin'])
def dashboard_lead_edit(request, lead_id):
    """Edit lead"""
    lead = get_object_or_404(Lead, id=lead_id)
    
    if request.method == 'POST':
        try:
            old_status = lead.status
            old_owner = lead.owner
            
            lead.name = request.POST.get('name')
            lead.email = request.POST.get('email') or None
            lead.phone = request.POST.get('phone', '')
            lead.source = request.POST.get('source', 'other')
            lead.status = request.POST.get('status', 'new')
            lead.notes = request.POST.get('notes', '')
            lead.owner_id = request.POST.get('owner') or None
            
            # Update last contact date if status changed to contacted/follow_up
            if lead.status in ['contacted', 'follow_up'] and not lead.last_contact_date:
                lead.last_contact_date = timezone.now()
            
            lead.save()
            
            # Create timeline events for changes
            if old_status != lead.status:
                LeadTimelineEvent.objects.create(
                    lead=lead,
                    event_type='LEAD_STATUS_CHANGED',
                    actor=request.user,
                    summary=f"Status changed from {dict(Lead.STATUS_CHOICES).get(old_status, old_status)} to {lead.get_status_display()}",
                    metadata={'old_status': old_status, 'new_status': lead.status}
                )
                # Create activity log entry
                try:
                    from myApp.activity_log import log_lead_status_updated
                    log_lead_status_updated(lead, old_status, lead.status, actor=request.user)
                except Exception:
                    pass
            
            if old_owner != lead.owner:
                LeadTimelineEvent.objects.create(
                    lead=lead,
                    event_type='LEAD_OWNER_CHANGED',
                    actor=request.user,
                    summary=f"Owner changed to {lead.owner.get_full_name() if lead.owner else 'Unassigned'}",
                    metadata={'old_owner_id': old_owner.id if old_owner else None, 'new_owner_id': lead.owner.id if lead.owner else None}
                )
            
            # General update event
            LeadTimelineEvent.objects.create(
                lead=lead,
                event_type='LEAD_UPDATED',
                actor=request.user,
                summary=f"Lead updated by {request.user.get_full_name() or request.user.username}",
                metadata={}
            )
            
            messages.success(request, f'Lead "{lead.name}" updated successfully!')
            return redirect('dashboard:lead_detail', lead_id=lead.id)
        except Exception as e:
            messages.error(request, f'Error updating lead: {str(e)}')
    
    owners = User.objects.filter(profile__role__in=['admin', 'staff']).select_related('profile').order_by('username')
    users = User.objects.all().order_by('username')
    
    context = {
        'lead': lead,
        'owners': owners,
        'users': users,
    }
    return render(request, 'dashboard/lead_edit.html', context)


@login_required
@role_required(['admin'])
@require_POST
def dashboard_lead_add_note(request, lead_id):
    """Add note to lead"""
    lead = get_object_or_404(Lead, id=lead_id)
    
    note_text = request.POST.get('note', '').strip()
    if not note_text:
        messages.error(request, 'Note cannot be empty')
        return redirect('dashboard:lead_detail', lead_id=lead.id)
    
    # Append note
    if lead.notes:
        lead.notes += f"\n\n[{timezone.now().strftime('%Y-%m-%d %H:%M')}] {note_text}"
    else:
        lead.notes = f"[{timezone.now().strftime('%Y-%m-%d %H:%M')}] {note_text}"
    
    lead.save(update_fields=['notes', 'updated_at'])
    
    # Create timeline event
    LeadTimelineEvent.objects.create(
        lead=lead,
        event_type='LEAD_NOTE_ADDED',
        actor=request.user,
        summary=f"Note added: {note_text[:100]}",
        metadata={'note_length': len(note_text)}
    )
    
    messages.success(request, 'Note added successfully!')
    return redirect('dashboard:lead_detail', lead_id=lead.id)


@login_required
@role_required(['admin'])
@require_POST
def dashboard_lead_link_user(request, lead_id):
    """Manually link/unlink user to lead"""
    lead = get_object_or_404(Lead, id=lead_id)
    user_id = request.POST.get('user_id')
    action = request.POST.get('action', 'link')
    
    if action == 'link' and user_id:
        user = get_object_or_404(User, id=user_id)
        lead.linked_user = user
        lead.save(update_fields=['linked_user', 'updated_at'])
        
        LeadTimelineEvent.objects.create(
            lead=lead,
            event_type='USER_LINKED_TO_LEAD',
            actor=request.user,
            summary=f"User {user.get_full_name() or user.username} manually linked to lead",
            metadata={'user_id': user.id, 'manual': True}
        )
        messages.success(request, f'User linked to lead successfully!')
    elif action == 'unlink':
        old_user = lead.linked_user
        lead.linked_user = None
        lead.save(update_fields=['linked_user', 'updated_at'])
        
        LeadTimelineEvent.objects.create(
            lead=lead,
            event_type='USER_UNLINKED_FROM_LEAD',
            actor=request.user,
            summary=f"User {old_user.get_full_name() if old_user else 'Unknown'} unlinked from lead",
            metadata={'user_id': old_user.id if old_user else None, 'manual': True}
        )
        messages.success(request, 'User unlinked from lead successfully!')
    
    return redirect('dashboard:lead_detail', lead_id=lead.id)


@login_required
@role_required(['admin'])
@require_POST
def dashboard_lead_link_gift(request, lead_id):
    """Manually link/unlink gift enrollment to lead"""
    lead = get_object_or_404(Lead, id=lead_id)
    gift_id = request.POST.get('gift_id')
    action = request.POST.get('action', 'link')
    
    if action == 'link' and gift_id:
        gift = get_object_or_404(GiftEnrollment, id=gift_id)
        link, created = GiftEnrollmentLeadLink.objects.get_or_create(
            gift_enrollment=gift,
            lead=lead,
            defaults={'created_by': request.user}
        )
        
        if created:
            LeadTimelineEvent.objects.create(
                lead=lead,
                event_type='GIFT_LINKED_TO_LEAD',
                actor=request.user,
                summary=f"Gift enrollment for {gift.course.title} manually linked to lead",
                metadata={'gift_id': gift.id, 'manual': True}
            )
            messages.success(request, 'Gift enrollment linked to lead successfully!')
        else:
            messages.info(request, 'Gift enrollment already linked to this lead')
    elif action == 'unlink' and gift_id:
        gift = get_object_or_404(GiftEnrollment, id=gift_id)
        GiftEnrollmentLeadLink.objects.filter(gift_enrollment=gift, lead=lead).delete()
        
        LeadTimelineEvent.objects.create(
            lead=lead,
            event_type='GIFT_UNLINKED_FROM_LEAD',
            actor=request.user,
            summary=f"Gift enrollment for {gift.course.title} unlinked from lead",
            metadata={'gift_id': gift.id, 'manual': True}
        )
        messages.success(request, 'Gift enrollment unlinked from lead successfully!')
    
    return redirect('dashboard:lead_detail', lead_id=lead.id)


@login_required
@role_required(['admin'])
@require_POST
def dashboard_lead_link_enrollment(request, lead_id):
    """Manually link/unlink enrollment to lead"""
    lead = get_object_or_404(Lead, id=lead_id)
    enrollment_id = request.POST.get('enrollment_id')
    action = request.POST.get('action', 'link')
    
    if action == 'link' and enrollment_id:
        enrollment = get_object_or_404(Enrollment, id=enrollment_id)
        link, created = EnrollmentLeadLink.objects.get_or_create(
            enrollment=enrollment,
            lead=lead,
            defaults={'created_by': request.user}
        )
        
        if created:
            LeadTimelineEvent.objects.create(
                lead=lead,
                event_type='ENROLLMENT_LINKED_TO_LEAD',
                actor=request.user,
                summary=f"Enrollment in {enrollment.course.title} manually linked to lead",
                metadata={'enrollment_id': enrollment.id, 'manual': True}
            )
            messages.success(request, 'Enrollment linked to lead successfully!')
        else:
            messages.info(request, 'Enrollment already linked to this lead')
    elif action == 'unlink' and enrollment_id:
        enrollment = get_object_or_404(Enrollment, id=enrollment_id)
        EnrollmentLeadLink.objects.filter(enrollment=enrollment, lead=lead).delete()
        
        LeadTimelineEvent.objects.create(
            lead=lead,
            event_type='ENROLLMENT_UNLINKED_FROM_LEAD',
            actor=request.user,
            summary=f"Enrollment in {enrollment.course.title} unlinked from lead",
            metadata={'enrollment_id': enrollment.id, 'manual': True}
        )
        messages.success(request, 'Enrollment unlinked from lead successfully!')
    
    return redirect('dashboard:lead_detail', lead_id=lead.id)


@login_required
@role_required(['admin'])
def dashboard_crm_analytics(request):
    """CRM Analytics dashboard"""
    from datetime import timedelta
    
    # Date filters
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    owner_filter = request.GET.get('owner')
    source_filter = request.GET.get('source')
    
    # Base queryset
    leads = Lead.objects.all()
    
    if date_from:
        try:
            from datetime import datetime
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            leads = leads.filter(created_at__gte=date_from_obj)
        except:
            pass
    
    if date_to:
        try:
            from datetime import datetime
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            leads = leads.filter(created_at__lte=date_to_obj)
        except:
            pass
    
    if owner_filter:
        leads = leads.filter(owner_id=owner_filter)
    
    if source_filter:
        leads = leads.filter(source=source_filter)
    
    # Metrics
    total_leads = leads.count()
    leads_by_status = leads.values('status').annotate(count=Count('id')).order_by('status')
    
    enrolled_leads = leads.filter(status='enrolled').count()
    conversion_rate = (enrolled_leads / total_leads * 100) if total_leads > 0 else 0
    
    # Source performance
    source_performance = []
    for source_code, source_name in Lead.SOURCE_CHOICES:
        source_leads = leads.filter(source=source_code)
        source_count = source_leads.count()
        source_enrolled = source_leads.filter(status='enrolled').count()
        source_conversion = (source_enrolled / source_count * 100) if source_count > 0 else 0
        
        source_performance.append({
            'source': source_name,
            'code': source_code,
            'lead_count': source_count,
            'enrolled_count': source_enrolled,
            'conversion_rate': source_conversion,
        })
    
    # Sort by lead count
    source_performance.sort(key=lambda x: x['lead_count'], reverse=True)
    
    # Get filter options
    owners = User.objects.filter(profile__role__in=['admin', 'staff']).select_related('profile').order_by('username')
    
    context = {
        'total_leads': total_leads,
        'leads_by_status': leads_by_status,
        'enrolled_leads': enrolled_leads,
        'conversion_rate': conversion_rate,
        'source_performance': source_performance,
        'date_from': date_from,
        'date_to': date_to,
        'owner_filter': owner_filter,
        'source_filter': source_filter,
        'owners': owners,
    }
    return render(request, 'dashboard/crm_analytics.html', context)


# ============================================
# PAYMENT MANAGEMENT (User-friendly interface)
# ============================================

@login_required
@role_required(['admin'])
def dashboard_payments(request):
    """
    Payment management - User-friendly interface
    (Django Admin can manage Payment model directly)
    """
    payments = Payment.objects.select_related('user', 'course').order_by('-created_at')
    
    status = request.GET.get('status')
    search = request.GET.get('search')
    
    if status:
        payments = payments.filter(status=status)
    if search:
        payments = payments.filter(
            Q(user__username__icontains=search) |
            Q(user__email__icontains=search) |
            Q(course__title__icontains=search)
        )
    
    paginator = Paginator(payments, 20)
    page = request.GET.get('page', 1)
    payments = paginator.get_page(page)
    
    context = {
        'payments': payments,
    }
    return render(request, 'dashboard/payments.html', context)


# ============================================
# GIFTED COURSES MANAGEMENT
# ============================================

@login_required
@role_required(['admin'])
def dashboard_gifted_courses(request):
    """Admin dashboard for managing gifted courses"""
    import logging
    logger = logging.getLogger(__name__)
    from myApp.models import GiftEnrollment
    
    # Log query attempt
    logger.info(f"Admin dashboard: Querying GiftEnrollment records. User: {request.user.username}")
    
    # Get total count before filters
    total_count = GiftEnrollment.objects.count()
    logger.info(f"Total GiftEnrollment records in database: {total_count}")
    
    gifts = GiftEnrollment.objects.select_related('buyer', 'course', 'payment', 'enrollment').order_by('-created_at')
    
    # Filters
    status = request.GET.get('status')
    search = request.GET.get('search')
    
    if status:
        gifts = gifts.filter(status=status)
        logger.info(f"Filtered by status: {status}")
    if search:
        gifts = gifts.filter(
            Q(buyer__username__icontains=search) |
            Q(buyer__email__icontains=search) |
            Q(recipient_email__icontains=search) |
            Q(course__title__icontains=search)
        )
        logger.info(f"Filtered by search: {search}")
    
    # Log filtered count
    filtered_count = gifts.count()
    logger.info(f"GiftEnrollment records after filters: {filtered_count}")
    
    paginator = Paginator(gifts, 20)
    page = request.GET.get('page', 1)
    try:
        gifts_page = paginator.get_page(page)
    except:
        gifts_page = paginator.get_page(1)
    
    logger.info(f"Rendering page {page} with {gifts_page.object_list.count()} gifts")
    
    context = {
        'gifts': gifts_page,
        'status_filter': status,
        'search_query': search,
        'total_count': total_count,
    }
    return render(request, 'dashboard/gifted_courses.html', context)


@login_required
@role_required(['admin'])
@require_POST
def dashboard_resend_gift_email(request, gift_id):
    """Resend gift email to recipient"""
    from myApp.models import GiftEnrollment
    from myApp.views import send_gift_email
    
    gift = get_object_or_404(GiftEnrollment, id=gift_id)
    
    if gift.status != 'pending_claim':
        messages.error(request, 'Can only resend email for pending gifts')
        return redirect('dashboard:gifted_courses')
    
    try:
        send_gift_email(gift, request)
        messages.success(request, f'Gift email resent to {gift.recipient_email}')
    except Exception as e:
        messages.error(request, f'Failed to resend email: {str(e)}')
    
    return redirect('dashboard:gifted_courses')


@login_required
@role_required(['admin'])
@require_POST
def dashboard_manual_claim_gift(request, gift_id):
    """Manually mark gift as claimed (support use)"""
    from myApp.models import GiftEnrollment, User
    
    gift = get_object_or_404(GiftEnrollment, id=gift_id)
    
    if gift.status != 'pending_claim':
        messages.error(request, 'Gift has already been claimed')
        return redirect('dashboard:gifted_courses')
    
    # Try to find user by email
    try:
        user = User.objects.get(email__iexact=gift.recipient_email)
        
        # Claim the gift
        try:
            enrollment = gift.claim(user)
            messages.success(request, f'Gift claimed successfully for {user.username}')
        except ValueError as e:
            messages.error(request, f'Failed to claim gift: {str(e)}')
    except User.DoesNotExist:
        messages.error(request, f'No user found with email {gift.recipient_email}. User must create an account first.')
    
    return redirect('dashboard:gifted_courses')


# ============================================
# TEACHER MANAGEMENT
# ============================================

@login_required
@role_required(['admin'])
def dashboard_teachers(request):
    """Teacher management"""
    teachers = Teacher.objects.select_related('user', 'approved_by').order_by('-created_at')
    
    # Get stats before filtering
    total_teachers = Teacher.objects.count()
    pending_count = Teacher.objects.filter(is_approved=False).count()
    approved_count = Teacher.objects.filter(is_approved=True).count()
    
    # Filters
    status = request.GET.get('status')
    search = request.GET.get('search')
    
    if status == 'approved':
        teachers = teachers.filter(is_approved=True)
    elif status == 'pending':
        teachers = teachers.filter(is_approved=False)
    
    if search:
        teachers = teachers.filter(
            Q(user__username__icontains=search) |
            Q(user__email__icontains=search) |
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search) |
            Q(specialization__icontains=search) |
            Q(bio__icontains=search)
        )
    
    paginator = Paginator(teachers, 20)
    page = request.GET.get('page', 1)
    teachers = paginator.get_page(page)
    
    context = {
        'teachers': teachers,
        'selected_status': status,
        'search_query': search,
        'total_teachers': total_teachers,
        'pending_count': pending_count,
        'approved_count': approved_count,
    }
    return render(request, 'dashboard/teachers.html', context)


@login_required
@role_required(['admin'])
@require_POST
def dashboard_teacher_approve(request, teacher_id):
    """Approve teacher"""
    teacher = get_object_or_404(Teacher, id=teacher_id)
    teacher.is_approved = True
    teacher.approved_at = timezone.now()
    teacher.approved_by = request.user
    teacher.save()
    
    # Update user profile role
    profile = get_or_create_profile(teacher.user)
    profile.role = 'instructor'
    profile.save()
    
    messages.success(request, f'Teacher {teacher.user.username} approved successfully!')
    return redirect('dashboard:teachers')


@login_required
@role_required(['admin'])
@require_POST
def dashboard_teacher_reject(request, teacher_id):
    """Reject teacher"""
    teacher = get_object_or_404(Teacher, id=teacher_id)
    teacher.is_approved = False
    teacher.save()
    
    messages.success(request, f'Teacher {teacher.user.username} rejected.')
    return redirect('dashboard:teachers')


@login_required
@role_required(['admin'])
def dashboard_teacher_details(request, teacher_id):
    """Get teacher details for AJAX modal (JSON response)"""
    from django.http import JsonResponse
    from django.db.models import Count
    
    teacher = get_object_or_404(Teacher.objects.select_related('user', 'approved_by'), id=teacher_id)
    
    # Get course count (courses where user is instructor)
    courses_count = Course.objects.filter(instructor=teacher.user).count()
    
    # Get live classes count
    live_classes_count = LiveClassSession.objects.filter(teacher=teacher).count()
    
    # Build response data
    data = {
        'id': teacher.id,
        'basic_info': {
            'full_name': teacher.user.get_full_name() or teacher.user.username,
            'username': teacher.user.username,
            'email': teacher.user.email,
            'role': teacher.user.profile.role if hasattr(teacher.user, 'profile') else 'instructor',
            'date_applied': teacher.created_at.strftime('%B %d, %Y at %I:%M %p') if teacher.created_at else 'N/A',
            'status': 'Approved' if teacher.is_approved else 'Pending',
            'is_active': teacher.user.is_active,
        },
        'professional': {
            'specialization': teacher.specialization or 'Not specified',
            'years_experience': teacher.years_experience or 0,
            'bio': teacher.bio or 'No bio provided',
            'courses_created': courses_count,
            'live_classes_hosted': live_classes_count,
            'permission_level': teacher.get_permission_level_display(),
        },
        'verification': {
            'is_approved': teacher.is_approved,
            'approved_by': teacher.approved_by.get_full_name() if teacher.approved_by else None,
            'approved_by_username': teacher.approved_by.username if teacher.approved_by else None,
            'approved_at': teacher.approved_at.strftime('%B %d, %Y at %I:%M %p') if teacher.approved_at else None,
            'approved_at_relative': teacher.approved_at.strftime('%Y-%m-%d %H:%M:%S') if teacher.approved_at else None,
        },
        'account': {
            'date_joined': teacher.user.date_joined.strftime('%B %d, %Y') if teacher.user.date_joined else 'N/A',
            'last_login': teacher.user.last_login.strftime('%B %d, %Y at %I:%M %p') if teacher.user.last_login else 'Never',
            'is_staff': teacher.user.is_staff,
            'is_superuser': teacher.user.is_superuser,
        }
    }
    
    return JsonResponse(data)


@login_required
@role_required(['admin'])
@require_POST
def dashboard_teacher_reset_password(request, teacher_id):
    """Reset teacher password with admin verification"""
    from django.contrib.auth import authenticate
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.http import urlsafe_base64_encode
    from django.utils.encoding import force_bytes
    from django.core.mail import send_mail
    from django.conf import settings
    import json
    import secrets
    import string
    
    teacher = get_object_or_404(Teacher.objects.select_related('user'), id=teacher_id)
    target_user = teacher.user
    
    # Get admin password from request
    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
    except:
        data = request.POST
    
    admin_password = data.get('admin_password', '')
    
    # Verify admin password
    admin_user = authenticate(request, username=request.user.username, password=admin_password)
    if not admin_user or admin_user != request.user:
        return JsonResponse({'success': False, 'error': 'Invalid admin password. Verification failed.'}, status=403)
    
    # Generate secure random password
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    new_password = ''.join(secrets.choice(alphabet) for i in range(16))
    
    # Set new password
    target_user.set_password(new_password)
    target_user.save()
    
    # Send password reset email
    try:
        token = default_token_generator.make_token(target_user)
        uid = urlsafe_base64_encode(force_bytes(target_user.pk))
        reset_url = request.build_absolute_uri(f'/accounts/password_reset_confirm/{uid}/{token}/')
        
        send_mail(
            subject='Your Fluentory Password Has Been Reset',
            message=f'''Hello {target_user.get_full_name() or target_user.username},

Your password has been reset by an administrator.

To set your new password, please click the link below:
{reset_url}

If you did not request this change, please contact support immediately.

Best regards,
Fluentory Team''',
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@fluentory.com'),
            recipient_list=[target_user.email],
            fail_silently=False,
        )
    except Exception as e:
        # Log error but don't fail the operation
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to send password reset email: {e}")
    
    # Log the action
    SecurityActionLog.objects.create(
        admin_user=request.user,
        target_user=target_user,
        action_type='password_reset',
        description=f'Password reset initiated by admin {request.user.username}',
        metadata=json.dumps({
            'teacher_id': teacher_id,
            'email_sent': True,
            'reset_method': 'email'
        })
    )
    
    return JsonResponse({
        'success': True,
        'message': 'Password reset initiated. Teacher will receive instructions by email.'
    })


@login_required
@role_required(['admin'])
@require_POST
def dashboard_teacher_force_password_reset(request, teacher_id):
    """Force password reset on next login"""
    from django.contrib.auth import authenticate
    import json
    
    teacher = get_object_or_404(Teacher.objects.select_related('user'), id=teacher_id)
    target_user = teacher.user
    
    # Get admin password from request
    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
    except:
        data = request.POST
    
    admin_password = data.get('admin_password', '')
    force_reset = data.get('force_reset', 'true').lower() == 'true'
    
    # Verify admin password
    admin_user = authenticate(request, username=request.user.username, password=admin_password)
    if not admin_user or admin_user != request.user:
        return JsonResponse({'success': False, 'error': 'Invalid admin password. Verification failed.'}, status=403)
    
    # Update force_password_reset flag
    profile = get_or_create_profile(target_user)
    profile.force_password_reset = force_reset
    profile.save()
    
    # Log the action
    SecurityActionLog.objects.create(
        admin_user=request.user,
        target_user=target_user,
        action_type='force_password_reset',
        description=f'Force password reset {"enabled" if force_reset else "disabled"} by admin {request.user.username}',
        metadata=json.dumps({
            'teacher_id': teacher_id,
            'force_reset': force_reset
        })
    )
    
    return JsonResponse({
        'success': True,
        'message': f'Password reset requirement {"enabled" if force_reset else "disabled"} successfully.',
        'force_reset': force_reset
    })


@login_required
@role_required(['admin'])
@require_POST
def dashboard_teacher_assign_course(request, teacher_id):
    """Assign course to teacher"""
    teacher = get_object_or_404(Teacher, id=teacher_id)
    data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
    
    course_id = data.get('course_id')
    permission_level = data.get('permission_level', 'view_only')
    can_create_live_classes = data.get('can_create_live_classes', 'false') == 'true'
    can_manage_schedule = data.get('can_manage_schedule', 'false') == 'true'
    
    course = get_object_or_404(Course, id=course_id)
    
    # Check if already assigned
    assignment, created = CourseTeacher.objects.get_or_create(
        course=course,
        teacher=teacher,
        defaults={
            'permission_level': permission_level,
            'can_create_live_classes': can_create_live_classes,
            'can_manage_schedule': can_manage_schedule,
            'assigned_by': request.user
        }
    )
    
    if not created:
        assignment.permission_level = permission_level
        assignment.can_create_live_classes = can_create_live_classes
        assignment.can_manage_schedule = can_manage_schedule
        assignment.save()
        messages.info(request, 'Assignment updated.')
    else:
        messages.success(request, f'Course "{course.title}" assigned to {teacher.user.username}!')
    
    if request.content_type == 'application/json':
        return JsonResponse({'success': True})
    return redirect('dashboard:teachers')


@login_required
@role_required(['admin'])
@require_POST
def dashboard_teacher_remove_course(request, teacher_id, assignment_id):
    """Remove course assignment from teacher"""
    assignment = get_object_or_404(CourseTeacher, id=assignment_id, teacher_id=teacher_id)
    course_title = assignment.course.title
    assignment.delete()
    
    messages.success(request, f'Course "{course_title}" removed from teacher.')
    return redirect('dashboard:teachers')


# ============================================
# ROLE SWITCHER & IMPERSONATION
# ============================================

@login_required
@role_required(['admin'])
def dashboard_switch_role(request):
    """Role switcher - preview different role views (godlike admin feature)"""
    role = request.GET.get('role')
    
    # Clear impersonation if switching roles
    if 'impersonating_user_id' in request.session:
        del request.session['impersonating_user_id']
        del request.session['impersonating']
    
    # Set preview role in session
    if role == 'student':
        request.session['preview_role'] = 'student'
        request.session['switched_from'] = 'admin'
        messages.info(request, 'Switched to Student view. You can switch back anytime from the admin dashboard.')
        return redirect('student_home')
    elif role == 'teacher':
        request.session['preview_role'] = 'teacher'
        request.session['switched_from'] = 'admin'
        messages.info(request, 'Switched to Teacher view. You can switch back anytime from the admin dashboard.')
        return redirect('teacher_dashboard')
    elif role == 'partner':
        request.session['preview_role'] = 'partner'
        request.session['switched_from'] = 'admin'
        messages.info(request, 'Switched to Partner view. You can switch back anytime from the admin dashboard.')
        return redirect('partner_overview')
    elif role == 'admin' or role == 'admin_dashboard':
        # Return to admin view
        if 'preview_role' in request.session:
            del request.session['preview_role']
        if 'switched_from' in request.session:
            del request.session['switched_from']
        messages.success(request, 'Switched back to Admin view.')
        return redirect('dashboard:overview')
    
    return redirect('dashboard:overview')


@login_required
@role_required(['admin'])
@require_POST
def dashboard_login_as(request, user_id):
    """Login as user (impersonation)"""
    target_user = get_object_or_404(User, id=user_id)
    
    # Store original user ID in session
    request.session['impersonating_user_id'] = request.user.id
    request.session['impersonating'] = True
    
    # Login as target user
    from django.contrib.auth import login
    login(request, target_user)
    
    messages.info(request, f'Now viewing as {target_user.username}. Use Stop Impersonation to return.')
    
    # Redirect based on their role
    from .views import redirect_by_role
    return redirect_by_role(target_user)


@login_required
def dashboard_stop_impersonation(request):
    """Stop impersonation and return to admin"""
    if 'impersonating_user_id' in request.session:
        original_user_id = request.session['impersonating_user_id']
        original_user = get_object_or_404(User, id=original_user_id)
        
        # Clear impersonation session
        del request.session['impersonating_user_id']
        del request.session['impersonating']
        
        # Login as original user
        from django.contrib.auth import login
        login(request, original_user)
        
        messages.success(request, 'Returned to admin view.')
        return redirect('dashboard:overview')
    
    return redirect('dashboard:overview')


# ============================================
# MANUAL ENROLLMENT
# ============================================

@login_required
@role_required(['admin'])
def dashboard_manual_enroll(request):
    """Manually enroll student in course"""
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        course_id = request.POST.get('course_id')
        notes = request.POST.get('notes', '')
        
        user = get_object_or_404(User, id=user_id)
        course = get_object_or_404(Course, id=course_id)
        
        # Check if already enrolled
        enrollment, created = Enrollment.objects.get_or_create(
            user=user,
            course=course,
            defaults={
                'status': 'active',
                'teacher_notes': ''  # Ensure teacher_notes is set to empty string, not None
            }
        )
        
        if created:
            # Create payment record if paid course
            if not course.is_free and course.price > 0:
                Payment.objects.create(
                    user=user,
                    course=course,
                    amount=course.price,
                    currency=course.currency,
                    status='completed',
                    payment_method='partner',
                    created_at=timezone.now(),
                    completed_at=timezone.now()
                )
            
            # Update course stats
            course.enrolled_count += 1
            course.save()
            
            messages.success(request, f'{user.username} enrolled in "{course.title}" successfully!')
        else:
            messages.info(request, f'{user.username} is already enrolled in "{course.title}".')
        
        return redirect('dashboard:manual_enroll')
    
    # Get users and courses for dropdown
    users = User.objects.filter(profile__role='student').order_by('username')[:100]
    courses = Course.objects.filter(status='published').order_by('title')
    
    context = {
        'users': users,
        'courses': courses,
    }
    return render(request, 'dashboard/manual_enroll.html', context)


# ============================================
# COURSE MANAGEMENT (ADMIN)
# ============================================

@login_required
@role_required(['admin'])
def dashboard_course_create(request):
    """Create new course (admin)"""
    if request.method == 'POST':
        course = Course.objects.create(
            title=request.POST.get('title'),
            slug=request.POST.get('slug'),
            description=request.POST.get('description'),
            short_description=request.POST.get('short_description', ''),
            outcome=request.POST.get('outcome', ''),
            category_id=request.POST.get('category'),
            level=request.POST.get('level', 'beginner'),
            instructor_id=request.POST.get('instructor') or None,
            price=float(request.POST.get('price', 0)),
            is_free=request.POST.get('is_free') == 'on',
            status='draft'
        )
        
        messages.success(request, f'Course "{course.title}" created successfully!')
        return redirect('dashboard:course_edit', course_id=course.id)
    
    categories = Category.objects.all()
    instructors = User.objects.filter(profile__role='instructor').order_by('username')
    
    context = {
        'categories': categories,
        'instructors': instructors,
    }
    return render(request, 'dashboard/course_create.html', context)


@login_required
@role_required(['admin'])
def dashboard_course_edit(request, course_id):
    """Edit course (admin)"""
    course = get_object_or_404(Course, id=course_id)
    
    if request.method == 'POST':
        course.title = request.POST.get('title', course.title)
        course.slug = request.POST.get('slug', course.slug)
        course.description = request.POST.get('description', course.description)
        course.short_description = request.POST.get('short_description', course.short_description)
        course.outcome = request.POST.get('outcome', course.outcome)
        course.category_id = request.POST.get('category') or course.category_id
        course.level = request.POST.get('level', course.level)
        course.instructor_id = request.POST.get('instructor') or course.instructor_id
        course.price = float(request.POST.get('price', course.price))
        course.is_free = request.POST.get('is_free') == 'on'
        course.status = request.POST.get('status', course.status)
        
        if request.FILES.get('thumbnail'):
            course.thumbnail = request.FILES.get('thumbnail')
        
        course.save()
        messages.success(request, 'Course updated successfully!')
        return redirect('dashboard:course_edit', course_id=course.id)
    
    categories = Category.objects.all()
    instructors = User.objects.filter(profile__role='instructor').order_by('username')
    modules = course.modules.prefetch_related('lessons').order_by('order')
    
    context = {
        'course': course,
        'categories': categories,
        'instructors': instructors,
        'modules': modules,
    }
    return render(request, 'dashboard/course_edit.html', context)


# ============================================
# USER MANAGEMENT (EXTENDED)
# ============================================

@login_required
@role_required(['admin'])
def dashboard_user_create(request):
    """Create new user (admin)"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        role = request.POST.get('role', 'student')
        
        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        
        # Create profile with role
        profile = get_or_create_profile(user)
        profile.role = role
        profile.save()
        
        # If teacher, create teacher profile and auto-approve
        if role == 'instructor':
            teacher = Teacher.objects.create(
                user=user,
                permission_level='standard',
                is_approved=True,
                approved_by=request.user,
                approved_at=timezone.now()
            )
            messages.success(request, f'Teacher {username} created and auto-approved!')
        else:
            messages.success(request, f'User {username} created successfully!')
        
        return redirect('dashboard:users')
    
    context = {}
    return render(request, 'dashboard/user_create.html', context)


# ============================================
# ANALYTICS DASHBOARD
# ============================================

@login_required
@role_required(['admin'])
def dashboard_analytics(request):
    """
    Comprehensive Analytics Dashboard
    Shows revenue, enrollment funnel, retention, course performance, and AI tutor usage
    """
    now = timezone.now()
    today = now.date()
    month_start = today.replace(day=1)
    week_start = today - timedelta(days=today.weekday())
    
    # Time period filter
    period = request.GET.get('period', 'month')  # day, week, month, year, all
    
    if period == 'day':
        start_date = today
    elif period == 'week':
        start_date = week_start
    elif period == 'month':
        start_date = month_start
    elif period == 'year':
        start_date = today.replace(month=1, day=1)
    else:  # all
        start_date = None
    
    # ============================================
    # 1. REVENUE ANALYTICS
    # ============================================
    revenue_query = Payment.objects.filter(status='completed')
    if start_date:
        revenue_query = revenue_query.filter(created_at__date__gte=start_date)
    
    # Revenue by currency
    revenue_by_currency = Payment.objects.filter(status='completed').values('currency').annotate(
        currency_total_revenue=Sum('amount'),
        count=Count('id')
    ).order_by('-currency_total_revenue')
    
    # Revenue by course (Payment.course reverse relationship is 'payment')
    revenue_by_course = Course.objects.filter(
        payment__status='completed'
    ).annotate(
        course_total_revenue=Sum('payment__amount'),
        payment_count=Count('payment', distinct=True)
    ).filter(course_total_revenue__gt=0).order_by('-course_total_revenue')[:10]
    
    # Revenue by teacher (through courses)
    # Course.instructor has related_name='courses_taught' on User
    # Payment.course reverse relationship is 'payment'
    revenue_by_teacher = Teacher.objects.filter(
        user__courses_taught__payment__status='completed'
    ).annotate(
        teacher_total_revenue=Sum('user__courses_taught__payment__amount'),
        course_count=Count('user__courses_taught', distinct=True)
    ).filter(teacher_total_revenue__gt=0).order_by('-teacher_total_revenue')[:10]
    
    # Revenue by partner (Payment.partner reverse relationship)
    # Note: Partner model has a total_revenue field, so we use partner_total_revenue for annotation
    revenue_by_partner = Partner.objects.filter(
        payment__status='completed'
    ).annotate(
        partner_total_revenue=Sum('payment__amount'),
        payment_count=Count('payment', distinct=True)
    ).filter(partner_total_revenue__gt=0).order_by('-partner_total_revenue')[:10]
    
    # Revenue trends (daily/weekly/monthly)
    revenue_trends_query = Payment.objects.filter(status='completed')
    if start_date:
        revenue_trends_query = revenue_trends_query.filter(created_at__date__gte=start_date)
    
    if period == 'day':
        revenue_trends = revenue_trends_query.annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            revenue=Sum('amount'),
            count=Count('id')
        ).order_by('date')
    elif period == 'week':
        revenue_trends = revenue_trends_query.annotate(
            week=TruncWeek('created_at')
        ).values('week').annotate(
            revenue=Sum('amount'),
            count=Count('id')
        ).order_by('week')
    elif period == 'all':
        # For 'all' period, show monthly trends
        revenue_trends = revenue_trends_query.annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            revenue=Sum('amount'),
            count=Count('id')
        ).order_by('month')
    else:  # month or year
        revenue_trends = revenue_trends_query.annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            revenue=Sum('amount'),
            count=Count('id')
        ).order_by('month')
    
    total_revenue = revenue_query.aggregate(total=Sum('amount'))['total'] or 0
    
    # ============================================
    # 2. ENROLLMENT FUNNEL
    # ============================================
    # Visit → Placement test → Checkout → Enroll → Completion
    total_visits = User.objects.count()  # Approximate by total users
    placement_tests_taken = PlacementTest.objects.count()
    if start_date:
        placement_tests_taken = PlacementTest.objects.filter(taken_at__date__gte=start_date).count()
    
    checkouts = Payment.objects.filter(status__in=['completed', 'pending', 'failed'])
    if start_date:
        checkouts = checkouts.filter(created_at__date__gte=start_date)
    checkout_count = checkouts.count()
    
    enrollments = Enrollment.objects.all()
    if start_date:
        enrollments = enrollments.filter(enrolled_at__date__gte=start_date)
    enrollment_count = enrollments.count()
    
    completions = Enrollment.objects.filter(status='completed', completed_at__isnull=False)
    if start_date:
        completions = completions.filter(completed_at__date__gte=start_date)
    completion_count = completions.count()
    
    # Conversion rates
    visit_to_placement = (placement_tests_taken / total_visits * 100) if total_visits > 0 else 0
    placement_to_checkout = (checkout_count / placement_tests_taken * 100) if placement_tests_taken > 0 else 0
    checkout_to_enroll = (enrollment_count / checkout_count * 100) if checkout_count > 0 else 0
    enroll_to_complete = (completion_count / enrollment_count * 100) if enrollment_count > 0 else 0
    
    # Drop-off analysis
    funnel_data = [
        {'stage': 'Visits', 'count': total_visits, 'percentage': 100},
        {'stage': 'Placement Test', 'count': placement_tests_taken, 'percentage': visit_to_placement},
        {'stage': 'Checkout', 'count': checkout_count, 'percentage': placement_to_checkout},
        {'stage': 'Enrolled', 'count': enrollment_count, 'percentage': checkout_to_enroll},
        {'stage': 'Completed', 'count': completion_count, 'percentage': enroll_to_complete},
    ]
    
    # ============================================
    # 3. STUDENT RETENTION
    # ============================================
    # Week 1/2/4 activity tracking
    week1_cutoff = now - timedelta(days=7)
    week2_cutoff = now - timedelta(days=14)
    week4_cutoff = now - timedelta(days=28)
    
    enrollments_for_retention = Enrollment.objects.filter(enrolled_at__lte=week4_cutoff)
    if start_date:
        enrollments_for_retention = enrollments_for_retention.filter(enrolled_at__date__gte=start_date)
    
    week1_active = enrollments_for_retention.filter(
        enrolled_at__lte=week1_cutoff,
        lesson_progress__started_at__gte=week1_cutoff
    ).values('user').distinct().count()
    
    week2_active = enrollments_for_retention.filter(
        enrolled_at__lte=week2_cutoff,
        lesson_progress__started_at__gte=week2_cutoff
    ).values('user').distinct().count()
    
    week4_active = enrollments_for_retention.filter(
        enrolled_at__lte=week4_cutoff,
        lesson_progress__started_at__gte=week4_cutoff
    ).values('user').distinct().count()
    
    total_for_retention = enrollments_for_retention.values('user').distinct().count()
    
    week1_retention = (week1_active / total_for_retention * 100) if total_for_retention > 0 else 0
    week2_retention = (week2_active / total_for_retention * 100) if total_for_retention > 0 else 0
    week4_retention = (week4_active / total_for_retention * 100) if total_for_retention > 0 else 0
    
    # Churn analysis (enrollments with no activity in last 14 days)
    churn_cutoff = now - timedelta(days=14)
    churned = Enrollment.objects.filter(
        status='active',
        enrolled_at__lt=churn_cutoff
    ).exclude(
        lesson_progress__started_at__gte=churn_cutoff
    ).values('user').distinct().count()
    
    # Engagement metrics (average lessons completed per user)
    avg_lessons_per_user = LessonProgress.objects.filter(completed=True).values('enrollment__user').annotate(
        lesson_count=Count('id')
    ).aggregate(avg=Avg('lesson_count'))['avg'] or 0
    
    # ============================================
    # 4. COURSE PERFORMANCE
    # ============================================
    # Completion rate per course (Course model has completion_rate field, so use computed_completion_rate for annotation)
    course_performance = Course.objects.annotate(
        total_enrollments=Count('enrollments', distinct=True),
        completed_enrollments=Count('enrollments', filter=Q(enrollments__status='completed'), distinct=True),
        avg_rating=Avg('reviews__rating'),
        review_count=Count('reviews', distinct=True)
    ).filter(total_enrollments__gt=0).annotate(
        computed_completion_rate=Count('enrollments', filter=Q(enrollments__status='completed'), distinct=True) * 100.0 / F('total_enrollments')
    ).order_by('-computed_completion_rate')[:20]
    
    # Quiz pass rate per course
    # Quiz has lesson FK with related_name='quizzes'
    # QuizAttempt has quiz FK with related_name='attempts'
    # So path: Course -> modules -> lessons -> quizzes -> attempts
    quiz_performance = Course.objects.annotate(
        total_attempts=Count('modules__lessons__quizzes__attempts', distinct=True),
        passed_attempts=Count('modules__lessons__quizzes__attempts', filter=Q(modules__lessons__quizzes__attempts__passed=True), distinct=True)
    ).filter(total_attempts__gt=0).annotate(
        computed_pass_rate=Count('modules__lessons__quizzes__attempts', filter=Q(modules__lessons__quizzes__attempts__passed=True), distinct=True) * 100.0 / F('total_attempts')
    ).order_by('-computed_pass_rate')[:20]
    
    # Average time-to-complete (calculate in Python for simplicity)
    completed_enrollments = Enrollment.objects.filter(
        status='completed',
        completed_at__isnull=False
    ).select_related('course').values('course__id', 'course__title', 'enrolled_at', 'completed_at')
    
    course_completion_times = defaultdict(list)
    for enroll in completed_enrollments:
        if enroll['enrolled_at'] and enroll['completed_at']:
            delta = enroll['completed_at'] - enroll['enrolled_at']
            days = delta.days + (delta.seconds / 86400.0)
            course_completion_times[(enroll['course__id'], enroll['course__title'])].append(days)
    
    time_to_complete_data = []
    for (course_id, course_title), times in sorted(course_completion_times.items(), key=lambda x: sum(x[1])/len(x[1]))[:20]:
        time_to_complete_data.append({
            'course__id': course_id,
            'course__title': course_title,
            'avg_days': sum(times) / len(times),
            'count': len(times)
        })
    
    # Student satisfaction (ratings)
    course_ratings = Course.objects.annotate(
        avg_rating=Avg('reviews__rating'),
        rating_count=Count('reviews', distinct=True)
    ).filter(rating_count__gt=0).order_by('-avg_rating')[:20]
    
    # ============================================
    # 5. AI TUTOR USAGE
    # ============================================
    ai_query = TutorMessage.objects.all()
    if start_date:
        ai_query = ai_query.filter(created_at__date__gte=start_date)
    
    # Total messages
    total_messages = ai_query.count()
    user_messages = ai_query.filter(role='user').count()
    ai_messages = ai_query.filter(role='assistant').count()
    
    # Token spend
    total_tokens = ai_query.aggregate(total=Sum('tokens_used'))['total'] or 0
    
    # Top user engagement (users with most messages)
    top_users = TutorConversation.objects.annotate(
        message_count=Count('messages'),
        token_count=Sum('messages__tokens_used')
    ).select_related('user', 'course').order_by('-message_count')[:10]
    
    # Common questions analysis (most common user messages)
    common_questions = TutorMessage.objects.filter(
        role='user'
    ).values('content').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    context = {
        # Revenue Analytics
        'total_revenue': total_revenue,
        'revenue_by_currency': revenue_by_currency,
        'revenue_by_course': revenue_by_course,
        'revenue_by_teacher': revenue_by_teacher,
        'revenue_by_partner': revenue_by_partner,
        'revenue_trends': list(revenue_trends),
        'period': period,
        
        # Enrollment Funnel
        'funnel_data': funnel_data,
        'visit_to_placement': visit_to_placement,
        'placement_to_checkout': placement_to_checkout,
        'checkout_to_enroll': checkout_to_enroll,
        'enroll_to_complete': enroll_to_complete,
        
        # Student Retention
        'week1_retention': week1_retention,
        'week2_retention': week2_retention,
        'week4_retention': week4_retention,
        'churned': churned,
        'avg_lessons_per_user': avg_lessons_per_user,
        
        # Course Performance
        'course_performance': course_performance,
        'quiz_performance': quiz_performance,
        'time_to_complete_data': list(time_to_complete_data),
        'course_ratings': course_ratings,
        
        # AI Tutor Usage
        'total_messages': total_messages,
        'user_messages': user_messages,
        'ai_messages': ai_messages,
        'total_tokens': total_tokens,
        'top_users': top_users,
        'common_questions': common_questions,
    }
    
    return render(request, 'dashboard/analytics.html', context)

