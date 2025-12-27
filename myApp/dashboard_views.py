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
    Payment, Media, SiteSettings, PlacementTest, Teacher, CourseTeacher,
    Category
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


# ============================================
# TEACHER MANAGEMENT
# ============================================

@login_required
@role_required(['admin'])
def dashboard_teachers(request):
    """Teacher management"""
    teachers = Teacher.objects.select_related('user').order_by('-created_at')
    
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
            Q(user__last_name__icontains=search)
        )
    
    paginator = Paginator(teachers, 20)
    page = request.GET.get('page', 1)
    teachers = paginator.get_page(page)
    
    context = {
        'teachers': teachers,
        'selected_status': status,
        'search_query': search,
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
@require_POST
def dashboard_teacher_assign_course(request, teacher_id):
    """Assign course to teacher"""
    teacher = get_object_or_404(Teacher, id=teacher_id)
    data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
    
    course_id = data.get('course_id')
    permission_level = data.get('permission_level', 'view_only')
    can_create_live_classes = data.get('can_create_live_classes', 'false') == 'true'
    
    course = get_object_or_404(Course, id=course_id)
    
    # Check if already assigned
    assignment, created = CourseTeacher.objects.get_or_create(
        course=course,
        teacher=teacher,
        defaults={
            'permission_level': permission_level,
            'can_create_live_classes': can_create_live_classes,
            'assigned_by': request.user
        }
    )
    
    if not created:
        assignment.permission_level = permission_level
        assignment.can_create_live_classes = can_create_live_classes
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
                'status': 'active'
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
            teacher = Teacher.objects.create(user=user, is_approved=True, approved_by=request.user, approved_at=timezone.now())
            messages.success(request, f'Teacher {username} created and auto-approved!')
        else:
            messages.success(request, f'User {username} created successfully!')
        
        return redirect('dashboard:users')
    
    context = {}
    return render(request, 'dashboard/user_create.html', context)

