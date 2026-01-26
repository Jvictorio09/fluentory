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
from django.db.models import Count, Sum, Q, Avg, F, Value, CharField, FloatField, Max
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
    Lead, LeadTimelineEvent, GiftEnrollmentLeadLink, EnrollmentLeadLink, GiftEnrollment,
    Certificate, Module, Lesson, Quiz, Question, Answer
)
from django.db import models
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
    from myApp.models import UserProfile
    
    # Get all users, handling those without profiles
    users = User.objects.all().order_by('-date_joined')
    
    # Filters - support both 'q' and 'search' for consistency
    role = request.GET.get('role')
    status = request.GET.get('status')
    search = request.GET.get('q') or request.GET.get('search')
    
    if role:
        # Filter by role, including users without profiles (treat as 'student')
        if role == 'student':
            users = users.filter(
                Q(profile__role='student') | Q(profile__isnull=True)
            )
        else:
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
    
    # Prefetch profiles to avoid N+1 queries
    users = users.prefetch_related('profile')
    
    paginator = Paginator(users, 20)
    page = request.GET.get('page', 1)
    try:
        users = paginator.get_page(page)
    except:
        users = paginator.get_page(1)
    
    context = {
        'users': users,
        'selected_role': role,
        'selected_status': status,
        'search_query': search,
    }
    
    # Return partial template for AJAX requests
    if request.GET.get('ajax') == '1' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'dashboard/partials/users_table.html', context)
    
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
    search = request.GET.get('q') or request.GET.get('search')
    
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
    
    # Return partial template for AJAX requests
    if request.GET.get('ajax') == '1' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'dashboard/partials/courses_table.html', context)
    
    return render(request, 'dashboard/courses.html', context)


@login_required
@role_required(['admin'])
@require_POST
def dashboard_courses_bulk_delete(request):
    """Bulk delete courses - Admin can delete any course"""
    from django.http import JsonResponse
    from django.db import connection
    
    def safe_delete(queryset):
        """Safely delete queryset, handling missing tables"""
        try:
            if hasattr(queryset, 'delete'):
                return queryset.delete()[0]
            return 0
        except Exception as e:
            error_str = str(e).lower()
            if 'does not exist' in error_str or 'no such table' in error_str:
                return 0  # Table doesn't exist, skip silently
            # For transaction errors, reset connection
            if 'transaction' in error_str or 'atomic' in error_str:
                connection.close()
                return 0
            return 0
    
    def safe_query(model, **filters):
        """Safely query model, return empty queryset if table doesn't exist"""
        try:
            return model.objects.filter(**filters)
        except Exception as e:
            error_str = str(e).lower()
            if 'does not exist' in error_str or 'no such table' in error_str:
                return model.objects.none()
            # For transaction errors, reset connection
            if 'transaction' in error_str or 'atomic' in error_str:
                connection.close()
                return model.objects.none()
            return model.objects.none()
    
    try:
        course_ids = request.POST.getlist('course_ids[]')
        if not course_ids:
            return JsonResponse({'success': False, 'error': 'No courses selected'}, status=400)
        
        # Get courses to delete
        courses = Course.objects.filter(id__in=course_ids)
        count = courses.count()
        
        if count == 0:
            return JsonResponse({'success': False, 'error': 'No courses found'}, status=400)
        
        # Delete related data first - NO transaction wrapper to avoid transaction errors
        for course in courses:
            # Delete enrollments and related progress
            try:
                enrollments = safe_query(Enrollment, course=course)
                if enrollments.exists():
                    enrollment_ids = list(enrollments.values_list('id', flat=True))
                    if enrollment_ids:
                        safe_delete(LessonProgress.objects.filter(enrollment_id__in=enrollment_ids))
                    safe_delete(enrollments)
            except Exception:
                pass
            
            # Delete certificates
            try:
                safe_delete(safe_query(Certificate, course=course))
            except Exception:
                pass
            
            # Delete reviews
            try:
                safe_delete(safe_query(Review, course=course))
            except Exception:
                pass
            
            # Delete course pricing
            try:
                safe_delete(safe_query(CoursePricing, course=course))
            except Exception:
                pass
            
            # Delete course-teacher links
            try:
                safe_delete(safe_query(CourseTeacher, course=course))
            except Exception:
                pass
            
            # Delete quiz attempts, questions, answers
            try:
                quiz_ids = list(Quiz.objects.filter(
                    Q(course=course) | Q(module__course=course)
                ).values_list('id', flat=True))
                if quiz_ids:
                    safe_delete(QuizAttempt.objects.filter(quiz_id__in=quiz_ids))
                    safe_delete(Question.objects.filter(quiz_id__in=quiz_ids))
            except Exception:
                pass
            
            # Delete modules, lessons, quizzes
            try:
                modules = Module.objects.filter(course=course)
                for module in modules:
                    # Clear unlock_quiz references first
                    try:
                        Lesson.objects.filter(module=module).update(unlock_quiz=None)
                    except Exception:
                        pass
                    # Delete lessons
                    try:
                        safe_delete(Lesson.objects.filter(module=module))
                    except Exception:
                        pass
                    # Delete module quizzes
                    try:
                        safe_delete(Quiz.objects.filter(module=module))
                    except Exception:
                        pass
                
                # Delete modules
                safe_delete(modules)
            except Exception:
                pass
            
            # Delete course-level quizzes
            try:
                safe_delete(Quiz.objects.filter(course=course))
            except Exception:
                pass
            
            # Try to delete booking-related data if tables exist
            try:
                from .models import LiveClassSession, LiveClassBooking, BookingSeries
                safe_delete(LiveClassSession.objects.filter(course=course))
                safe_delete(LiveClassBooking.objects.filter(course=course))
                safe_delete(BookingSeries.objects.filter(course=course))
            except Exception:
                pass
            
            # Try Booking model (might not have table)
            try:
                from .models import Booking
                safe_delete(Booking.objects.filter(session__course=course))
            except Exception:
                pass
            
            # Try OneOnOneBooking
            try:
                from .models import OneOnOneBooking
                safe_delete(OneOnOneBooking.objects.filter(course=course))
            except Exception:
                pass
        
        # Finally delete courses - use raw SQL to avoid Django ORM querying related tables
        try:
            # Get course IDs before deleting (convert to list of integers)
            course_id_list = [int(cid) for cid in course_ids]
            
            # Get the actual table name from the model
            course_table = Course._meta.db_table
            
            # For PostgreSQL, find the actual table name (case-sensitive)
            if 'postgresql' in connection.vendor:
                try:
                    with connection.cursor() as check_cursor:
                        # Query to find the actual table name (case-sensitive)
                        check_cursor.execute("""
                            SELECT table_name 
                            FROM information_schema.tables 
                            WHERE table_schema = 'public' 
                            AND LOWER(table_name) = LOWER(%s)
                            LIMIT 1
                        """, [course_table])
                        result = check_cursor.fetchone()
                        if result:
                            course_table = result[0]  # Use the actual case-sensitive table name
                except:
                    pass  # Fall back to model's db_table
            
            # Quote the table name properly for the database
            quoted_table = connection.ops.quote_name(course_table)
            
            # Use raw SQL to delete courses directly, bypassing ORM relationships
            # This avoids Django checking reverse relationships like Booking
            with connection.cursor() as cursor:
                # PostgreSQL syntax
                if 'postgresql' in connection.vendor:
                    cursor.execute(
                        f"DELETE FROM {quoted_table} WHERE id = ANY(%s)",
                        [course_id_list]
                    )
                else:
                    # SQLite or other databases
                    placeholders = ','.join(['?' if 'sqlite' in connection.vendor.lower() else '%s'] * len(course_id_list))
                    cursor.execute(
                        f"DELETE FROM {quoted_table} WHERE id IN ({placeholders})",
                        course_id_list
                    )
            
            deleted_count = cursor.rowcount if hasattr(cursor, 'rowcount') and cursor.rowcount > 0 else len(course_id_list)
            
        except Exception as e:
            # If raw SQL fails, try to delete one by one with error handling
            deleted_count = 0
            course_table = Course._meta.db_table
            for course_id in course_ids:
                try:
                    # Close connection to reset state
                    connection.close()
                    # Try to delete individual course
                    Course.objects.filter(id=course_id).delete()
                    deleted_count += 1
                except Exception as e2:
                    error_str = str(e2).lower()
                    # If it's a missing table error, try raw SQL for this one
                    if 'does not exist' in error_str or 'booking' in error_str:
                        try:
                            # Get quoted table name
                            if 'postgresql' in connection.vendor:
                                quoted_table = connection.ops.quote_name(Course._meta.db_table)
                            else:
                                quoted_table = Course._meta.db_table
                            
                            with connection.cursor() as cursor:
                                if 'postgresql' in connection.vendor:
                                    cursor.execute(f"DELETE FROM {quoted_table} WHERE id = %s", [course_id])
                                else:
                                    cursor.execute(f"DELETE FROM {quoted_table} WHERE id = ?", [course_id])
                            if cursor.rowcount > 0:
                                deleted_count += 1
                        except:
                            pass
                    pass
            
            if deleted_count == 0:
                raise e
        
        return JsonResponse({
            'success': True, 
            'deleted': deleted_count, 
            'message': f'Deleted {deleted_count} course(s)'
        })
        
        return JsonResponse({'success': True, 'deleted': count, 'message': f'Deleted {count} course(s)'})
        
    except Exception as e:
        import traceback
        error_msg = str(e)
        # Reset connection if transaction error
        if 'transaction' in error_msg.lower() or 'atomic' in error_msg.lower():
            connection.close()
            # Try one more time without transaction
            try:
                Course.objects.filter(id__in=course_ids).delete()
                return JsonResponse({
                    'success': True, 
                    'deleted': count if 'count' in locals() else 0, 
                    'message': f'Deleted courses (some related data may have been skipped)'
                })
            except:
                pass
        
        return JsonResponse({'success': False, 'error': error_msg}, status=500)


