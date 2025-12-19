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
from django.db.models import Count, Sum, Q
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db import connection
from django.db.utils import OperationalError, DatabaseError

from .models import (
    User, UserProfile, Course, Enrollment, LessonProgress, QuizAttempt,
    Payment, Media, SiteSettings, PlacementTest
)
from .views import role_required, get_or_create_profile


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
            action_items.append({
                'type': 'warning',
                'title': f'{stuck_students} students stuck at early milestones',
                'description': 'Students with <25% progress after 2 weeks',
                'icon': 'fa-exclamation-triangle',
                'color': 'red',
                'url': '/dashboard/users/?status=stuck'
            })
        
        if failed_payments > 0:
            action_items.append({
                'type': 'warning',
                'title': f'{failed_payments} payment failures in queue',
                'description': 'Requires manual review',
                'icon': 'fa-credit-card',
                'color': 'orange',
                'url': '/dashboard/payments/?status=failed'
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
    (Django Admin can manage Course model directly)
    """
    courses = Course.objects.select_related('category', 'instructor').order_by('-created_at')
    
    status = request.GET.get('status')
    search = request.GET.get('search')
    
    if status:
        courses = courses.filter(status=status)
    if search:
        courses = courses.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search)
        )
    
    paginator = Paginator(courses, 20)
    page = request.GET.get('page', 1)
    courses = paginator.get_page(page)
    
    context = {
        'courses': courses,
    }
    return render(request, 'dashboard/courses.html', context)


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