@login_required
@role_required(['admin'])
def dashboard_course_create(request):
    """Create new course"""
    from myApp.models import Category
    
    if request.method == 'POST':
        try:
            from django.utils.text import slugify
            from django.utils import timezone
            import logging
            import traceback
            
            logger = logging.getLogger(__name__)
            
            title = request.POST.get('title', '').strip()
            if not title:
                messages.error(request, 'Course title is required.')
                categories = Category.objects.all()
                instructors = User.objects.filter(profile__role='instructor').select_related('profile')
                context = {
                    'categories': categories,
                    'instructors': instructors,
                }
                return render(request, 'dashboard/course_create.html', context)
            
            slug = request.POST.get('slug', '').strip() or slugify(title)
            if not slug:
                slug = slugify(title) or 'course-' + str(timezone.now().timestamp())
            
            # Note: The Course.save() method will automatically ensure slug uniqueness
            # This pre-check is kept for performance optimization, but save() is the safety net
            
            # Convert price to float
            try:
                price = float(request.POST.get('price', 0) or 0)
            except (ValueError, TypeError):
                price = 0.0
            
            # Convert estimated_hours to int
            try:
                estimated_hours = int(request.POST.get('estimated_hours', 10) or 10)
            except (ValueError, TypeError):
                estimated_hours = 10
            
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
                price=price,
                currency=request.POST.get('currency', 'USD'),
                is_free=request.POST.get('is_free') == 'on',
                estimated_hours=estimated_hours,
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
            import logging
            import traceback
            logger = logging.getLogger(__name__)
            error_msg = str(e)
            error_traceback = traceback.format_exc()
            logger.error(f'Error creating course: {error_msg}\n{error_traceback}')
            messages.error(request, f'Error creating course: {error_msg}')
            # Log full traceback to console for debugging
            print(f'\n{"="*50}')
            print(f'ERROR CREATING COURSE:')
            print(f'{error_msg}')
            print(f'\nFull traceback:')
            print(f'{error_traceback}')
            print(f'{"="*50}\n')
    
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
    
    # Get modules, lessons, and quizzes for recorded courses
    modules = []
    quizzes = []
    if course.course_type == 'recorded':
        modules = course.modules.all().prefetch_related('lessons').order_by('order')
        quizzes = course.quizzes.all().order_by('created_at')
    
    context = {
        'course': course,
        'categories': categories,
        'instructors': instructors,
        'modules': modules,
        'quizzes': quizzes,
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
    
    # Filters - support both 'q' and 'search' for consistency
    status = request.GET.get('status')
    course_id = request.GET.get('course')
    teacher_id = request.GET.get('teacher')
    date_filter = request.GET.get('date_filter')
    search = request.GET.get('q') or request.GET.get('search')
    
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
    
    # Return partial template for AJAX requests
    if request.GET.get('ajax') == '1' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'dashboard/partials/live_classes_table.html', context)
    
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
        # Note: The Course.save() method will automatically ensure slug uniqueness
        # This pre-check is kept for performance optimization, but save() is the safety net
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
    
    # Filters - support both 'q' and 'search' for consistency
    status = request.GET.get('status')
    source = request.GET.get('source')
    owner_id = request.GET.get('owner')
    search = request.GET.get('q') or request.GET.get('search')
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
    
    # Return partial template for AJAX requests
    if request.GET.get('ajax') == '1' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'dashboard/partials/leads_table.html', context)
    
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
    search = request.GET.get('q') or request.GET.get('search')
    
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
        'status_filter': status,
        'search_query': search,
    }
    
    # Return partial template for AJAX requests
    if request.GET.get('ajax') == '1' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'dashboard/partials/payments_table.html', context)
    
    return render(request, 'dashboard/payments.html', context)


# ============================================
# GIFTED COURSES MANAGEMENT
# ============================================

@login_required
@role_required(['admin'])
def dashboard_gifted_courses(request):
    """Admin dashboard for managing gifted courses"""
    import logging
    from django.db.utils import ProgrammingError, OperationalError
    logger = logging.getLogger(__name__)
    from myApp.models import GiftEnrollment
    
    # Log query attempt
    logger.info(f"Admin dashboard: Querying GiftEnrollment records. User: {request.user.username}")
    
    # Safely get total count - handle missing table
    try:
        total_count = GiftEnrollment.objects.count()
        logger.info(f"Total GiftEnrollment records in database: {total_count}")
    except (ProgrammingError, OperationalError) as e:
        error_str = str(e).lower()
        if 'does not exist' in error_str or 'no such table' in error_str:
            logger.warning(f"GiftEnrollment table does not exist yet. Showing empty list.")
            total_count = 0
            # Return empty page
            empty_list = []
            paginator = Paginator(empty_list, 20)
            gifts_page = paginator.get_page(1)
            
            context = {
                'gifts': gifts_page,
                'status_filter': None,
                'search_query': None,
                'total_count': 0,
                'table_missing': True,
            }
            return render(request, 'dashboard/gifted_courses.html', context)
        else:
            raise
    
    gifts = GiftEnrollment.objects.select_related('buyer', 'course', 'payment', 'enrollment').order_by('-created_at')
    
    # Filters - support both 'q' and 'search' for consistency
    status = request.GET.get('status')
    search = request.GET.get('q') or request.GET.get('search')
    
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
    try:
        filtered_count = gifts.count()
        logger.info(f"GiftEnrollment records after filters: {filtered_count}")
    except (ProgrammingError, OperationalError) as e:
        error_str = str(e).lower()
        if 'does not exist' in error_str or 'no such table' in error_str:
            filtered_count = 0
        else:
            raise
    
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
        'table_missing': False,
    }
    
    # Return partial template for AJAX requests
    if request.GET.get('ajax') == '1' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'dashboard/partials/gifted_courses_table.html', context)
    
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
def dashboard_teacher_create(request):
    """Create a new teacher account"""
    if request.method == 'POST':
        try:
            # Get form data
            username = request.POST.get('username', '').strip()
            email = request.POST.get('email', '').strip()
            password = request.POST.get('password', '').strip()
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            specialization = request.POST.get('specialization', '').strip()
            bio = request.POST.get('bio', '').strip()
            years_experience = request.POST.get('years_experience', '0').strip() or '0'
            permission_level = request.POST.get('permission_level', 'standard').strip()
            is_approved = request.POST.get('is_approved') == 'on'
            
            # Validation
            if not username:
                messages.error(request, 'Username is required.')
                return render(request, 'dashboard/teacher_create.html', {'form_data': request.POST})
            
            if not email:
                messages.error(request, 'Email is required.')
                return render(request, 'dashboard/teacher_create.html', {'form_data': request.POST})
            
            # Password is optional - will be auto-generated if not provided
            
            # Check if user already exists
            if User.objects.filter(username=username).exists():
                messages.error(request, f'Username "{username}" already exists.')
                return render(request, 'dashboard/teacher_create.html', {'form_data': request.POST})
            
            if User.objects.filter(email=email).exists():
                messages.error(request, f'Email "{email}" already exists.')
                return render(request, 'dashboard/teacher_create.html', {'form_data': request.POST})
            
            # Generate a secure temporary password if not provided
            # (User will set their own password via email link)
            import secrets
            import string
            if not password:
                alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
                password = ''.join(secrets.choice(alphabet) for i in range(16))
            
            # Create user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            
            # Update user profile role to instructor
            if hasattr(user, 'profile'):
                user.profile.role = 'instructor'
                user.profile.save()
            else:
                # Create profile if doesn't exist
                UserProfile.objects.create(user=user, role='instructor')
            
            # Create teacher profile (professional info will be filled on first login)
            teacher = Teacher.objects.create(
                user=user,
                specialization=specialization or '',  # Allow empty - will be filled on first login
                bio=bio or '',  # Allow empty - will be filled on first login
                years_experience=int(years_experience) if years_experience and years_experience.isdigit() else 0,
                permission_level=permission_level,
                is_approved=is_approved,
                approved_by=request.user if is_approved else None,
                approved_at=timezone.now() if is_approved else None
            )
            
            # Force password reset on first login
            if hasattr(user.profile, 'force_password_reset'):
                user.profile.force_password_reset = True
                user.profile.save()
            
            # Send welcome email with password reset link
            try:
                from myApp.email_utils import send_teacher_account_creation_email
                email_result = send_teacher_account_creation_email(user, teacher, request)
                if email_result == 1:
                    messages.success(request, f'Teacher account created successfully for {user.get_full_name() or username}. Welcome email sent to {user.email}.')
                else:
                    messages.warning(request, f'Teacher account created successfully, but email could not be sent to {user.email}. Please notify the teacher manually.')
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to send teacher account creation email: {e}", exc_info=True)
                messages.warning(request, f'Teacher account created successfully, but email could not be sent: {str(e)}. Please notify the teacher manually.')
            
            # Redirect back to teachers list instead of details page
            return redirect('dashboard:teachers')
            
        except Exception as e:
            messages.error(request, f'Error creating teacher account: {str(e)}')
            return render(request, 'dashboard/teacher_create.html', {'form_data': request.POST})
    
    # GET request - show form
    return render(request, 'dashboard/teacher_create.html')


@login_required
@role_required(['admin'])
def dashboard_teachers(request):
    """Teacher management"""
    teachers = Teacher.objects.select_related('user', 'approved_by').order_by('-created_at')
    
    # Get stats before filtering
    total_teachers = Teacher.objects.count()
    pending_count = Teacher.objects.filter(is_approved=False).count()
    approved_count = Teacher.objects.filter(is_approved=True).count()
    
    # Filters - support both 'q' and 'search' for consistency
    status = request.GET.get('status')
    search = request.GET.get('q') or request.GET.get('search')
    
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
    
    # Return partial template for AJAX requests
    if request.GET.get('ajax') == '1' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'dashboard/partials/teachers_table.html', context)
    
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
@require_POST
def dashboard_teachers_bulk_delete(request):
    """Bulk delete teachers - Admin can delete any teacher"""
    from django.http import JsonResponse
    from django.db import connection
    
    def safe_delete(queryset):
        """Safely delete queryset, handling missing tables"""
        try:
            if hasattr(queryset, 'delete'):
                return queryset.delete()[0]
            return 0
        except Exception as e:
            error_str = str(e).lower()
            if 'does not exist' in error_str or 'no such table' in error_str:
                return 0
            if 'transaction' in error_str or 'atomic' in error_str:
                connection.close()
                return 0
            return 0
    
    try:
        teacher_ids = request.POST.getlist('teacher_ids[]')
        if not teacher_ids:
            return JsonResponse({'success': False, 'error': 'No teachers selected'}, status=400)
        
        # Get teachers and associated users first
        teachers = Teacher.objects.filter(id__in=teacher_ids)
        count = teachers.count()
        
        if count == 0:
            return JsonResponse({'success': False, 'error': 'No teachers found'}, status=400)
        
        # Get associated user IDs before deleting
        user_ids = list(teachers.values_list('user_id', flat=True))
        teacher_id_list = [int(tid) for tid in teacher_ids]
        teacher_table = Teacher._meta.db_table
        
        # Delete related data first (course teachers, etc.)
        try:
            safe_delete(CourseTeacher.objects.filter(teacher__in=teachers))
        except:
            pass
        
        # Try to delete booking-related data if tables exist
        try:
            from .models import LiveClassBooking, BookingSeries, TeacherBookingPolicy, LiveClassSession, TeacherAvailability
            safe_delete(LiveClassBooking.objects.filter(teacher__in=teachers))
            safe_delete(BookingSeries.objects.filter(teacher__in=teachers))
            safe_delete(TeacherBookingPolicy.objects.filter(teacher__in=teachers))
            # Set teacher to NULL for live class sessions (they use SET_NULL)
            try:
                LiveClassSession.objects.filter(teacher__in=teachers).update(teacher=None)
            except:
                pass
            try:
                TeacherAvailability.objects.filter(teacher__in=teachers).delete()
            except:
                pass
        except:
            pass
        
        # STEP 1: Delete Teachers FIRST (removes foreign key constraint on User)
        deleted_count = 0
        try:
            with connection.cursor() as cursor:
                quoted_table = connection.ops.quote_name(teacher_table)
                if 'postgresql' in connection.vendor:
                    cursor.execute(
                        f"DELETE FROM {quoted_table} WHERE id = ANY(%s)",
                        [teacher_id_list]
                    )
                else:
                    placeholders = ','.join(['%s'] * len(teacher_id_list))
                    cursor.execute(
                        f"DELETE FROM {teacher_table} WHERE id IN ({placeholders})",
                        teacher_id_list
                    )
                deleted_count = cursor.rowcount if hasattr(cursor, 'rowcount') and cursor.rowcount else len(teacher_id_list)
                print(f"Deleted {deleted_count} Teacher records")
        except Exception as teacher_delete_error:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Teacher deletion failed: {teacher_delete_error}")
            # Try ORM deletion as fallback
            try:
                teachers.delete()
                deleted_count = len(teacher_id_list)
                print(f"Deleted {deleted_count} Teacher records via ORM")
            except Exception as orm_error:
                logger.error(f"Teacher ORM deletion also failed: {orm_error}")
        
        # STEP 2: Delete UserProfiles (must be deleted before Users)
        # Teacher has OneToOne with User (CASCADE), so deleting User deletes Teacher
        try:
            # Get users that are teachers (not admins/superusers)
            users_to_delete = User.objects.filter(
                id__in=user_ids
            ).exclude(
                Q(is_superuser=True) | Q(is_staff=True) | Q(profile__role='admin')
            )
            
            user_id_list = list(users_to_delete.values_list('id', flat=True))
            if user_id_list:
                # CRITICAL: Delete UserProfiles FIRST (foreign key constraint)
                # UserProfile has OneToOne with User, so we must delete it before User
                try:
                    from .models import UserProfile
                    # Get the actual table name (handle case sensitivity)
                    userprofile_table = UserProfile._meta.db_table
                    # Use proper quoting for PostgreSQL
                    quoted_table = connection.ops.quote_name(userprofile_table)
                    
                    with connection.cursor() as cursor:
                        if 'postgresql' in connection.vendor:
                            cursor.execute(
                                f"DELETE FROM {quoted_table} WHERE user_id = ANY(%s)",
                                [user_id_list]
                            )
                        else:
                            placeholders = ','.join(['%s'] * len(user_id_list))
                            cursor.execute(
                                f"DELETE FROM {userprofile_table} WHERE user_id IN ({placeholders})",
                                user_id_list
                            )
                    userprofile_deleted = cursor.rowcount if hasattr(cursor, 'rowcount') and cursor.rowcount else 0
                    print(f"Deleted {userprofile_deleted} UserProfile records")
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"UserProfile deletion error: {e}", exc_info=True)
                    # Try using ORM instead
                    try:
                        from .models import UserProfile
                        UserProfile.objects.filter(user_id__in=user_id_list).delete()
                        print("Deleted UserProfile records via ORM")
                    except Exception as e2:
                        logger.error(f"UserProfile ORM deletion also failed: {e2}")
                        # Continue anyway - might fail at User deletion
                
                # STEP 3: Now delete Users (Teachers already deleted, so no constraint violation)
                try:
                    with connection.cursor() as cursor:
                        if 'postgresql' in connection.vendor:
                            cursor.execute(
                                "DELETE FROM auth_user WHERE id = ANY(%s)",
                                [user_id_list]
                            )
                        else:
                            placeholders = ','.join(['%s'] * len(user_id_list))
                            cursor.execute(
                                f"DELETE FROM auth_user WHERE id IN ({placeholders})",
                                user_id_list
                            )
                    users_deleted = cursor.rowcount if hasattr(cursor, 'rowcount') and cursor.rowcount else len(user_id_list)
                    print(f"Deleted {users_deleted} User records")
                except Exception as user_error:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"User deletion failed: {user_error}")
                    # Try ORM as fallback (might fail if SecurityActionLog doesn't exist)
                    try:
                        # Delete one by one to handle missing tables gracefully
                        for user_id in user_id_list:
                            try:
                                User.objects.filter(id=user_id).delete()
                            except Exception:
                                # If ORM fails (e.g., missing SecurityActionLog table), use raw SQL
                                try:
                                    with connection.cursor() as cursor:
                                        cursor.execute("DELETE FROM auth_user WHERE id = %s", [user_id])
                                except:
                                    pass
                        print(f"Deleted {len(user_id_list)} User records")
                    except Exception as fallback_error:
                        logger.error(f"User deletion fallback also failed: {fallback_error}")
                
                # Verify all deletions succeeded
                remaining_teachers = Teacher.objects.filter(id__in=teacher_id_list).count()
                remaining_users = User.objects.filter(id__in=user_id_list).count()
                if remaining_teachers == 0 and remaining_users == 0:
                    # Success! All deletions completed
                    connection.close()
                    return JsonResponse({
                        'success': True,
                        'deleted': deleted_count,
                        'message': f'Successfully deleted {deleted_count} teacher(s)'
                    })
        except Exception as user_delete_error:
            # If user deletion fails, log it but continue
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"User deletion failed: {user_delete_error}", exc_info=True)
            print(f"User deletion failed: {user_delete_error}")
        
        # If user deletion didn't work or teachers still exist, try deleting teachers directly
        remaining_before = Teacher.objects.filter(id__in=teacher_id_list).count()
        if remaining_before > 0:
            try:
                with connection.cursor() as cursor:
                    if 'postgresql' in connection.vendor:
                        cursor.execute(
                            f"DELETE FROM {teacher_table} WHERE id = ANY(%s)",
                            [teacher_id_list]
                        )
                    else:
                        placeholders = ','.join(['?' if 'sqlite' in connection.vendor.lower() else '%s'] * len(teacher_id_list))
                        cursor.execute(
                            f"DELETE FROM {teacher_table} WHERE id IN ({placeholders})",
                            teacher_id_list
                        )
                deleted_count = cursor.rowcount if hasattr(cursor, 'rowcount') and cursor.rowcount > 0 else 0
                
                # Verify deletion worked
                remaining = Teacher.objects.filter(id__in=teacher_id_list).count()
                if remaining > 0:
                    # If some weren't deleted, try one by one
                    for teacher_id in teacher_id_list:
                        if Teacher.objects.filter(id=teacher_id).exists():
                            try:
                                with connection.cursor() as cursor:
                                    if 'postgresql' in connection.vendor:
                                        cursor.execute(f"DELETE FROM {teacher_table} WHERE id = %s", [teacher_id])
                                    else:
                                        cursor.execute(f"DELETE FROM {teacher_table} WHERE id = ?", [teacher_id])
                                if cursor.rowcount > 0:
                                    deleted_count += 1
                            except Exception as e3:
                                # Last resort: try ORM deletion
                                try:
                                    Teacher.objects.filter(id=teacher_id).delete()
                                    deleted_count += 1
                                except:
                                    pass
            except Exception as e:
                # Fallback: try one by one
                for teacher_id in teacher_id_list:
                    try:
                        # Try raw SQL first
                        with connection.cursor() as cursor:
                            if 'postgresql' in connection.vendor:
                                cursor.execute(f"DELETE FROM {teacher_table} WHERE id = %s", [teacher_id])
                            else:
                                cursor.execute(f"DELETE FROM {teacher_table} WHERE id = ?", [teacher_id])
                        if cursor.rowcount > 0:
                            deleted_count += 1
                    except Exception as e2:
                        # Last resort: try ORM deletion
                        try:
                            Teacher.objects.filter(id=teacher_id).delete()
                            deleted_count += 1
                        except:
                            pass
        
        # Note: Users are deleted above (before teachers), which should cascade delete teachers
        # This section is kept for backwards compatibility but shouldn't run if deletion worked above
        
        # Refresh connection to ensure we see latest data
        connection.close()
        
        # Final verification: check how many teachers were actually deleted
        final_count = Teacher.objects.filter(id__in=teacher_id_list).count()
        
        # If all teachers were deleted via user cascade, return success early
        if final_count == 0:
            return JsonResponse({
                'success': True,
                'deleted': len(teacher_id_list),
                'message': f'Successfully deleted {len(teacher_id_list)} teacher(s)'
            })
        if final_count > 0:
            # Some teachers still exist - deletion partially failed
            # Try one more time with ORM to see if it works
            try:
                remaining_teachers = Teacher.objects.filter(id__in=teacher_id_list)
                remaining_count = remaining_teachers.count()
                if remaining_count > 0:
                    # Force delete using ORM
                    for teacher in remaining_teachers:
                        try:
                            teacher.delete()
                            deleted_count += 1
                        except:
                            pass
                    
                    # Check again
                    final_count = Teacher.objects.filter(id__in=teacher_id_list).count()
                    if final_count > 0:
                        return JsonResponse({
                            'success': False, 
                            'error': f'Failed to delete all teachers. {final_count} teacher(s) still exist. Please check database constraints.',
                            'deleted': deleted_count,
                            'remaining': final_count
                        }, status=500)
            except Exception as verify_error:
                return JsonResponse({
                    'success': False, 
                    'error': f'Deletion completed but verification failed: {str(verify_error)}',
                    'deleted': deleted_count,
                    'remaining': final_count
                }, status=500)
        
        return JsonResponse({
            'success': True, 
            'deleted': deleted_count, 
            'message': f'Successfully deleted {deleted_count} teacher(s)'
        })
    except Exception as e:
        import traceback
        error_msg = str(e)
        if 'transaction' in error_msg.lower() or 'atomic' in error_msg.lower():
            connection.close()
        return JsonResponse({'success': False, 'error': error_msg}, status=500)


@login_required
@role_required(['admin'])
@require_POST
def dashboard_students_bulk_delete(request):
    """Bulk delete students - Admin can delete any student"""
    from django.http import JsonResponse
    from django.db import connection
    
    def safe_delete(queryset):
        """Safely delete queryset, handling missing tables"""
        try:
            if hasattr(queryset, 'delete'):
                return queryset.delete()[0]
            return 0
        except Exception as e:
            error_str = str(e).lower()
            if 'does not exist' in error_str or 'no such table' in error_str:
                return 0
            if 'transaction' in error_str or 'atomic' in error_str:
                connection.close()
                return 0
            return 0
    
    try:
        user_ids = request.POST.getlist('user_ids[]')
        if not user_ids:
            return JsonResponse({'success': False, 'error': 'No students selected'}, status=400)
        
        # Convert to integers
        user_ids = [int(uid) for uid in user_ids if uid]
        
        # Get students - be more lenient with filtering
        # First get all users with those IDs (excluding superusers/staff)
        all_users = User.objects.filter(id__in=user_ids).exclude(
            Q(is_superuser=True) | Q(is_staff=True)
        )
        
        # Filter to only students by checking profile role
        student_user_ids = []
        for user in all_users:
            try:
                # Try to get profile
                profile = getattr(user, 'profile', None)
                if profile is None:
                    # No profile exists - try to access it to see if it exists
                    try:
                        profile = user.profile
                    except:
                        profile = None
                
                # If no profile or profile role is student, include them
                if profile is None:
                    # No profile - assume student if not admin
                    student_user_ids.append(user.id)
                elif profile.role == 'student':
                    student_user_ids.append(user.id)
            except Exception as e:
                # If any error accessing profile, include user if not admin
                if not user.is_superuser and not user.is_staff:
                    student_user_ids.append(user.id)
        
        count = len(student_user_ids)
        
        if count == 0:
            # Debug: check what users were sent
            all_user_count = all_users.count()
            return JsonResponse({
                'success': False, 
                'error': f'No students found to delete. Found {all_user_count} user(s) with those IDs, but none are students. User IDs sent: {user_ids}'
            }, status=400)
        
        # Delete ALL related data first, in correct order
        # 1. Delete data that depends on enrollments
        try:
            enrollments = Enrollment.objects.filter(user_id__in=student_user_ids)
            enrollment_ids = list(enrollments.values_list('id', flat=True))
            if enrollment_ids:
                safe_delete(LessonProgress.objects.filter(enrollment_id__in=enrollment_ids))
            safe_delete(enrollments)
        except Exception:
            pass
        
        # 2. Delete quiz attempts, certificates, placement tests
        try:
            safe_delete(QuizAttempt.objects.filter(user_id__in=student_user_ids))
            safe_delete(Certificate.objects.filter(user_id__in=student_user_ids))
            safe_delete(PlacementTest.objects.filter(user_id__in=student_user_ids))
        except Exception:
            pass
        
        # 3. Delete tutor conversations and messages
        try:
            from .models import TutorConversation, TutorMessage
            conversations = TutorConversation.objects.filter(user_id__in=student_user_ids)
            conv_ids = list(conversations.values_list('id', flat=True))
            if conv_ids:
                safe_delete(TutorMessage.objects.filter(conversation_id__in=conv_ids))
            safe_delete(conversations)
        except Exception:
            pass
        
        # 4. Delete payments and gifts
        try:
            safe_delete(Payment.objects.filter(user_id__in=student_user_ids))
            safe_delete(GiftEnrollment.objects.filter(buyer_id__in=student_user_ids))
        except Exception:
            pass
        
        # 5. Delete activity logs and security logs
        try:
            safe_delete(ActivityLog.objects.filter(actor_id__in=student_user_ids))
            safe_delete(SecurityActionLog.objects.filter(target_user_id__in=student_user_ids))
            safe_delete(SecurityActionLog.objects.filter(admin_user_id__in=student_user_ids))
        except Exception:
            pass
        
        # 6. Delete booking-related data
        try:
            from .models import LiveClassBooking, BookingSeries
            safe_delete(LiveClassBooking.objects.filter(student_user_id__in=student_user_ids))
            safe_delete(BookingSeries.objects.filter(student_user_id__in=student_user_ids))
        except Exception:
            pass
        
        try:
            from .models import Booking, OneOnOneBooking
            safe_delete(Booking.objects.filter(user_id__in=student_user_ids))
            safe_delete(OneOnOneBooking.objects.filter(user_id__in=student_user_ids))
        except Exception:
            pass
        
        # 7. Delete user profiles LAST before users (OneToOne with CASCADE)
        # Use raw SQL to ensure it happens
        try:
            profile_table = UserProfile._meta.db_table
            with connection.cursor() as cursor:
                if 'postgresql' in connection.vendor:
                    cursor.execute(
                        f"DELETE FROM {profile_table} WHERE user_id = ANY(%s)",
                        [student_user_ids]
                    )
                else:
                    placeholders = ','.join(['%s'] * len(student_user_ids))
                    cursor.execute(
                        f"DELETE FROM {profile_table} WHERE user_id IN ({placeholders})",
                        student_user_ids
                    )
        except Exception as e:
            # If raw SQL fails, try ORM
            try:
                UserProfile.objects.filter(user_id__in=student_user_ids).delete()
            except Exception:
                pass
        
        # Try to delete booking-related data if tables exist
        try:
            from .models import LiveClassBooking, BookingSeries
            safe_delete(LiveClassBooking.objects.filter(student_user_id__in=student_user_ids))
            safe_delete(BookingSeries.objects.filter(student_user_id__in=student_user_ids))
        except Exception:
            pass
        
        # Try Booking and OneOnOneBooking models
        try:
            from .models import Booking, OneOnOneBooking
            safe_delete(Booking.objects.filter(user_id__in=student_user_ids))
            safe_delete(OneOnOneBooking.objects.filter(user_id__in=student_user_ids))
        except Exception:
            pass
        
        # Delete users using raw SQL to avoid ORM relationship checks
        # Get the actual table name from User model
        user_table = User._meta.db_table
        deleted_count = 0
        error_details = []
        
        try:
            user_id_list = [int(uid) for uid in student_user_ids]
            
            # First, verify users exist before deletion
            existing_count = User.objects.filter(id__in=user_id_list).count()
            
            if existing_count == 0:
                return JsonResponse({
                    'success': False, 
                    'error': f'No users found with IDs: {user_id_list}'
                }, status=400)
            
            # Delete using raw SQL
            with connection.cursor() as cursor:
                if 'postgresql' in connection.vendor:
                    cursor.execute(
                        f"DELETE FROM {user_table} WHERE id = ANY(%s)",
                        [user_id_list]
                    )
                else:
                    placeholders = ','.join(['%s'] * len(user_id_list))
                    cursor.execute(
                        f"DELETE FROM {user_table} WHERE id IN ({placeholders})",
                        user_id_list
                    )
            
            # Verify deletion by checking remaining users
            remaining = User.objects.filter(id__in=user_id_list).count()
            deleted_count = existing_count - remaining
            
            # If still 0, try individual deletions
            if deleted_count == 0:
                # Try deleting one by one with raw SQL
                for user_id in user_id_list:
                    try:
                        with connection.cursor() as cursor:
                            if 'postgresql' in connection.vendor:
                                cursor.execute(f"DELETE FROM {user_table} WHERE id = %s", [user_id])
                            else:
                                cursor.execute(f"DELETE FROM {user_table} WHERE id = ?", [user_id])
                        # Check if user still exists
                        if not User.objects.filter(id=user_id).exists():
                            deleted_count += 1
                    except Exception as e3:
                        error_details.append(f"User {user_id}: {str(e3)[:50]}")
                        pass
                        
        except Exception as e:
            error_details.append(f"Bulk delete error: {str(e)[:100]}")
            # Fallback: try one by one
            for user_id in student_user_ids:
                try:
                    # Close connection to reset state
                    connection.close()
                    # Try raw SQL for individual user
                    user_table = User._meta.db_table
                    with connection.cursor() as cursor:
                        if 'postgresql' in connection.vendor:
                            cursor.execute(f"DELETE FROM {user_table} WHERE id = %s", [user_id])
                        else:
                            cursor.execute(f"DELETE FROM {user_table} WHERE id = ?", [user_id])
                    # Verify deletion
                    if not User.objects.filter(id=user_id).exists():
                        deleted_count += 1
                except Exception as e2:
                    error_str = str(e2).lower()
                    error_details.append(f"User {user_id}: {str(e2)[:50]}")
                    pass
        
        if deleted_count == 0:
            error_msg = 'Failed to delete students. No students were deleted.'
            if error_details:
                error_msg += f' Errors: {"; ".join(error_details[:3])}'
            return JsonResponse({
                'success': False, 
                'error': error_msg
            }, status=500)
        
        return JsonResponse({
            'success': True, 
            'deleted': deleted_count, 
            'message': f'Successfully deleted {deleted_count} student(s)'
        })
    except Exception as e:
        import traceback
        error_msg = str(e)
        if 'transaction' in error_msg.lower() or 'atomic' in error_msg.lower():
            connection.close()
        return JsonResponse({'success': False, 'error': error_msg}, status=500)


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
        from django.urls import reverse
        reset_url = request.build_absolute_uri(
            reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
        )
        
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
    from django.db import IntegrityError
    from django.contrib.auth.models import User
    
    # Strict guard: Ensure user is authenticated
    if not request.user.is_authenticated:
        if request.content_type == 'application/json':
            return JsonResponse({'error': 'Authentication required'}, status=401)
        messages.error(request, 'You must be logged in.')
        return redirect('dashboard:teachers')
    
    # Get teacher and validate it exists and has a valid user
    try:
        teacher = Teacher.objects.select_related('user').get(id=teacher_id)
    except Teacher.DoesNotExist:
        if request.content_type == 'application/json':
            return JsonResponse({'error': 'Teacher not found'}, status=404)
        messages.error(request, 'Teacher not found.')
        return redirect('dashboard:teachers')
    
    # Strict guard: Verify teacher.user points to a valid User
    if not teacher.user:
        if request.content_type == 'application/json':
            return JsonResponse({'error': 'Teacher profile is not linked to a user account'}, status=400)
        messages.error(request, 'Teacher profile is not properly linked to a user account.')
        return redirect('dashboard:teachers')
    
    # Verify the user exists
    try:
        teacher_user = User.objects.get(pk=teacher.user.pk)
    except User.DoesNotExist:
        if request.content_type == 'application/json':
            return JsonResponse({'error': 'Teacher user account not found'}, status=400)
        messages.error(request, 'Teacher user account not found.')
        return redirect('dashboard:teachers')
    
    data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
    
    course_id = data.get('course_id')
    permission_level = data.get('permission_level', 'view_only')
    can_create_live_classes = data.get('can_create_live_classes', 'false') == 'true'
    can_manage_schedule = data.get('can_manage_schedule', 'false') == 'true'
    
    if not course_id:
        if request.content_type == 'application/json':
            return JsonResponse({'error': 'Course ID is required'}, status=400)
        messages.error(request, 'Course ID is required.')
        return redirect('dashboard:teachers')
    
    try:
        course = Course.objects.get(id=course_id)
    except Course.DoesNotExist:
        if request.content_type == 'application/json':
            return JsonResponse({'error': 'Course not found'}, status=404)
        messages.error(request, 'Course not found.')
        return redirect('dashboard:teachers')
    
    # Check if already assigned - use get_or_create to prevent duplicates
    try:
        assignment, created = CourseTeacher.objects.get_or_create(
            course=course,
            teacher=teacher_user,  # Use teacher.user, not Teacher instance
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
            assignment.assigned_by = request.user
            assignment.save()
            if request.content_type == 'application/json':
                return JsonResponse({'success': True, 'message': 'Assignment updated'})
            messages.info(request, 'Assignment updated.')
        else:
            if request.content_type == 'application/json':
                return JsonResponse({'success': True, 'message': f'Course "{course.title}" assigned to {teacher.user.username}!'})
            messages.success(request, f'Course "{course.title}" assigned to {teacher.user.username}!')
    
    except IntegrityError as e:
        error_msg = str(e)
        if 'teacher_id' in error_msg.lower() or 'foreign key' in error_msg.lower():
            error_message = 'Error linking teacher to course. The teacher profile may be invalid.'
        else:
            error_message = f'Database error: {error_msg}'
        
        if request.content_type == 'application/json':
            return JsonResponse({'error': error_message}, status=400)
        messages.error(request, error_message)
        return redirect('dashboard:teachers')
    except Exception as e:
        error_message = f'Error assigning course: {str(e)}'
        if request.content_type == 'application/json':
            return JsonResponse({'error': error_message}, status=500)
        messages.error(request, error_message)
        return redirect('dashboard:teachers')
    
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
        from django.utils.text import slugify
        
        # Get title and generate slug if not provided
        title = request.POST.get('title', '').strip()
        if not title:
            messages.error(request, 'Course title is required.')
            categories = Category.objects.all()
            instructors = User.objects.filter(profile__role='instructor').order_by('username')
            context = {
                'categories': categories,
                'instructors': instructors,
            }
            return render(request, 'dashboard/course_create.html', context)
        
        # Generate slug from title if not provided
        # The save() method will ensure uniqueness automatically
        slug = request.POST.get('slug', '').strip()
        if not slug:
            slug = slugify(title)
        
        # Create course - save() method will ensure slug is unique
        course = Course.objects.create(
            title=title,
            slug=slug,
            description=request.POST.get('description', ''),
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


# ============================================
# INFOBIP INTEGRATION
# ============================================

@login_required
@role_required(['admin'])
def dashboard_infobip_sync(request):
    """Infobip sync management page"""
    from myApp.utils.infobip_service import InfobipService
    from django.conf import settings
    import subprocess
    from django.core.cache import cache
    
    infobip = InfobipService()
    
    # Test connection
    connection_status = infobip.test_connection()
    
    # Get sync statistics
    total_leads_with_infobip = Lead.objects.exclude(infobip_profile_id__isnull=True).exclude(infobip_profile_id='').count()
    recently_synced = Lead.objects.filter(
        infobip_last_synced_at__gte=timezone.now() - timedelta(days=1)
    ).count()
    
    # Get last sync info from cache or database
    last_sync_info = cache.get('infobip_last_sync_info', {})
    if not last_sync_info:
        # Try to get from most recently synced lead
        last_synced_lead = Lead.objects.exclude(infobip_last_synced_at__isnull=True).order_by('-infobip_last_synced_at').first()
        if last_synced_lead:
            last_sync_info = {
                'timestamp': last_synced_lead.infobip_last_synced_at,
                'leads_updated': 0,
                'leads_created': 0,
            }
    
    # Handle manual sync trigger
    sync_result = None
    if request.method == 'POST' and 'sync_now' in request.POST:
        days = int(request.POST.get('days', 30))
        create_new = 'create_new' in request.POST
        
        try:
            # Run sync command
            cmd = ['python', 'manage.py', 'sync_infobip_contacts', '--days', str(days), '--limit', '100']
            if create_new:
                cmd.append('--create-new')
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                cwd=settings.BASE_DIR
            )
            
            sync_result = {
                'success': result.returncode == 0,
                'output': result.stdout,
                'error': result.stderr if result.returncode != 0 else None
            }
            
            if sync_result['success']:
                messages.success(request, 'Infobip sync completed successfully!')
                # Update cache
                cache.set('infobip_last_sync_info', {
                    'timestamp': timezone.now(),
                    'leads_updated': 0,  # Would need to parse output for actual numbers
                    'leads_created': 0,
                }, 3600)  # Cache for 1 hour
            else:
                messages.error(request, f"Sync failed: {sync_result.get('error', 'Unknown error')}")
                
        except subprocess.TimeoutExpired:
            sync_result = {
                'success': False,
                'error': 'Sync timed out after 5 minutes'
            }
            messages.error(request, 'Sync timed out. Please try again or run manually.')
        except Exception as e:
            sync_result = {
                'success': False,
                'error': str(e)
            }
            messages.error(request, f'Sync error: {str(e)}')
    
    context = {
        'connection_status': connection_status,
        'total_leads_with_infobip': total_leads_with_infobip,
        'recently_synced': recently_synced,
        'last_sync_info': last_sync_info,
        'sync_result': sync_result,
        'infobip_configured': bool(getattr(settings, 'INFOBIP_API_KEY', '')),
        'sync_channels': getattr(settings, 'INFOBIP_SYNC_CHANNELS', []),
    }
    
    return render(request, 'dashboard/infobip_sync.html', context)


@login_required
@role_required(['admin'])
@require_POST
def dashboard_infobip_test_connection(request):
    """Test Infobip API connection via AJAX"""
    from myApp.utils.infobip_service import InfobipService
    
    infobip = InfobipService()
    test_type = request.POST.get('test_type', 'basic')
    
    if test_type == 'whatsapp':
        result = infobip.check_whatsapp_connection()
    else:
        result = infobip.test_connection()
    
    return JsonResponse(result)


# ============================================
# CERTIFICATES MANAGEMENT
# ============================================

@login_required
@role_required(['admin'])
def dashboard_certificates(request):
    """Admin dashboard for managing certificates"""
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    
    certificates = Certificate.objects.select_related('user', 'course').order_by('-issued_at')
    
    # Filters - support both 'q' and 'search' for consistency
    search = request.GET.get('q') or request.GET.get('search')
    course_filter = request.GET.get('course')
    verified_filter = request.GET.get('verified')
    
    if search:
        certificates = certificates.filter(
            Q(certificate_id__icontains=search) |
            Q(user__username__icontains=search) |
            Q(user__email__icontains=search) |
            Q(course__title__icontains=search)
        )
    
    if course_filter:
        certificates = certificates.filter(course_id=course_filter)
    
    if verified_filter:
        if verified_filter == 'yes':
            certificates = certificates.filter(is_verified=True)
        elif verified_filter == 'no':
            certificates = certificates.filter(is_verified=False)
    
    # Pagination
    paginator = Paginator(certificates, 20)
    page = request.GET.get('page', 1)
    try:
        certificates_page = paginator.get_page(page)
    except PageNotAnInteger:
        certificates_page = paginator.get_page(1)
    except EmptyPage:
        certificates_page = paginator.get_page(paginator.num_pages)
    
    # Get courses for filter dropdown
    courses = Course.objects.all().order_by('title')
    
    context = {
        'certificates': certificates_page,
        'courses': courses,
        'search_query': search,
        'course_filter': course_filter,
        'verified_filter': verified_filter,
        'total_count': certificates.count(),
    }
    
    # Return partial template for AJAX requests
    if request.GET.get('ajax') == '1' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'dashboard/partials/certificates_table.html', context)
    
    return render(request, 'dashboard/certificates.html', context)


@login_required
@role_required(['admin'])
def dashboard_certificate_preview(request, certificate_id):
    """Preview how a certificate looks"""
    certificate = get_object_or_404(Certificate, certificate_id=certificate_id)
    
    # Generate QR code if it doesn't exist
    if not certificate.qr_code:
        certificate.generate_qr_code(request.build_absolute_uri('/')[:-1])
    
    context = {
        'certificate': certificate,
        'preview_mode': True,
    }
    return render(request, 'dashboard/certificate_preview.html', context)


# ============================================
# COURSE CONTENT MANAGEMENT API (Modules, Lessons, Quizzes)
# ============================================

@login_required
@role_required(['admin'])
def dashboard_api_modules(request, course_id):
    """Get all modules for a course"""
    course = get_object_or_404(Course, id=course_id)
    
    # Check if content column exists by trying to defer it
    content_column_exists = True
    try:
        # Try to query with defer to see if column exists
        test_lesson = Lesson.objects.defer('content').first()
        if test_lesson is None:
            # No lessons exist, but column might exist
            from django.db import connection
            if 'postgresql' in connection.vendor:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT column_name FROM information_schema.columns 
                        WHERE table_name = 'myApp_lesson' AND column_name = 'content'
                    """)
                    content_column_exists = cursor.fetchone() is not None
            else:
                # SQLite
                with connection.cursor() as cursor:
                    cursor.execute("PRAGMA table_info(myApp_lesson)")
                    columns = [row[1] for row in cursor.fetchall()]
                    content_column_exists = 'content' in columns
    except Exception:
        content_column_exists = False
    
    # Get modules
    modules = course.modules.all().order_by('order')
    
    modules_data = []
    for module in modules:
        lessons_data = []
        # Get lessons, deferring content if column doesn't exist
        try:
            if content_column_exists:
                lessons_queryset = module.lessons.all().order_by('order')
            else:
                # Use only() to select specific columns, avoiding content
                lessons_queryset = module.lessons.all().only(
                    'id', 'title', 'content_type', 'order', 'estimated_minutes', 'is_preview'
                ).order_by('order')
        except Exception as e:
            # Fallback: use raw SQL if ORM fails
            if 'content' in str(e).lower():
                from django.db import connection
                with connection.cursor() as cursor:
                    table_name = Lesson._meta.db_table
                    cursor.execute(f"""
                        SELECT id, title, content_type, "order", estimated_minutes, is_preview
                        FROM {table_name}
                        WHERE module_id = %s
                        ORDER BY "order"
                    """, [module.id])
                    lessons_queryset = []
                    for row in cursor.fetchall():
                        class LessonObj:
                            def __init__(self, id, title, content_type, order, estimated_minutes, is_preview):
                                self.id = id
                                self.title = title
                                self.content_type = content_type
                                self.order = order
                                self.estimated_minutes = estimated_minutes
                                self.is_preview = is_preview
                        lessons_queryset.append(LessonObj(*row))
            else:
                raise
        
        for lesson in lessons_queryset:
            lessons_data.append({
                'id': lesson.id,
                'title': lesson.title,
                'content_type': lesson.content_type,
                'order': lesson.order,
                'estimated_minutes': lesson.estimated_minutes,
                'is_preview': lesson.is_preview,
            })
        
        modules_data.append({
            'id': module.id,
            'title': module.title,
            'description': module.description,
            'order': module.order,
            'is_locked': module.is_locked,
            'lessons': lessons_data,
            'lessons_count': len(lessons_data),
        })
    
    return JsonResponse({'success': True, 'modules': modules_data})


@login_required
@role_required(['admin'])
@require_POST
def dashboard_api_module_create(request, course_id):
    """Create a new module"""
    course = get_object_or_404(Course, id=course_id)
    
    try:
        import json
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
        
        title = data.get('title', '').strip()
        if not title:
            return JsonResponse({'success': False, 'error': 'Module title is required'}, status=400)
        
        # Get the highest order number
        max_order = course.modules.aggregate(Max('order'))['order__max'] or 0
        
        module = Module.objects.create(
            course=course,
            title=title,
            description=data.get('description', ''),
            order=max_order + 1,
            is_locked=data.get('is_locked', False) == True or data.get('is_locked') == 'true',
        )
        
        return JsonResponse({
            'success': True,
            'module': {
                'id': module.id,
                'title': module.title,
                'description': module.description,
                'order': module.order,
                'is_locked': module.is_locked,
                'lessons': [],
                'lessons_count': 0,
            }
        })
    except Exception as e:
        import traceback
        return JsonResponse({'success': False, 'error': str(e), 'traceback': traceback.format_exc()}, status=500)


@login_required
@role_required(['admin'])
def dashboard_api_module_update(request, module_id):
    """Update a module (or get module data if GET request)"""
    module = get_object_or_404(Module, id=module_id)
    
    if request.method == 'GET':
        return JsonResponse({
            'success': True,
            'module': {
                'id': module.id,
                'title': module.title,
                'description': module.description,
                'order': module.order,
                'is_locked': module.is_locked,
            }
        })
    
    try:
        import json
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
        
        # Check if this is a GET request via POST (for compatibility)
        if data.get('get') == True or data.get('get') == 'true':
            return JsonResponse({
                'success': True,
                'module': {
                    'id': module.id,
                    'title': module.title,
                    'description': module.description,
                    'order': module.order,
                    'is_locked': module.is_locked,
                }
            })
        
        if 'title' in data:
            module.title = data['title'].strip()
        if 'description' in data:
            module.description = data.get('description', '')
        if 'order' in data:
            module.order = int(data['order'])
        if 'is_locked' in data:
            module.is_locked = data['is_locked'] == True or data['is_locked'] == 'true'
        
        module.save()
        
        return JsonResponse({
            'success': True,
            'module': {
                'id': module.id,
                'title': module.title,
                'description': module.description,
                'order': module.order,
                'is_locked': module.is_locked,
            }
        })
    except Exception as e:
        import traceback
        return JsonResponse({'success': False, 'error': str(e), 'traceback': traceback.format_exc()}, status=500)


@login_required
@role_required(['admin'])
@require_POST
def dashboard_api_module_delete(request, module_id):
    """Delete a module"""
    module = get_object_or_404(Module, id=module_id)
    
    try:
        module_id_val = module.id
        module.delete()
        return JsonResponse({'success': True, 'message': 'Module deleted successfully'})
    except Exception as e:
        import traceback
        return JsonResponse({'success': False, 'error': str(e), 'traceback': traceback.format_exc()}, status=500)


@login_required
@role_required(['admin'])
def dashboard_api_lessons(request, module_id):
    """Get all lessons for a module"""
    module = get_object_or_404(Module, id=module_id)
    lessons = module.lessons.all().order_by('order')
    
    lessons_data = []
    for lesson in lessons:
        lessons_data.append({
            'id': lesson.id,
            'title': lesson.title,
            'description': lesson.description,
            'content_type': lesson.content_type,
            'video_url': lesson.video_url,
            'video_duration': lesson.video_duration,
            'text_content': lesson.text_content,
            'order': lesson.order,
            'estimated_minutes': lesson.estimated_minutes,
            'is_preview': lesson.is_preview,
            'is_milestone': lesson.is_milestone,
        })
    
    return JsonResponse({'success': True, 'lessons': lessons_data})


@login_required
@role_required(['admin'])
@require_POST
def dashboard_api_lesson_create(request, module_id):
    """Create a new lesson"""
    module = get_object_or_404(Module, id=module_id)
    
    try:
        import json
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
        
        title = data.get('title', '').strip()
        if not title:
            return JsonResponse({'success': False, 'error': 'Lesson title is required'}, status=400)
        
        # Get the highest order number
        max_order = module.lessons.aggregate(Max('order'))['order__max'] or 0
        
        # Handle Editor.js content
        content_data = {}
        if 'content' in data:
            try:
                content_data = data.get('content', {})
                if isinstance(content_data, str):
                    content_data = json.loads(content_data)
            except (json.JSONDecodeError, TypeError):
                content_data = {}
        
        lesson = Lesson.objects.create(
            module=module,
            title=title,
            description=data.get('description', ''),
            content_type=data.get('content_type', 'video'),
            video_url=data.get('video_url', ''),
            video_duration=int(data.get('video_duration', 0) or 0),
            text_content=data.get('text_content', ''),
            content=content_data,
            order=max_order + 1,
            estimated_minutes=int(data.get('estimated_minutes', 10) or 10),
            is_preview=data.get('is_preview', False) == True or data.get('is_preview') == 'true',
            is_milestone=data.get('is_milestone', False) == True or data.get('is_milestone') == 'true',
        )
        
        return JsonResponse({
            'success': True,
            'lesson': {
                'id': lesson.id,
                'title': lesson.title,
                'description': lesson.description,
                'content_type': lesson.content_type,
                'video_url': lesson.video_url,
                'video_duration': lesson.video_duration,
                'text_content': lesson.text_content,
                'content': lesson.content if hasattr(lesson, 'content') else {},
                'order': lesson.order,
                'estimated_minutes': lesson.estimated_minutes,
                'is_preview': lesson.is_preview,
                'is_milestone': lesson.is_milestone,
            }
        })
    except Exception as e:
        import traceback
        return JsonResponse({'success': False, 'error': str(e), 'traceback': traceback.format_exc()}, status=500)


@login_required
@role_required(['admin'])
def dashboard_api_lesson_update(request, lesson_id):
    """Update a lesson (or get lesson data if GET request)"""
    lesson = get_object_or_404(Lesson, id=lesson_id)
    
    if request.method == 'GET':
        return JsonResponse({
            'success': True,
            'lesson': {
                'id': lesson.id,
                'title': lesson.title,
                'description': lesson.description,
                'content_type': lesson.content_type,
                'video_url': lesson.video_url,
                'video_duration': lesson.video_duration,
                'text_content': lesson.text_content,
                'content': lesson.content if hasattr(lesson, 'content') else {},
                'order': lesson.order,
                'estimated_minutes': lesson.estimated_minutes,
                'is_preview': lesson.is_preview,
                'is_milestone': lesson.is_milestone,
            }
        })
    
    try:
        import json
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
        
        # Check if this is a GET request via POST (for compatibility)
        if data.get('get') == True or data.get('get') == 'true':
            return JsonResponse({
                'success': True,
                'lesson': {
                    'id': lesson.id,
                    'title': lesson.title,
                    'description': lesson.description,
                    'content_type': lesson.content_type,
                    'video_url': lesson.video_url,
                    'video_duration': lesson.video_duration,
                    'text_content': lesson.text_content,
                    'content': lesson.content if hasattr(lesson, 'content') else {},
                    'order': lesson.order,
                    'estimated_minutes': lesson.estimated_minutes,
                    'is_preview': lesson.is_preview,
                    'is_milestone': lesson.is_milestone,
                }
            })
        
        if 'title' in data:
            lesson.title = data['title'].strip()
        if 'description' in data:
            lesson.description = data.get('description', '')
        if 'content_type' in data:
            lesson.content_type = data['content_type']
        if 'video_url' in data:
            lesson.video_url = data.get('video_url', '')
        if 'video_duration' in data:
            lesson.video_duration = int(data.get('video_duration', 0) or 0)
        if 'text_content' in data:
            lesson.text_content = data.get('text_content', '')
        if 'content' in data:
            # Handle Editor.js JSON content
            import json
            try:
                content_data = data.get('content', {})
                if isinstance(content_data, str):
                    content_data = json.loads(content_data)
                lesson.content = content_data if content_data else {}
            except (json.JSONDecodeError, TypeError):
                pass  # Keep existing content if JSON is invalid
        if 'order' in data:
            lesson.order = int(data['order'])
        if 'estimated_minutes' in data:
            lesson.estimated_minutes = int(data.get('estimated_minutes', 10) or 10)
        if 'is_preview' in data:
            lesson.is_preview = data['is_preview'] == True or data['is_preview'] == 'true'
        if 'is_milestone' in data:
            lesson.is_milestone = data['is_milestone'] == True or data['is_milestone'] == 'true'
        
        lesson.save()
        
        return JsonResponse({
            'success': True,
            'lesson': {
                'id': lesson.id,
                'title': lesson.title,
                'description': lesson.description,
                'content_type': lesson.content_type,
                'video_url': lesson.video_url,
                'video_duration': lesson.video_duration,
                'order': lesson.order,
                'estimated_minutes': lesson.estimated_minutes,
                'is_preview': lesson.is_preview,
                'is_milestone': lesson.is_milestone,
            }
        })
    except Exception as e:
        import traceback
        return JsonResponse({'success': False, 'error': str(e), 'traceback': traceback.format_exc()}, status=500)


@login_required
@role_required(['admin'])
@require_POST
def dashboard_api_lesson_delete(request, lesson_id):
    """Delete a lesson"""
    lesson = get_object_or_404(Lesson, id=lesson_id)
    
    try:
        lesson.delete()
        return JsonResponse({'success': True, 'message': 'Lesson deleted successfully'})
    except Exception as e:
        import traceback
        return JsonResponse({'success': False, 'error': str(e), 'traceback': traceback.format_exc()}, status=500)


@login_required
@role_required(['admin'])
def dashboard_api_quizzes(request, course_id):
    """Get all quizzes for a course"""
    course = get_object_or_404(Course, id=course_id)
    quizzes = course.quizzes.all().prefetch_related('questions').order_by('created_at')
    
    quizzes_data = []
    for quiz in quizzes:
        quizzes_data.append({
            'id': quiz.id,
            'title': quiz.title,
            'description': quiz.description,
            'quiz_type': quiz.quiz_type,
            'passing_score': quiz.passing_score,
            'time_limit_minutes': quiz.time_limit_minutes,
            'max_attempts': quiz.max_attempts,
            'questions_count': quiz.questions.count(),
        })
    
    return JsonResponse({'success': True, 'quizzes': quizzes_data})


@login_required
@role_required(['admin'])
@require_POST
def dashboard_api_quiz_create(request, course_id):
    """Create a new quiz"""
    course = get_object_or_404(Course, id=course_id)
    
    try:
        import json
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
        
        title = data.get('title', '').strip()
        if not title:
            return JsonResponse({'success': False, 'error': 'Quiz title is required'}, status=400)
        
        quiz = Quiz.objects.create(
            course=course,
            title=title,
            description=data.get('description', ''),
            quiz_type=data.get('quiz_type', 'lesson'),
            passing_score=int(data.get('passing_score', 70) or 70),
            time_limit_minutes=int(data.get('time_limit_minutes', 0) or 0) or None,
            max_attempts=int(data.get('max_attempts', 3) or 3),
            randomize_questions=data.get('randomize_questions', True) == True or data.get('randomize_questions') == 'true',
            show_correct_answers=data.get('show_correct_answers', True) == True or data.get('show_correct_answers') == 'true',
        )
        
        return JsonResponse({
            'success': True,
            'quiz': {
                'id': quiz.id,
                'title': quiz.title,
                'description': quiz.description,
                'quiz_type': quiz.quiz_type,
                'passing_score': quiz.passing_score,
                'time_limit_minutes': quiz.time_limit_minutes,
                'max_attempts': quiz.max_attempts,
                'questions_count': 0,
            }
        })
    except Exception as e:
        import traceback
        return JsonResponse({'success': False, 'error': str(e), 'traceback': traceback.format_exc()}, status=500)


@login_required
@role_required(['admin'])
def dashboard_api_quiz_update(request, quiz_id):
    """Update a quiz (or get quiz data if GET request)"""
    quiz = get_object_or_404(Quiz, id=quiz_id)
    
    if request.method == 'GET':
        return JsonResponse({
            'success': True,
            'quiz': {
                'id': quiz.id,
                'title': quiz.title,
                'description': quiz.description,
                'quiz_type': quiz.quiz_type,
                'passing_score': quiz.passing_score,
                'time_limit_minutes': quiz.time_limit_minutes,
                'max_attempts': quiz.max_attempts,
                'randomize_questions': quiz.randomize_questions,
                'show_correct_answers': quiz.show_correct_answers,
            }
        })
    
    try:
        import json
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
        
        # Check if this is a GET request via POST (for compatibility)
        if data.get('get') == True or data.get('get') == 'true':
            return JsonResponse({
                'success': True,
                'quiz': {
                    'id': quiz.id,
                    'title': quiz.title,
                    'description': quiz.description,
                    'quiz_type': quiz.quiz_type,
                    'passing_score': quiz.passing_score,
                    'time_limit_minutes': quiz.time_limit_minutes,
                    'max_attempts': quiz.max_attempts,
                    'randomize_questions': quiz.randomize_questions,
                    'show_correct_answers': quiz.show_correct_answers,
                }
            })
        
        if 'title' in data:
            quiz.title = data['title'].strip()
        if 'description' in data:
            quiz.description = data.get('description', '')
        if 'quiz_type' in data:
            quiz.quiz_type = data['quiz_type']
        if 'passing_score' in data:
            quiz.passing_score = int(data.get('passing_score', 70) or 70)
        if 'time_limit_minutes' in data:
            time_limit = int(data.get('time_limit_minutes', 0) or 0)
            quiz.time_limit_minutes = time_limit if time_limit > 0 else None
        if 'max_attempts' in data:
            quiz.max_attempts = int(data.get('max_attempts', 3) or 3)
        if 'randomize_questions' in data:
            quiz.randomize_questions = data['randomize_questions'] == True or data['randomize_questions'] == 'true'
        if 'show_correct_answers' in data:
            quiz.show_correct_answers = data['show_correct_answers'] == True or data['show_correct_answers'] == 'true'
        
        quiz.save()
        
        return JsonResponse({
            'success': True,
            'quiz': {
                'id': quiz.id,
                'title': quiz.title,
                'description': quiz.description,
                'quiz_type': quiz.quiz_type,
                'passing_score': quiz.passing_score,
                'time_limit_minutes': quiz.time_limit_minutes,
                'max_attempts': quiz.max_attempts,
            }
        })
    except Exception as e:
        import traceback
        return JsonResponse({'success': False, 'error': str(e), 'traceback': traceback.format_exc()}, status=500)


@login_required
@role_required(['admin'])
@require_POST
def dashboard_api_quiz_delete(request, quiz_id):
    """Delete a quiz"""
    quiz = get_object_or_404(Quiz, id=quiz_id)
    
    try:
        quiz.delete()
        return JsonResponse({'success': True, 'message': 'Quiz deleted successfully'})
    except Exception as e:
        import traceback
        return JsonResponse({'success': False, 'error': str(e), 'traceback': traceback.format_exc()}, status=500)


@login_required
@role_required(['admin'])
def dashboard_api_quiz_questions(request, quiz_id):
    """Get all questions for a quiz"""
    quiz = get_object_or_404(Quiz, id=quiz_id)
    questions = quiz.questions.all().prefetch_related('answers').order_by('order')
    
    questions_data = []
    for question in questions:
        answers_data = []
        for answer in question.answers.all().order_by('order'):
            answers_data.append({
                'id': answer.id,
                'answer_text': answer.answer_text,
                'is_correct': answer.is_correct,
                'order': answer.order,
            })
        
        questions_data.append({
            'id': question.id,
            'question_text': question.question_text,
            'question_type': question.question_type,
            'points': question.points,
            'order': question.order,
            'explanation': question.explanation,
            'hint': question.hint,
            'answers': answers_data,
        })
    
    return JsonResponse({'success': True, 'questions': questions_data})


@login_required
@role_required(['admin'])
@require_POST
def dashboard_api_question_create(request, quiz_id):
    """Create a new question for a quiz"""
    quiz = get_object_or_404(Quiz, id=quiz_id)
    
    try:
        import json
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
        
        question_text = data.get('question_text', '').strip()
        if not question_text:
            return JsonResponse({'success': False, 'error': 'Question text is required'}, status=400)
        
        # Get the highest order number
        max_order = quiz.questions.aggregate(Max('order'))['order__max'] or 0
        
        question = Question.objects.create(
            quiz=quiz,
            question_text=question_text,
            question_type=data.get('question_type', 'multiple_choice'),
            points=int(data.get('points', 1) or 1),
            order=max_order + 1,
            explanation=data.get('explanation', ''),
            hint=data.get('hint', ''),
        )
        
        # Create answers if provided
        answers_data = data.get('answers', [])
        if isinstance(answers_data, str):
            import json
            try:
                answers_data = json.loads(answers_data)
            except:
                answers_data = []
        
        for idx, answer_data in enumerate(answers_data):
            if isinstance(answer_data, dict):
                Answer.objects.create(
                    question=question,
                    answer_text=answer_data.get('answer_text', ''),
                    is_correct=answer_data.get('is_correct', False) == True or answer_data.get('is_correct') == 'true',
                    order=answer_data.get('order', idx),
                )
        
        return JsonResponse({
            'success': True,
            'question': {
                'id': question.id,
                'question_text': question.question_text,
                'question_type': question.question_type,
                'points': question.points,
                'order': question.order,
            }
        })
    except Exception as e:
        import traceback
        return JsonResponse({'success': False, 'error': str(e), 'traceback': traceback.format_exc()}, status=500)


@login_required
@role_required(['admin'])
@require_POST
def dashboard_api_editor_image(request):
    """Upload image for Editor.js"""
    from myApp.utils.cloudinary_utils import upload_image_to_cloudinary
    
    if 'file' not in request.FILES:
        return JsonResponse({'success': False, 'error': 'No file provided'}, status=400)
    
    try:
        file = request.FILES['file']
        
        # Upload to Cloudinary
        result = upload_image_to_cloudinary(
            file,
            folder='editor-images',
            should_convert_to_webp=True
        )
        
        if result and result.get('secure_url'):
            return JsonResponse({
                'success': True,
                'url': result['secure_url']
            })
        else:
            return JsonResponse({'success': False, 'error': 'Upload failed'}, status=500)
            
    except Exception as e:
        import traceback
        logger.error(f'Editor image upload error: {traceback.format_exc()}')
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

