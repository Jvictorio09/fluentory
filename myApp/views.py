from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse
from django.db.models import Count, Avg, Sum, Q
from django.db import connection, transaction
from django.utils import timezone
from django.views.decorators.http import require_POST, require_GET
from django.core.paginator import Paginator
from django.conf import settings
from django.db.utils import OperationalError, DatabaseError
import json
import openai

from .models import (
    UserProfile, Category, Course, CoursePricing, Module, Lesson,
    Quiz, Question, Answer, Enrollment, LessonProgress, QuizAttempt,
    Certificate, PlacementTest, TutorConversation, TutorMessage, AITutorSettings,
    Partner, Cohort, CohortMembership, Payment, Review, FAQ,
    Notification, SiteSettings, Media, Teacher, CourseTeacher,
    LiveClassSession, CourseAnnouncement, StudentMessage,
    TeacherAvailability, Booking, OneOnOneBooking, BookingReminder,
    LiveClassBooking, TeacherBookingPolicy, BookingSeries, BookingSeriesItem, SessionWaitlist
)


# ============================================
# HELPER FUNCTIONS
# ============================================

# Message scoping constants
MESSAGE_SCOPE_AUTH = 'auth'
MESSAGE_SCOPE_APP = 'app'

def get_site_settings():
    """Get site settings singleton"""
    return SiteSettings.get_settings()


def message_auth(request, level, message):
    """
    Add an authentication-scoped message.
    These messages appear on the login page.
    """
    extra_tags = MESSAGE_SCOPE_AUTH
    if level == messages.SUCCESS:
        messages.success(request, message, extra_tags=extra_tags)
    elif level == messages.ERROR:
        messages.error(request, message, extra_tags=extra_tags)
    elif level == messages.INFO:
        messages.info(request, message, extra_tags=extra_tags)
    elif level == messages.WARNING:
        messages.warning(request, message, extra_tags=extra_tags)
    else:
        messages.add_message(request, level, message, extra_tags=extra_tags)


def message_app(request, level, message):
    """
    Add an application-scoped message.
    These messages appear in authenticated pages only, not on login page.
    """
    extra_tags = MESSAGE_SCOPE_APP
    if level == messages.SUCCESS:
        messages.success(request, message, extra_tags=extra_tags)
    elif level == messages.ERROR:
        messages.error(request, message, extra_tags=extra_tags)
    elif level == messages.INFO:
        messages.info(request, message, extra_tags=extra_tags)
    elif level == messages.WARNING:
        messages.warning(request, message, extra_tags=extra_tags)
    else:
        messages.add_message(request, level, message, extra_tags=extra_tags)


def get_or_create_profile(user):
    """Get or create a user profile. Auto-creates profile if missing."""
    if not hasattr(user, 'profile'):
        # Auto-create profile with default role
        # If user is superuser/staff, make them admin
        default_role = 'admin' if (user.is_superuser or user.is_staff) else 'student'
        UserProfile.objects.create(user=user, role=default_role)
        user.refresh_from_db()
    return user.profile


def role_required(allowed_roles):
    """Decorator to check user role. Allows superusers/admins to access everything (godlike admin)."""
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            
            # Allow superusers/staff to access admin views even without profile
            if 'admin' in allowed_roles and (request.user.is_superuser or request.user.is_staff):
                return view_func(request, *args, **kwargs)
            
            # Get or create profile
            profile = get_or_create_profile(request.user)
            
            # Godlike Admin Feature: Admins can access ALL views (for preview/switching)
            if profile.role == 'admin' or request.user.is_superuser or request.user.is_staff:
                return view_func(request, *args, **kwargs)
            
            if profile.role in allowed_roles:
                return view_func(request, *args, **kwargs)
            # Show 403 page instead of redirecting
            from django.shortcuts import render
            return render(request, '403.html', status=403)
        return wrapper
    return decorator


def teacher_approved_required(view_func):
    """Decorator to check if teacher is approved. Redirects pending teachers to pending page."""
    def wrapper(request, *args, **kwargs):
        user = request.user
        profile = get_or_create_profile(user)
        
        # Allow superusers/admins to access automatically
        is_superuser_or_admin = user.is_superuser or user.is_staff or profile.role == 'admin'
        if is_superuser_or_admin:
            return view_func(request, *args, **kwargs)
        
        # Check if user has teacher profile
        if hasattr(user, 'teacher_profile'):
            teacher = user.teacher_profile
            if not teacher.is_approved:
                message_app(request, messages.INFO, 'Your teacher account is under review. We\'ll notify you once approved.')
                return render(request, 'auth/teacher_pending.html')
        
        return view_func(request, *args, **kwargs)
    return wrapper


# ============================================
# LANDING PAGE
# ============================================

def home(request):
    """Public landing page"""
    site_settings = get_site_settings()
    
    # Featured courses
    featured_courses = Course.objects.filter(
        status='published'
    ).select_related('category', 'instructor').order_by('-enrolled_count')[:6]
    
    # FAQs
    faqs = FAQ.objects.filter(is_active=True, is_featured=True).order_by('order')[:6]
    
    # Categories
    categories = Category.objects.annotate(
        course_count=Count('courses', filter=Q(courses__status='published'))
    ).order_by('order')
    
    # Reviews/Testimonials
    reviews = Review.objects.filter(
        is_approved=True, 
        is_featured=True
    ).select_related('user', 'course').order_by('-created_at')[:5]
    
    context = {
        'site_settings': site_settings,
        'featured_courses': featured_courses,
        'faqs': faqs,
        'categories': categories,
        'reviews': reviews,
    }
    return render(request, 'landing.html', context)


# ============================================
# STATIC PAGES
# ============================================

def about_page(request):
    """About page"""
    return render(request, 'pages/about.html')


def careers_page(request):
    """Careers page"""
    return render(request, 'pages/careers.html')


def blog_page(request):
    """Blog page"""
    return render(request, 'pages/blog.html')


def help_center_page(request):
    """Help Center page"""
    return render(request, 'pages/help_center.html')


def contact_page(request):
    """Contact page"""
    return render(request, 'pages/contact.html')


def privacy_page(request):
    """Privacy Policy page"""
    return render(request, 'pages/privacy.html')


def terms_page(request):
    """Terms of Service page"""
    return render(request, 'pages/terms.html')


def cookies_page(request):
    """Cookies Policy page"""
    return render(request, 'pages/cookies.html')


# ============================================
# AUTHENTICATION
# ============================================

def login_view(request):
    """User login"""
    # If user is already authenticated, normally redirect them to their dashboard.
    # However, if the request explicitly asks to show the login form (e.g. ?show=login),
    # render the login page so they can enter different credentials.
    if request.user.is_authenticated and not request.GET.get('show'):
        return redirect_by_role(request.user)
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            # Check if teacher is pending approval
            if hasattr(user, 'teacher_profile') and not user.teacher_profile.is_approved:
                # Don't log them in, show pending message
                message_auth(request, messages.INFO, 'Your teacher account is under review. We\'ll notify you once approved.')
                return render(request, 'auth/login.html')
            
            # Check if password reset is required
            profile = get_or_create_profile(user)
            if profile.force_password_reset:
                # Store user ID in session for password reset flow
                request.session['force_password_reset_user_id'] = user.id
                login(request, user)
                message_auth(request, messages.WARNING, 'You must change your password before continuing.')
                return redirect('accounts:password_change')
            
            login(request, user)
            message_auth(request, messages.SUCCESS, f'Welcome back, {user.first_name or user.username}!')
            
            # Redirect based on role
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect_by_role(user)
        else:
            message_auth(request, messages.ERROR, 'Invalid username or password.')
    # On GET request, the template will filter messages by scope
    # Auth-scoped messages will be displayed
    # App-scoped messages will be consumed when iterated but not displayed
    # This ensures they don't appear on the login page
    # Note: App-scoped messages should be set on authenticated pages, not before login
    return render(request, 'auth/login.html')


def signup_view(request):
    """User registration"""
    if request.user.is_authenticated:
        return redirect_by_role(request.user)
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        
        # Validation
        if password != password_confirm:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'auth/signup.html')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return render(request, 'auth/signup.html')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
            return render(request, 'auth/signup.html')
        
        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        
        login(request, user)
        messages.success(request, 'Welcome to Fluentory! Start by taking our placement test.')
        return redirect('student_placement')
    
    return render(request, 'auth/signup.html')


def teacher_signup_view(request):
    """Teacher registration with pending approval"""
    if request.user.is_authenticated:
        return redirect_by_role(request.user)
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        bio = request.POST.get('bio', '')
        specialization = request.POST.get('specialization', '')
        years_experience = request.POST.get('years_experience', '0')
        
        # Validation
        if password != password_confirm:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'auth/teacher_signup.html')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return render(request, 'auth/teacher_signup.html')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
            return render(request, 'auth/teacher_signup.html')
        
        # Create user (inactive until approved)
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_active=True  # User can log in, but teacher portal access is restricted
        )
        
        # Create user profile with instructor role
        profile = get_or_create_profile(user)
        profile.role = 'instructor'
        profile.bio = bio
        profile.save()
        
        # Create teacher profile (pending approval)
        teacher = Teacher.objects.create(
            user=user,
            is_approved=False,  # Pending approval
            bio=bio,
            specialization=specialization,
            years_experience=int(years_experience) if years_experience.isdigit() else 0
        )
        
        # Redirect to pending confirmation page
        return redirect('teacher_signup_pending')
    
    return render(request, 'auth/teacher_signup.html')


def teacher_signup_pending(request):
    """Teacher signup pending approval confirmation page"""
    # Allow both authenticated and unauthenticated users to see this page
    # If authenticated, check their status
    if request.user.is_authenticated:
        if hasattr(request.user, 'teacher_profile'):
            teacher = request.user.teacher_profile
            if teacher.is_approved:
                # Already approved, redirect to dashboard
                return redirect('teacher_dashboard')
    return render(request, 'auth/teacher_pending.html')


def logout_view(request):
    """User logout"""
    logout(request)
    message_auth(request, messages.INFO, 'You have been logged out.')
    # Allow an optional `next` parameter so callers can control where to go after logout.
    next_url = request.GET.get('next') or request.POST.get('next')
    if next_url:
        return redirect(next_url)
    # Default: send the user to the login page so they can sign in again.
    return redirect('login')


def redirect_by_role(user):
    """Redirect user based on their role"""
    # Allow superusers/staff to access admin dashboard
    if user.is_superuser or user.is_staff:
        return redirect('dashboard:overview')
    
    profile = get_or_create_profile(user)
    role = profile.role
    
    # Check if user is a teacher (must be approved)
    if role == 'instructor' or hasattr(user, 'teacher_profile'):
        if hasattr(user, 'teacher_profile') and user.teacher_profile.is_approved:
            return redirect('teacher_dashboard')
        # Pending teacher - redirect to pending page
        return redirect('teacher_signup_pending')
    elif role == 'admin':
        return redirect('dashboard:overview')
    elif role == 'partner':
        return redirect('partner_overview')
    return redirect('student_home')


# ============================================
# STUDENT VIEWS
# ============================================

@login_required
def student_home(request):
    """Student dashboard"""
    user = request.user
    profile = get_or_create_profile(user)
    
    # Check if admin/superuser is previewing as teacher - redirect to teacher dashboard
    preview_role = request.session.get('preview_role')
    if preview_role == 'teacher':
        # Check if user is admin or superuser
        if profile.role == 'admin' or user.is_superuser or user.is_staff:
            return redirect('teacher_dashboard')
    
    try:
        # Ensure database connection is alive
        connection.ensure_connection()
        
        # Update streak
        try:
            profile.update_streak()
        except (OperationalError, DatabaseError):
            # If connection fails, refresh and retry
            connection.close()
            connection.ensure_connection()
            profile.refresh_from_db()
            profile.update_streak()
        
        # Current enrollment (continue learning)
        current_enrollment = Enrollment.objects.filter(
            user=user,
            status='active'
        ).select_related('course', 'current_lesson', 'current_module').first()
        
        # All active enrollments
        enrollments = Enrollment.objects.filter(
            user=user,
            status__in=['active', 'completed']
        ).select_related('course').order_by('-enrolled_at')[:5]
        
        # Recommended courses (not enrolled)
        enrolled_course_ids = Enrollment.objects.filter(user=user).values_list('course_id', flat=True)
        recommended_courses = Course.objects.filter(
            status='published'
        ).exclude(
            id__in=enrolled_course_ids
        ).order_by('-enrolled_count')[:6]
        
        # Placement test result
        placement_test = PlacementTest.objects.filter(user=user).order_by('-taken_at').first()
        
        # Upcoming milestones
        if current_enrollment:
            upcoming_quiz = Quiz.objects.filter(
                course=current_enrollment.course,
                quiz_type__in=['module', 'final']
            ).exclude(
                attempts__user=user,
                attempts__passed=True
            ).first()
        else:
            upcoming_quiz = None
        
        # Certificates
        certificates_count = Certificate.objects.filter(user=user).count()
        
        # Learning stats this week
        week_start = timezone.now().date() - timezone.timedelta(days=7)
        week_learning_minutes = LessonProgress.objects.filter(
            enrollment__user=user,
            started_at__date__gte=week_start
        ).aggregate(total=Sum('time_spent'))['total'] or 0
        
        # Notifications (unread)
        notifications = Notification.objects.filter(
            user=user,
            is_read=False
        ).order_by('-created_at')[:5]
        
        context = {
            'profile': profile,
            'current_enrollment': current_enrollment,
            'enrollments': enrollments,
            'recommended_courses': recommended_courses,
            'placement_test': placement_test,
            'upcoming_quiz': upcoming_quiz,
            'certificates_count': certificates_count,
            'week_learning_minutes': week_learning_minutes // 60,  # Convert to hours
            'notifications': notifications,
        }
        return render(request, 'student/home.html', context)
    
    except (OperationalError, DatabaseError) as e:
        # Handle database connection errors gracefully
        connection.close()
        messages.error(request, 'Database connection error. Please try again.')
        # Return a simplified context with empty data
        context = {
            'profile': get_or_create_profile(user),
            'current_enrollment': None,
            'enrollments': [],
            'recommended_courses': [],
            'placement_test': None,
            'upcoming_quiz': None,
            'certificates_count': 0,
            'week_learning_minutes': 0,
            'notifications': [],
        }
        return render(request, 'student/home.html', context)


@login_required
def student_courses(request):
    """Course catalog for students"""
    user = request.user
    
    # Get filter parameters
    level = request.GET.get('level')
    category_slug = request.GET.get('category')
    search = request.GET.get('search')
    
    # Base queryset - Show ALL published courses regardless of who created them
    courses = Course.objects.filter(status='published').select_related('category', 'instructor')
    
    # Apply filters
    if level:
        courses = courses.filter(level=level)
    if category_slug:
        courses = courses.filter(category__slug=category_slug)
    if search:
        courses = courses.filter(
            Q(title__icontains=search) | 
            Q(description__icontains=search) |
            Q(outcome__icontains=search)
        )
    
    # Log the queryset for debugging (temporary - can be removed after verification)
    import logging
    logger = logging.getLogger(__name__)
    course_ids = list(courses.values_list('id', flat=True))
    logger.info(f"Student Course Catalog Query - Found {len(course_ids)} published courses. Course IDs: {course_ids}")
    
    # Get categories for filter
    categories = Category.objects.annotate(
        course_count=Count('courses', filter=Q(courses__status='published'))
    ).filter(course_count__gt=0)
    
    # Get user's enrolled courses
    enrolled_course_ids = list(Enrollment.objects.filter(user=user).values_list('course_id', flat=True))
    
    # Pagination
    paginator = Paginator(courses, 12)
    page = request.GET.get('page', 1)
    courses = paginator.get_page(page)
    
    # Get selected currency from session
    selected_currency = request.session.get('selected_currency', 'USD')
    
    # Prefetch pricing for all courses
    course_pricing_map = {}
    course_ids = [c.id for c in courses]
    pricing_objects = CoursePricing.objects.filter(course_id__in=course_ids, currency=selected_currency).select_related('course')
    for pricing in pricing_objects:
        course_pricing_map[pricing.course_id] = pricing.price
    
    # Add pricing info to each course object for template access
    for course in courses:
        if course.id in course_pricing_map:
            course.display_price = course_pricing_map[course.id]
            course.display_currency = selected_currency
        else:
            course.display_price = course.price
            course.display_currency = course.currency
    
    context = {
        'courses': courses,
        'categories': categories,
        'enrolled_course_ids': enrolled_course_ids,
        'selected_level': level,
        'selected_category': category_slug,
        'search_query': search,
        'selected_currency': selected_currency,
    }
    return render(request, 'student/courses.html', context)


@login_required
def student_course_detail(request, slug):
    """Course detail page"""
    course = get_object_or_404(Course, slug=slug, status='published')
    user = request.user
    
    # Check if enrolled
    enrollment = Enrollment.objects.filter(user=user, course=course).first()
    
    # Get selected currency from session
    selected_currency = request.session.get('selected_currency', 'USD')
    
    # Get price in selected currency
    try:
        pricing = CoursePricing.objects.get(course=course, currency=selected_currency)
        course_price = pricing.price
        course_currency = selected_currency
    except CoursePricing.DoesNotExist:
        if selected_currency == course.currency:
            course_price = course.price
            course_currency = course.currency
        else:
            # Fallback to course's default currency
            course_price = course.price
            course_currency = course.currency
    
    # For live courses, show different content
    if course.course_type == 'live':
        # Get quizzes for this course
        quizzes = course.quizzes.all().order_by('-created_at')
        
        # Get upcoming live class sessions
        from django.utils import timezone
        now = timezone.now()
        upcoming_sessions = LiveClassSession.objects.filter(
            course=course,
            status='scheduled',
            scheduled_start__gt=now
        ).select_related('teacher', 'teacher__user').order_by('scheduled_start')[:10]
        
        # Get course announcements (activities)
        announcements = CourseAnnouncement.objects.filter(
            course=course
        ).order_by('-created_at')[:10]
        
        # Get user's quiz attempts to show status
        quiz_attempts_dict = {}
        if enrollment:
            from myApp.models import QuizAttempt
            attempts = QuizAttempt.objects.filter(
                user=user,
                quiz__course=course
            ).select_related('quiz').order_by('-started_at')
            for attempt in attempts:
                if attempt.quiz_id not in quiz_attempts_dict:
                    quiz_attempts_dict[attempt.quiz_id] = attempt
        
        # Add attempt info to each quiz
        for quiz in quizzes:
            quiz.user_attempt = quiz_attempts_dict.get(quiz.id)
        
        context = {
            'course': course,
            'enrollment': enrollment,
            'quizzes': quizzes,
            'upcoming_sessions': upcoming_sessions,
            'announcements': announcements,
            'selected_currency': selected_currency,
            'course_price': course_price,
            'course_currency': course_currency,
            'is_live_course': True,
        }
        return render(request, 'student/course_detail_live.html', context)
    
    # For recorded/hybrid courses, show standard content
    # Course modules and lessons
    modules = course.modules.prefetch_related('lessons').order_by('order')
    
    # Reviews
    reviews = course.reviews.filter(is_approved=True).select_related('user').order_by('-created_at')[:10]
    
    # Similar courses
    similar_courses = Course.objects.filter(
        category=course.category,
        status='published'
    ).exclude(id=course.id)[:4]
    
    context = {
        'course': course,
        'enrollment': enrollment,
        'modules': modules,
        'reviews': reviews,
        'similar_courses': similar_courses,
        'selected_currency': selected_currency,
        'course_price': course_price,
        'course_currency': course_currency,
        'is_live_course': False,
    }
    return render(request, 'student/course_detail.html', context)


@login_required
def student_placement(request):
    """Placement test page"""
    user = request.user
    
    # Check if already taken
    existing_test = PlacementTest.objects.filter(user=user).order_by('-taken_at').first()
    
    # Get placement quiz
    placement_quiz = Quiz.objects.filter(quiz_type='placement').first()
    
    if request.method == 'POST' and placement_quiz:
        # Process quiz submission
        answers = {}
        score = 0
        total_points = 0
        
        for question in placement_quiz.questions.all():
            answer_id = request.POST.get(f'question_{question.id}')
            if answer_id:
                answers[str(question.id)] = answer_id
                correct_answer = question.answers.filter(is_correct=True).first()
                if correct_answer and str(correct_answer.id) == answer_id:
                    score += question.points
            total_points += question.points
        
        # Calculate percentage
        percentage = (score / total_points * 100) if total_points > 0 else 0
        
        # Determine level
        if percentage >= 80:
            level = 'advanced'
        elif percentage >= 50:
            level = 'intermediate'
        else:
            level = 'beginner'
        
        # Create placement test record
        placement = PlacementTest.objects.create(
            user=user,
            quiz=placement_quiz,
            score=percentage,
            recommended_level=level
        )
        
        # Add recommended courses
        recommended = Course.objects.filter(
            level=level,
            status='published'
        )[:5]
        placement.recommended_courses.set(recommended)
        
        messages.success(request, f'Your level: {level.title()}! Check your recommended courses.')
        return redirect('student_home')
    
    context = {
        'existing_test': existing_test,
        'placement_quiz': placement_quiz,
        'questions': placement_quiz.questions.prefetch_related('answers').order_by('order') if placement_quiz else [],
    }
    return render(request, 'student/placement.html', context)


@login_required
def student_learning(request):
    """My Learning page - all enrollments"""
    user = request.user
    
    # Active enrollments
    active_enrollments = Enrollment.objects.filter(
        user=user,
        status='active'
    ).select_related('course', 'current_lesson', 'current_module').prefetch_related('course__modules__lessons').order_by('-enrolled_at')
    
    # Add additional info for each enrollment
    for enrollment in active_enrollments:
        # Update progress if needed
        enrollment.update_progress()
        
        # Calculate current lesson number and total lessons
        total_lessons = Lesson.objects.filter(module__course=enrollment.course).count()
        enrollment.total_lessons = total_lessons
        
        if enrollment.current_lesson:
            # Find current lesson number
            all_lessons = Lesson.objects.filter(module__course=enrollment.course).order_by('module__order', 'order')
            lesson_numbers = {lesson.id: idx + 1 for idx, lesson in enumerate(all_lessons)}
            enrollment.current_lesson_number = lesson_numbers.get(enrollment.current_lesson.id, 0)
        else:
            enrollment.current_lesson_number = 0
        
        # Calculate hours remaining (estimated)
        completed_lessons = LessonProgress.objects.filter(enrollment=enrollment, completed=True).count()
        remaining_lessons = max(0, total_lessons - completed_lessons)
        enrollment.estimated_hours_remaining = (enrollment.course.estimated_hours / total_lessons * remaining_lessons) if total_lessons > 0 else 0
        
        # Days since enrollment
        days_since = (timezone.now().date() - enrollment.enrolled_at.date()).days
        enrollment.days_since_enrollment = days_since
    
    # Completed enrollments
    completed_enrollments = Enrollment.objects.filter(
        user=user,
        status='completed'
    ).select_related('course').order_by('-completed_at')
    
    context = {
        'active_enrollments': active_enrollments,
        'completed_enrollments': completed_enrollments,
    }
    return render(request, 'student/learning.html', context)


@login_required
def student_certificates(request):
    """Certificates page"""
    user = request.user
    
    certificates = Certificate.objects.filter(user=user).select_related('course').order_by('-issued_at')
    
    context = {
        'certificates': certificates,
    }
    return render(request, 'student/certificates.html', context)


@login_required
def student_settings(request):
    """Student settings page"""
    user = request.user
    profile = get_or_create_profile(user)
    
    if request.method == 'POST':
        # Update user info
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        user.save()
        
        # Update profile
        profile.preferred_language = request.POST.get('language', profile.preferred_language)
        profile.timezone = request.POST.get('timezone', profile.timezone)
        profile.daily_goal_minutes = int(request.POST.get('daily_goal', profile.daily_goal_minutes))
        profile.learning_goal = request.POST.get('learning_goal', profile.learning_goal)
        profile.save()
        
        messages.success(request, 'Settings updated successfully!')
        return redirect('student_settings')
    
    context = {
        'user': user,
        'profile': profile,
    }
    return render(request, 'student/settings.html', context)


@login_required
def student_course_player(request, enrollment_id=None, lesson_id=None):
    """Course player - learning interface"""
    user = request.user
    
    # Get enrollment
    if enrollment_id:
        enrollment = get_object_or_404(Enrollment, id=enrollment_id, user=user)
    else:
        enrollment = Enrollment.objects.filter(user=user, status='active').first()
    
    if not enrollment:
        messages.warning(request, 'No active course found. Browse our catalog!')
        return redirect('student_courses')
    
    course = enrollment.course
    
    # Check if this is a live class course - these don't have lessons
    if course.course_type == 'live':
        # Redirect to live classes page for live courses
        message_app(request, messages.INFO, 'This is a live class course. View available live sessions to book.')
        return redirect('student_live_classes')
    
    # Get current lesson
    if lesson_id:
        current_lesson = get_object_or_404(Lesson, id=lesson_id, module__course=course)
    else:
        current_lesson = enrollment.current_lesson
        if not current_lesson:
            # Start from first lesson
            first_module = course.modules.order_by('order').first()
            if first_module:
                current_lesson = first_module.lessons.order_by('order').first()
    
    # If no lesson found, show message and redirect
    if not current_lesson:
        messages.warning(request, 'This course has no lessons available yet. Please check back later.')
        return redirect('student_course_detail', slug=course.slug)
    
    # Update enrollment's current position
    if current_lesson:
        enrollment.current_lesson = current_lesson
        enrollment.current_module = current_lesson.module
        enrollment.save()
    
    # Get or create lesson progress - only if lesson exists
    progress = None
    if current_lesson:
        progress, created = LessonProgress.objects.get_or_create(
            enrollment=enrollment,
            lesson=current_lesson
        )
    
    # Get all modules with lessons
    modules = course.modules.prefetch_related('lessons').order_by('order')
    
    # Get completed lesson IDs
    completed_lesson_ids = list(LessonProgress.objects.filter(
        enrollment=enrollment,
        completed=True
    ).values_list('lesson_id', flat=True))
    
    # AI Tutor conversation - only if lesson exists
    conversation = None
    tutor_messages = []
    conversation_id = None
    if current_lesson:
        conversation = TutorConversation.objects.filter(
            user=user,
            lesson=current_lesson
        ).first()
        
        if conversation:
            tutor_messages = conversation.messages.all()[:20]
            conversation_id = conversation.id
    
    context = {
        'enrollment': enrollment,
        'course': course,
        'current_lesson': current_lesson,
        'progress': progress,
        'modules': modules,
        'completed_lesson_ids': completed_lesson_ids,
        'tutor_messages': tutor_messages,
        'conversation_id': conversation_id,
    }
    return render(request, 'student/course_player.html', context)


@login_required
@require_POST
def mark_lesson_complete(request):
    """Mark a lesson as complete (AJAX)"""
    data = json.loads(request.body)
    lesson_id = data.get('lesson_id')
    enrollment_id = data.get('enrollment_id')
    
    enrollment = get_object_or_404(Enrollment, id=enrollment_id, user=request.user)
    lesson = get_object_or_404(Lesson, id=lesson_id)
    
    progress, _ = LessonProgress.objects.get_or_create(
        enrollment=enrollment,
        lesson=lesson
    )
    progress.mark_complete()
    
    # Update user streak
    profile = get_or_create_profile(request.user)
    profile.update_streak()
    
    return JsonResponse({
        'success': True,
        'progress_percentage': enrollment.progress_percentage
    })


@require_POST
def set_currency(request):
    """Set user's preferred currency in session"""
    currency = request.POST.get('currency', 'USD')
    # Validate currency
    valid_currencies = ['USD', 'EUR', 'SAR', 'AED', 'JOD', 'GBP']
    if currency in valid_currencies:
        request.session['selected_currency'] = currency
        request.session.modified = True
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json':
            return JsonResponse({'success': True, 'currency': currency})
        return redirect(request.META.get('HTTP_REFERER', '/'))
    return JsonResponse({'success': False, 'error': 'Invalid currency'})


@require_GET
def get_course_price(request, course_id):
    """Get course price in specified currency (AJAX endpoint)"""
    currency = request.GET.get('currency', 'USD')
    
    # Validate currency
    valid_currencies = ['USD', 'EUR', 'SAR', 'AED', 'JOD', 'GBP']
    if currency not in valid_currencies:
        return JsonResponse({'success': False, 'error': 'Invalid currency'}, status=400)
    
    try:
        course = Course.objects.get(id=course_id, status='published')
    except Course.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Course not found'}, status=404)
    
    # Currency symbol mapping
    currency_symbols = {
        'USD': '$',
        'EUR': '€',
        'SAR': '﷼',
        'AED': 'د.إ',
        'JOD': 'د.ا',
        'GBP': '£',
    }
    
    # Get price in selected currency
    try:
        pricing = CoursePricing.objects.get(course=course, currency=currency)
        price = float(pricing.price)
        currency_code = currency
    except CoursePricing.DoesNotExist:
        # Fallback to course's default currency
        if currency == course.currency:
            price = float(course.price)
            currency_code = course.currency
        else:
            price = float(course.price)
            currency_code = course.currency
    
    return JsonResponse({
        'success': True,
        'currency': currency_code,
        'symbol': currency_symbols.get(currency_code, currency_code),
        'price': price,
        'formatted_price': f"{currency_symbols.get(currency_code, currency_code)} {price:.2f}"
    })


@login_required
@require_POST
def enroll_course(request):
    """Enroll in a course (AJAX)"""
    try:
        # Try to parse JSON from request body
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            # Fallback to form data
            data = request.POST
        
        course_id = data.get('course_id')
        
        if not course_id:
            return JsonResponse({'success': False, 'error': 'Course ID is required'}, status=400)
        
        try:
            course_id = int(course_id)
        except (ValueError, TypeError):
            return JsonResponse({'success': False, 'error': 'Invalid course ID'}, status=400)
        
        # Try to get the course - handle both existence and status
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return JsonResponse({
                'success': False, 
                'error': 'Course not found. The course may have been removed.'
            }, status=404)
        
        # Check if course is published
        if course.status != 'published':
            return JsonResponse({
                'success': False, 
                'error': f'Course is not available for enrollment. Status: {course.get_status_display()}'
            }, status=403)
        
        # Check if already enrolled
        existing_enrollment = Enrollment.objects.filter(user=request.user, course=course).first()
        if existing_enrollment:
            if existing_enrollment.status == 'active':
                return JsonResponse({
                    'success': False, 
                    'error': 'Already enrolled',
                    'enrollment_id': existing_enrollment.id
                })
            else:
                # Reactivate enrollment if it was paused/expired
                existing_enrollment.status = 'active'
                existing_enrollment.save()
                return JsonResponse({
                    'success': True,
                    'enrollment_id': existing_enrollment.id,
                    'redirect_url': f'/student/player/{existing_enrollment.id}/'
                })
        
        # Create enrollment
        enrollment = Enrollment.objects.create(
            user=request.user,
            course=course,
            status='active',
            teacher_notes=''  # Ensure teacher_notes is set to empty string, not None
        )
        
        # Update course stats
        course.enrolled_count += 1
        course.save()
        
        # Determine redirect URL based on course type
        if course.course_type == 'live':
            # For live courses, redirect to live classes page
            redirect_url = '/student/live-classes/'
        else:
            # For recorded/hybrid courses, redirect to course player
            redirect_url = f'/student/player/{enrollment.id}/'
        
        return JsonResponse({
            'success': True,
            'enrollment_id': enrollment.id,
            'redirect_url': redirect_url
        })
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ============================================
# GIFT A COURSE
# ============================================

@login_required
@require_POST
def purchase_gift(request):
    """Purchase a course as a gift"""
    try:
        # Parse request data
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
        
        course_id = data.get('course_id')
        recipient_email = data.get('recipient_email', '').strip().lower()
        sender_name = data.get('sender_name', '').strip()
        gift_message = data.get('gift_message', '').strip()
        
        # Validation
        if not course_id:
            return JsonResponse({'success': False, 'error': 'Course ID is required'}, status=400)
        
        if not recipient_email:
            return JsonResponse({'success': False, 'error': 'Recipient email is required'}, status=400)
        
        # Validate email format
        from django.core.validators import validate_email
        from django.core.exceptions import ValidationError
        try:
            validate_email(recipient_email)
        except ValidationError:
            return JsonResponse({'success': False, 'error': 'Invalid email address'}, status=400)
        
        try:
            course_id = int(course_id)
        except (ValueError, TypeError):
            return JsonResponse({'success': False, 'error': 'Invalid course ID'}, status=400)
        
        # Get course
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return JsonResponse({
                'success': False, 
                'error': 'Course not found'
            }, status=404)
        
        # Check if course is published and eligible for gifting
        if course.status != 'published':
            return JsonResponse({
                'success': False, 
                'error': 'Course is not available for gifting'
            }, status=403)
        
        # Check if course is free (gifts are for paid courses)
        if course.is_free:
            return JsonResponse({
                'success': False, 
                'error': 'Free courses cannot be gifted'
            }, status=400)
        
        # Check if buyer is trying to gift to themselves
        if request.user.email.lower() == recipient_email.lower():
            return JsonResponse({
                'success': False, 
                'error': 'You cannot gift a course to yourself'
            }, status=400)
        
        # Get selected currency from session
        selected_currency = request.session.get('selected_currency', course.currency)
        
        # Get price in selected currency
        try:
            from myApp.models import CoursePricing
            pricing = CoursePricing.objects.get(course=course, currency=selected_currency)
            course_price = pricing.price
            course_currency = selected_currency
        except:
            if selected_currency == course.currency:
                course_price = course.price
                course_currency = course.currency
            else:
                course_price = course.price
                course_currency = course.currency
        
        # Create payment record (in real implementation, this would integrate with payment gateway)
        from myApp.models import Payment
        payment = Payment.objects.create(
            user=request.user,
            course=course,
            amount=course_price,
            currency=course_currency,
            status='completed',  # In production, this would be 'pending' until payment confirms
            payment_method='card',
            completed_at=timezone.now()
        )
        
        # Create gift enrollment
        from myApp.models import GiftEnrollment
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"Creating gift enrollment: buyer={request.user.email}, recipient={recipient_email}, course={course.title}")
        
        gift_enrollment = GiftEnrollment.objects.create(
            buyer=request.user,
            course=course,
            recipient_email=recipient_email,
            recipient_name=data.get('recipient_name', '').strip(),
            sender_name=sender_name or request.user.get_full_name() or request.user.username,
            gift_message=gift_message,
            payment=payment,
            status='pending_claim'
        )
        
        logger.info(f"Gift enrollment created successfully: ID={gift_enrollment.id}, token={gift_enrollment.gift_token}, recipient_email={gift_enrollment.recipient_email}")
        
        # Create GIFT_CREATED timeline event if linked to lead
        try:
            from myApp.models import GiftEnrollmentLeadLink, LeadTimelineEvent
            gift_link = GiftEnrollmentLeadLink.objects.filter(gift_enrollment=gift_enrollment).first()
            if gift_link:
                LeadTimelineEvent.objects.create(
                    lead=gift_link.lead,
                    event_type='GIFT_CREATED',
                    actor=None,  # System
                    summary=f"Gift enrollment for {course.title} purchased by {request.user.get_full_name() or request.user.username}",
                    metadata={'gift_id': gift_enrollment.id, 'buyer_id': request.user.id}
                )
        except Exception:
            pass  # Fail silently if models not yet loaded
        
        # Send gift emails (invite to recipient + confirmation to buyer)
        logger.info(f"Attempting to send gift emails")
        try:
            from myApp.email_utils import send_gift_invite_email, send_gift_confirmation_email
            # Send invite to recipient
            send_gift_invite_email(gift_enrollment, request)
            logger.info(f"Gift invite email sent to {recipient_email}")
            # Send confirmation to buyer
            send_gift_confirmation_email(gift_enrollment, request)
            logger.info(f"Gift confirmation email sent to buyer")
        except Exception as e:
            # Log error but don't fail the purchase
            logger.error(f"Failed to send gift emails: {str(e)}", exc_info=True)
        
        return JsonResponse({
            'success': True,
            'gift_id': gift_enrollment.id,
            'message': 'Your gift has been sent!',
            'redirect_url': f'/student/gift-confirmation/{gift_enrollment.id}/'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Gift purchase error: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def send_gift_email(gift_enrollment, request=None):
    """Send gift notification email to recipient"""
    import logging
    logger = logging.getLogger(__name__)
    
    from django.core.mail import send_mail
    from django.conf import settings
    from django.urls import reverse
    
    # Validate recipient email
    if not gift_enrollment.recipient_email:
        logger.error(f"Gift {gift_enrollment.id}: recipient_email is empty!")
        raise ValueError("Recipient email is required")
    
    logger.info(f"Preparing gift email: gift_id={gift_enrollment.id}, recipient={gift_enrollment.recipient_email}")
    
    # Build claim URL
    if request:
        claim_url = request.build_absolute_uri(
            reverse('claim_gift', kwargs={'gift_token': str(gift_enrollment.gift_token)})
        )
    else:
        # Fallback if request not available (e.g., from admin)
        try:
            from django.contrib.sites.models import Site
            site = Site.objects.get_current()
            domain = site.domain
        except:
            domain = getattr(settings, 'ALLOWED_HOSTS', ['localhost'])[0] if hasattr(settings, 'ALLOWED_HOSTS') and settings.ALLOWED_HOSTS else 'localhost:8000'
        protocol = 'https' if not settings.DEBUG else 'http'
        claim_url = f"{protocol}://{domain}{reverse('claim_gift', kwargs={'gift_token': str(gift_enrollment.gift_token)})}"
    
    logger.info(f"Claim URL generated: {claim_url}")
    
    # Email subject
    subject = f"You've been gifted a course: {gift_enrollment.course.title}"
    
    # Email body (HTML)
    html_message = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #00655F 0%, #82C293 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
            .button {{ display: inline-block; background: #00655F; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
            .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎁 You've Been Gifted a Course!</h1>
            </div>
            <div class="content">
                <p>Hello {gift_enrollment.recipient_name or 'there'},</p>
                
                <p><strong>{gift_enrollment.sender_name}</strong> has gifted you access to:</p>
                
                <h2>{gift_enrollment.course.title}</h2>
                
                {f'<p><em>"{gift_enrollment.gift_message}"</em></p>' if gift_enrollment.gift_message else ''}
                
                <p>To claim your gift and start learning, click the button below:</p>
                
                <div style="text-align: center;">
                    <a href="{claim_url}" class="button">Claim Your Gift</a>
                </div>
                
                <p>Or copy and paste this link into your browser:</p>
                <p style="word-break: break-all; color: #00655F;">{claim_url}</p>
                
                <p>This gift is exclusively for <strong>{gift_enrollment.recipient_email}</strong>.</p>
            </div>
            <div class="footer">
                <p>Happy Learning!<br>The Fluentory Team</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Plain text version
    message = f"""
    You've been gifted a course!
    
    {gift_enrollment.sender_name} has gifted you access to: {gift_enrollment.course.title}
    
    {f'Message: "{gift_enrollment.gift_message}"' if gift_enrollment.gift_message else ''}
    
    Claim your gift: {claim_url}
    
    This gift is exclusively for {gift_enrollment.recipient_email}.
    """
    
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or getattr(settings, 'SERVER_EMAIL', 'noreply@fluentory.com')
    
    # Log email configuration
    logger.info(f"Email config: from_email={from_email}, recipient={gift_enrollment.recipient_email}")
    logger.info(f"Email backend: {getattr(settings, 'EMAIL_BACKEND', 'default')}")
    
    # Check if email backend is configured
    email_backend = getattr(settings, 'EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
    if email_backend == 'django.core.mail.backends.console.EmailBackend':
        logger.warning("Using console email backend - emails will only appear in console/logs")
    
    try:
        result = send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=[gift_enrollment.recipient_email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Email send result: {result} (1 = success, 0 = failure)")
        if result == 0:
            logger.error(f"Email send returned 0 - email was not sent!")
    except Exception as e:
        logger.error(f"Exception during email send: {str(e)}", exc_info=True)
        raise


def claim_gift(request, gift_token):
    """Claim a gift enrollment"""
    from myApp.models import GiftEnrollment
    from django.contrib.auth import login
    from django.shortcuts import redirect, render
    
    try:
        gift = GiftEnrollment.objects.get(gift_token=gift_token)
    except GiftEnrollment.DoesNotExist:
        return render(request, 'student/gift_error.html', {
            'error': 'Gift not found',
            'message': 'The gift link is invalid or has expired.'
        }, status=404)
    
    # Check if gift can be claimed
    can_claim, error = gift.can_be_claimed()
    if not can_claim:
        return render(request, 'student/gift_error.html', {
            'error': 'Gift cannot be claimed',
            'message': error
        })
    
    # If user is logged in
    if request.user.is_authenticated:
        # Check if email matches
        if request.user.email.lower() != gift.recipient_email.lower():
            return render(request, 'student/gift_error.html', {
                'error': 'Email mismatch',
                'message': f'This gift is for {gift.recipient_email}. Please log in with that email address to claim it.'
            })
        
        # User is logged in with matching email - claim the gift
        try:
            enrollment = gift.claim(request.user)
            # Send claim success email
            try:
                from myApp.email_utils import send_claim_success_email
                send_claim_success_email(gift, enrollment, request, notify_buyer=True)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to send claim success email: {str(e)}", exc_info=True)
            return redirect('student_course_player_enrollment', enrollment_id=enrollment.id)
        except ValueError as e:
            return render(request, 'student/gift_error.html', {
                'error': 'Claim failed',
                'message': str(e)
            })
    
    # User is not logged in - show claim page with signup/login options
    return render(request, 'student/claim_gift.html', {
        'gift': gift,
        'recipient_email': gift.recipient_email
    })


@login_required
@require_POST
def claim_gift_authenticated(request):
    """Claim gift after user is authenticated (AJAX)"""
    try:
        gift_token = request.POST.get('gift_token') or json.loads(request.body).get('gift_token')
        
        if not gift_token:
            return JsonResponse({'success': False, 'error': 'Gift token is required'}, status=400)
        
        from myApp.models import GiftEnrollment
        try:
            gift = GiftEnrollment.objects.get(gift_token=gift_token)
        except GiftEnrollment.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Gift not found'}, status=404)
        
        # Check if gift can be claimed
        can_claim, error = gift.can_be_claimed()
        if not can_claim:
            return JsonResponse({'success': False, 'error': error}, status=400)
        
        # Verify email matches
        if request.user.email.lower() != gift.recipient_email.lower():
            return JsonResponse({
                'success': False, 
                'error': f'This gift is for {gift.recipient_email}. Please log in with that email address.'
            }, status=403)
        
        # Claim the gift
        try:
            enrollment = gift.claim(request.user)
            
            # Send claim success email
            try:
                from myApp.email_utils import send_claim_success_email
                send_claim_success_email(gift, enrollment, request, notify_buyer=True)
            except Exception as e:
                logger.error(f"Failed to send claim success email: {str(e)}", exc_info=True)
            
            # Determine redirect URL
            if gift.course.course_type == 'live':
                redirect_url = '/student/live-classes/'
            else:
                redirect_url = f'/student/player/{enrollment.id}/'
            
            return JsonResponse({
                'success': True,
                'message': 'Gift claimed successfully!',
                'redirect_url': redirect_url
            })
        except ValueError as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
            
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Gift claim error: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def gift_confirmation(request, gift_id):
    """Show gift purchase confirmation page"""
    from myApp.models import GiftEnrollment
    from django.core.exceptions import PermissionDenied
    
    try:
        gift = GiftEnrollment.objects.get(id=gift_id)
    except GiftEnrollment.DoesNotExist:
        return render(request, 'student/gift_error.html', {
            'error': 'Gift not found'
        }, status=404)
    
    # Only buyer can view confirmation
    if gift.buyer != request.user:
        raise PermissionDenied
    
    return render(request, 'student/gift_confirmation.html', {
        'gift': gift
    })


# ============================================
# AI TUTOR
# ============================================

@login_required
@require_POST
def ai_tutor_chat(request):
    """AI Tutor chat endpoint - uses course-specific AI settings"""
    data = json.loads(request.body)
    message = data.get('message')
    lesson_id = data.get('lesson_id')
    conversation_id = data.get('conversation_id')
    
    user = request.user
    lesson = get_object_or_404(Lesson, id=lesson_id) if lesson_id else None
    course = lesson.module.course if lesson else None
    
    # Get or create conversation
    if conversation_id:
        conversation = get_object_or_404(TutorConversation, id=conversation_id, user=user)
        if not course:
            course = conversation.course
    else:
        conversation = TutorConversation.objects.create(
            user=user,
            lesson=lesson,
            course=course,
            title=f"Chat about {lesson.title}" if lesson else "General Chat"
        )
    
    # Get AI Tutor settings for the course (or use defaults)
    ai_settings = None
    if course and hasattr(course, 'ai_tutor_settings'):
        ai_settings = course.ai_tutor_settings
    elif course:
        # Create default settings if they don't exist
        ai_settings = AITutorSettings.objects.create(course=course)
    
    # Use default values if no settings exist
    model = ai_settings.model if ai_settings else "gpt-4o-mini"
    temperature = ai_settings.temperature if ai_settings else 0.7
    max_tokens = ai_settings.max_tokens if ai_settings else 500
    max_history = ai_settings.max_conversation_history if ai_settings else 10
    
    # Save user message
    TutorMessage.objects.create(
        conversation=conversation,
        role='user',
        content=message
    )
    
    # Get conversation history (limited by settings)
    history = conversation.messages.filter(role__in=['user', 'assistant']).order_by('created_at')[:max_history]
    
    # Build context based on settings
    context_text = ""
    if course and ai_settings:
        if ai_settings.include_course_context:
            context_text += f"\nCourse: {course.title}\n"
            if course.description:
                context_text += f"Course Description: {course.description[:500]}\n"
        
        if lesson and ai_settings.include_lesson_context:
            context_text += f"\nModule: {lesson.module.title}\n"
            context_text += f"Lesson: {lesson.title}\n"
            if lesson.description:
                context_text += f"Lesson Description: {lesson.description[:500]}\n"
            if lesson.text_content:
                context_text += f"Lesson Content: {lesson.text_content[:1000]}\n"
            elif lesson.video_url:
                context_text += "Lesson Type: Video lesson\n"
    elif lesson:
        # Fallback context if no settings
        context_text = f"""
        Course: {lesson.module.course.title}
        Module: {lesson.module.title}
        Lesson: {lesson.title}
        Lesson Content: {lesson.text_content[:1000] if lesson.text_content else 'Video lesson'}
        """
    
    # Get system prompt from settings
    if ai_settings:
        system_prompt = ai_settings.get_system_prompt(lesson=lesson)
        if context_text:
            system_prompt += f"\n\nCurrent context: {context_text}"
    else:
        # Default system prompt
        system_prompt = f"""You are a helpful AI tutor for Fluentory, an online learning platform.
        Be encouraging, clear, and concise. Help students understand concepts from their lessons.
        Current context: {context_text}
        """
    
    # Build messages for OpenAI
    messages_for_ai = [
        {
            "role": "system",
            "content": system_prompt
        }
    ]
    
    for msg in history:
        messages_for_ai.append({
            "role": msg.role if msg.role != 'assistant' else 'assistant',
            "content": msg.content
        })
    
    # Call OpenAI with configured settings
    try:
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=model,
            messages=messages_for_ai,
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        ai_response = response.choices[0].message.content
        tokens_used = response.usage.total_tokens
        
    except Exception as e:
        ai_response = "I'm sorry, I'm having trouble connecting right now. Please try again in a moment."
        tokens_used = 0
    
    # Save AI response
    TutorMessage.objects.create(
        conversation=conversation,
        role='assistant',
        content=ai_response,
        tokens_used=tokens_used
    )
    
    return JsonResponse({
        'success': True,
        'response': ai_response,
        'conversation_id': conversation.id
    })


# ============================================
# QUIZ
# ============================================

@login_required
def take_quiz(request, quiz_id):
    """Take a quiz"""
    quiz = get_object_or_404(Quiz, id=quiz_id)
    user = request.user
    
    # Check attempts
    attempts_count = QuizAttempt.objects.filter(user=user, quiz=quiz).count()
    if quiz.max_attempts and attempts_count >= quiz.max_attempts:
        messages.error(request, 'You have reached the maximum number of attempts for this quiz.')
        return redirect('student_learning')
    
    questions = quiz.questions.prefetch_related('answers').order_by('order')
    
    if request.method == 'POST':
        # Process submission
        answers = {}
        score = 0
        total_points = 0
        
        for question in questions:
            answer_value = request.POST.get(f'question_{question.id}')
            if answer_value:
                answers[str(question.id)] = answer_value
                
                # Handle different question types
                if question.question_type == 'short_answer':
                    # For short answer, compare text (case-insensitive, trimmed)
                    correct_answers = question.answers.filter(is_correct=True)
                    student_answer = answer_value.strip().lower()
                    for correct in correct_answers:
                        if correct.answer_text.strip().lower() == student_answer:
                            score += question.points
                            break
                else:
                    # For multiple choice and true/false, compare answer IDs
                    correct = question.answers.filter(is_correct=True).first()
                    if correct and str(correct.id) == answer_value:
                        score += question.points
            total_points += question.points
        
        percentage = (score / total_points * 100) if total_points > 0 else 0
        passed = percentage >= quiz.passing_score
        
        # Create attempt record
        attempt = QuizAttempt.objects.create(
            user=user,
            quiz=quiz,
            score=percentage,
            passed=passed,
            answers=answers,
            completed_at=timezone.now()
        )
        
        # Update quiz stats
        quiz.total_attempts += 1
        all_attempts = QuizAttempt.objects.filter(quiz=quiz)
        quiz.pass_rate = all_attempts.filter(passed=True).count() / all_attempts.count() * 100
        quiz.save()
        
        if passed:
            messages.success(request, f'Congratulations! You passed with {percentage:.0f}%!')
        else:
            messages.warning(request, f'You scored {percentage:.0f}%. You need {quiz.passing_score}% to pass.')
        
        return redirect('quiz_result', attempt_id=attempt.id)
    
    context = {
        'quiz': quiz,
        'questions': questions,
        'attempts_remaining': quiz.max_attempts - attempts_count if quiz.max_attempts else None,
    }
    return render(request, 'student/quiz.html', context)


@login_required
def quiz_result(request, attempt_id):
    """Quiz result page"""
    attempt = get_object_or_404(QuizAttempt, id=attempt_id, user=request.user)
    quiz = attempt.quiz
    
    # Get questions with answers
    questions = quiz.questions.prefetch_related('answers').order_by('order')
    
    # Prepare question results
    question_results = []
    for question in questions:
        question_id_str = str(question.id)
        student_answer_id = attempt.answers.get(question_id_str)
        
        # Find correct answer
        correct_answer = question.answers.filter(is_correct=True).first()
        
        # Check if student's answer is correct
        is_correct = False
        student_answer_obj = None
        
        if student_answer_id:
            if question.question_type == 'short_answer':
                # For short answer, compare text (case-insensitive)
                student_answer_text = str(student_answer_id).strip().lower()
                if correct_answer:
                    correct_answer_text = correct_answer.answer_text.strip().lower()
                    if correct_answer_text == student_answer_text:
                        is_correct = True
                student_answer_obj = {'text': str(student_answer_id), 'id': None}
            else:
                # For MCQ/True-False, compare IDs
                try:
                    answer_id_int = int(student_answer_id)
                    student_answer_obj = question.answers.filter(id=answer_id_int).first()
                    if correct_answer and str(correct_answer.id) == str(student_answer_id):
                        is_correct = True
                except (ValueError, TypeError):
                    student_answer_obj = None
        
        question_results.append({
            'question': question,
            'student_answer': student_answer_obj,
            'correct_answer': correct_answer,
            'is_correct': is_correct,
        })
    
    # Check attempts remaining
    attempts_count = QuizAttempt.objects.filter(user=request.user, quiz=quiz).count()
    attempts_remaining = None
    if quiz.max_attempts:
        attempts_remaining = max(0, quiz.max_attempts - attempts_count)
    
    context = {
        'attempt': attempt,
        'quiz': quiz,
        'question_results': question_results,
        'attempts_remaining': attempts_remaining,
    }
    return render(request, 'student/quiz_result.html', context)


# ============================================
# CERTIFICATE VERIFICATION
# ============================================

def verify_certificate(request, certificate_id):
    """Public certificate verification page"""
    try:
        certificate = Certificate.objects.get(certificate_id=certificate_id)
        certificate.verified_count += 1
        certificate.save()
        
        context = {
            'certificate': certificate,
            'verified': True,
        }
    except Certificate.DoesNotExist:
        context = {
            'certificate': None,
            'verified': False,
        }
    
    return render(request, 'verify_certificate.html', context)


# ============================================
# ADMIN VIEWS
# ============================================

@login_required
@role_required(['admin'])
def admin_overview(request):
    """Admin dashboard"""
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
            'url': reverse('dashboard:users') + '?status=stuck'
        })
    
    if failed_payments > 0:
        action_items.append({
            'type': 'warning',
            'title': f'{failed_payments} payment failures in queue',
            'description': 'Requires manual review',
            'icon': 'fa-credit-card',
            'color': 'orange',
            'url': reverse('dashboard:payments') + '?status=failed'
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
    return render(request, 'admin/overview.html', context)


@login_required
@role_required(['admin'])
def admin_users(request):
    """Admin user management"""
    users = User.objects.select_related('profile').order_by('-date_joined')
    
    # Filters
    role = request.GET.get('role')
    status = request.GET.get('status')
    
    if role:
        users = users.filter(profile__role=role)
    if status == 'active':
        users = users.filter(is_active=True)
    elif status == 'inactive':
        users = users.filter(is_active=False)
    
    paginator = Paginator(users, 20)
    page = request.GET.get('page', 1)
    users = paginator.get_page(page)
    
    context = {
        'users': users,
    }
    return render(request, 'admin/users.html', context)


@login_required
@role_required(['admin'])
def admin_courses(request):
    """Admin course management"""
    courses = Course.objects.select_related('category', 'instructor').order_by('-created_at')
    
    paginator = Paginator(courses, 20)
    page = request.GET.get('page', 1)
    courses = paginator.get_page(page)
    
    context = {
        'courses': courses,
    }
    return render(request, 'admin/courses.html', context)


@login_required
@role_required(['admin'])
def admin_payments(request):
    """Admin payment management"""
    payments = Payment.objects.select_related('user', 'course').order_by('-created_at')
    
    status = request.GET.get('status')
    if status:
        payments = payments.filter(status=status)
    
    paginator = Paginator(payments, 20)
    page = request.GET.get('page', 1)
    payments = paginator.get_page(page)
    
    context = {
        'payments': payments,
    }
    return render(request, 'admin/payments.html', context)


# ============================================
# MEDIA MANAGEMENT VIEWS
# ============================================

@login_required
@role_required(['admin'])
def admin_media(request):
    """Admin media management - list all media"""
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
    return render(request, 'admin/media.html', context)


@login_required
@role_required(['admin'])
def admin_media_add(request):
    """Add new media - supports file upload or Cloudinary URL"""
    if request.method == 'POST':
        try:
            # Check if uploading from URL (Cloudinary)
            image_url = request.POST.get('image_url', '').strip()
            
            if image_url:
                # Upload from URL to Cloudinary
                try:
                    import requests
                    from django.core.files.base import ContentFile
                    from django.core.files.images import ImageFile
                    from .cloudinary_helper import upload_image_from_url
                    
                    folder = f"media/{request.POST.get('category', 'general')}"
                    result = upload_image_from_url(image_url, folder=folder)
                    
                    if result['success']:
                        # Download the image and create a file object for Django
                        img_response = requests.get(result['secure_url'], timeout=30)
                        img_response.raise_for_status()
                        
                        # Create Media object
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
                        
                        # Save the image file (will upload to Cloudinary via storage backend)
                        file_extension = result.get('format', 'jpg')
                        img_file = ContentFile(img_response.content)
                        media.file.save(f"{media.title}.{file_extension}", img_file, save=False)
                        media.save()
                        
                        messages.success(request, f'Media "{media.title}" uploaded from Cloudinary successfully!')
                    else:
                        messages.error(request, f'Error uploading from URL: {result.get("error")}')
                        return redirect('admin_media_add')
                except Exception as e:
                    messages.error(request, f'Error processing Cloudinary URL: {str(e)}')
                    return redirect('admin_media_add')
            else:
                # Regular file upload (will use Cloudinary storage automatically)
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
            
            return redirect('admin_media')
        except Exception as e:
            messages.error(request, f'Error uploading media: {str(e)}')
    
    context = {
        'categories': Media.CATEGORY_CHOICES,
        'media_types': Media.MEDIA_TYPE_CHOICES,
    }
    return render(request, 'admin/media_add.html', context)


@login_required
@role_required(['admin'])
def admin_media_edit(request, media_id):
    """Edit media details"""
    media = get_object_or_404(Media, id=media_id)
    
    if request.method == 'POST':
        try:
            media.title = request.POST.get('title', media.title)
            media.description = request.POST.get('description', media.description)
            media.media_type = request.POST.get('media_type', media.media_type)
            media.category = request.POST.get('category', media.category)
            media.alt_text = request.POST.get('alt_text', media.alt_text)
            media.tags = request.POST.get('tags', media.tags)
            
            # Handle file replacement
            if request.FILES.get('file'):
                media.file = request.FILES.get('file')
            
            media.save()
            messages.success(request, f'Media "{media.title}" updated successfully!')
            return redirect('admin_media')
        except Exception as e:
            messages.error(request, f'Error updating media: {str(e)}')
    
    context = {
        'media': media,
        'categories': Media.CATEGORY_CHOICES,
        'media_types': Media.MEDIA_TYPE_CHOICES,
    }
    return render(request, 'admin/media_edit.html', context)


@login_required
@role_required(['admin'])
@require_POST
def admin_media_delete(request, media_id):
    """Delete media"""
    media = get_object_or_404(Media, id=media_id)
    title = media.title
    
    try:
        # Delete the file from storage
        if media.file:
            media.file.delete()
        media.delete()
        messages.success(request, f'Media "{title}" deleted successfully!')
    except Exception as e:
        messages.error(request, f'Error deleting media: {str(e)}')
    
    return redirect('admin_media')


@login_required
@role_required(['admin'])
def admin_site_images(request):
    """Manage images for all site sections"""
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
            return redirect('admin_site_images')
        except Exception as e:
            messages.error(request, f'Error updating images: {str(e)}')
    
    # Get all media for reference
    all_media = Media.objects.filter(media_type='image').order_by('-created_at')[:20]
    
    context = {
        'settings': settings,
        'all_media': all_media,
    }
    return render(request, 'admin/site_images.html', context)


# ============================================
# TEACHER VIEWS
# ============================================

@login_required
def teacher_dashboard(request):
    """Teacher dashboard"""
    user = request.user
    profile = get_or_create_profile(user)
    
    # Allow admin/superuser to access teacher views automatically (godlike admin)
    is_superuser_or_admin = user.is_superuser or user.is_staff or profile.role == 'admin'
    preview_role = request.session.get('preview_role')
    is_previewing_teacher = preview_role == 'teacher' and is_superuser_or_admin
    
    # Superusers/admins automatically have teacher access
    if is_superuser_or_admin and not hasattr(user, 'teacher_profile'):
        # For superusers/admins without teacher profile, use mock teacher for template compatibility
        class MockTeacher:
            def __init__(self, user):
                self.user = user
                self.is_approved = True
                self.is_online = False
                self.last_seen = None
                self.id = None
            
            def save(self):
                pass  # No-op for mock object
            
            def __getattr__(self, name):
                # Return None or default values for any other attributes
                return None
        
        teacher = MockTeacher(user)
    elif hasattr(user, 'teacher_profile'):
        teacher = user.teacher_profile
        # Check if teacher is approved
        if not teacher.is_approved and not is_superuser_or_admin:
            message_app(request, messages.INFO, 'Your teacher account is under review. We\'ll notify you once approved.')
            return render(request, 'auth/teacher_pending.html')
    else:
        # Regular user - check if they're a teacher
        if profile.role != 'instructor':
            messages.error(request, 'You do not have permission to access the teacher dashboard.')
            return redirect('student_home')
        # Create teacher profile if doesn't exist
        teacher, _ = Teacher.objects.get_or_create(
            user=user,
            defaults={'permission_level': 'standard', 'is_approved': True}
        )
        if not teacher.is_approved:
            teacher.is_approved = True
            teacher.save()
    
    # Update online status (only for real teacher objects)
    if hasattr(teacher, 'save') and teacher.id is not None:
        teacher.is_online = True
        teacher.last_seen = timezone.now()
        teacher.save()
    
    # Get assigned courses (for superusers/admins without teacher profile, show all courses)
    if is_superuser_or_admin and teacher.id is None:
        # Admin preview mode: show all courses
        assigned_courses = CourseTeacher.objects.none()  # Empty queryset
        course_ids = list(Course.objects.filter(status__in=['published', 'draft']).values_list('id', flat=True))
        total_courses = Course.objects.filter(status__in=['published', 'draft']).count()
        total_students = Enrollment.objects.filter(course_id__in=course_ids).values('user').distinct().count() if course_ids else 0
        week_ago = timezone.now() - timezone.timedelta(days=7)
        active_students = LessonProgress.objects.filter(
            enrollment__course_id__in=course_ids,
            started_at__gte=week_ago
        ).values('enrollment__user').distinct().count() if course_ids else 0
        upcoming_classes = LiveClassSession.objects.filter(
            status='scheduled',
            scheduled_start__gte=timezone.now()
        ).select_related('course').order_by('scheduled_start')[:5]
        recent_announcements = CourseAnnouncement.objects.all().select_related('course').order_by('-created_at')[:5]
        unread_messages_count = 0
    else:
        # Normal teacher mode
        assigned_courses = CourseTeacher.objects.filter(teacher=teacher).select_related('course')
        course_ids = [ct.course.id for ct in assigned_courses]
        
        # KPIs
        total_students = Enrollment.objects.filter(course_id__in=course_ids).values('user').distinct().count()
        
        # Active students (last 7 days)
        week_ago = timezone.now() - timezone.timedelta(days=7)
        active_students = LessonProgress.objects.filter(
            enrollment__course_id__in=course_ids,
            started_at__gte=week_ago
        ).values('enrollment__user').distinct().count()
        
        # Total courses
        total_courses = len(course_ids)
        
        # Upcoming live classes
        upcoming_classes = LiveClassSession.objects.filter(
            teacher=teacher,
            status='scheduled',
            scheduled_start__gte=timezone.now()
        ).select_related('course').order_by('scheduled_start')[:5]
        
        # Recent announcements
        recent_announcements = CourseAnnouncement.objects.filter(
            teacher=teacher
        ).select_related('course').order_by('-created_at')[:5]
        
        # Unread messages
        unread_messages_count = StudentMessage.objects.filter(
            teacher=teacher,
            is_read=False
        ).count()
    
    # Live activity feed data (for AJAX)
    # This will be loaded via API endpoint
    
    context = {
        'teacher': teacher,
        'total_students': total_students,
        'active_students': active_students,
        'total_courses': total_courses,
        'upcoming_classes': upcoming_classes,
        'recent_announcements': recent_announcements,
        'unread_messages_count': unread_messages_count,
        'assigned_courses': assigned_courses,
    }
    return render(request, 'teacher/dashboard.html', context)


@login_required
@teacher_approved_required
def teacher_courses(request):
    """My Courses - view all assigned courses"""
    user = request.user
    profile = get_or_create_profile(user)
    
    # Allow superusers/admins to access automatically
    is_superuser_or_admin = user.is_superuser or user.is_staff or profile.role == 'admin'
    
    if is_superuser_or_admin and not hasattr(user, 'teacher_profile'):
        # For superusers/admins, show all courses
        course_assignments = CourseTeacher.objects.all().select_related('course')
        context = {
            'courses': [ca.course for ca in course_assignments],
            'course_assignments': course_assignments,
        }
        return render(request, 'teacher/courses.html', context)
    
    # Check if user is teacher
    if not hasattr(user, 'teacher_profile'):
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('student_home')
    teacher = user.teacher_profile
    
    # Get assigned courses
    course_assignments = CourseTeacher.objects.filter(teacher=teacher).select_related('course')
    
    # Filters
    status = request.GET.get('status')
    search = request.GET.get('search')
    
    courses = [ca.course for ca in course_assignments]
    
    if status:
        courses = [c for c in courses if c.status == status]
    if search:
        courses = [c for c in courses if search.lower() in c.title.lower() or search.lower() in c.description.lower()]
    
    context = {
        'courses': courses,
        'course_assignments': course_assignments,
    }
    return render(request, 'teacher/courses.html', context)


@login_required
@teacher_approved_required
def teacher_course_create(request):
    """Create new course (only for teachers with 'full' permission)"""
    user = request.user
    teacher, _ = Teacher.objects.get_or_create(
        user=user,
        defaults={'permission_level': 'standard', 'is_approved': True}
    )
    
    # Double-check approval (shouldn't reach here if not approved due to decorator, but safety check)
    if not teacher.is_approved and not (user.is_superuser or user.is_staff):
        message_app(request, messages.INFO, 'Your teacher account is under review. We\'ll notify you once approved.')
        return render(request, 'auth/teacher_pending.html')
    
    if request.method == 'POST':
        # Create course
        course = Course.objects.create(
            title=request.POST.get('title'),
            slug=request.POST.get('slug'),
            description=request.POST.get('description'),
            short_description=request.POST.get('short_description', ''),
            outcome=request.POST.get('outcome', ''),
            category_id=request.POST.get('category'),
            level=request.POST.get('level', 'beginner'),
            course_type=request.POST.get('course_type', 'recorded'),
            instructor=user,
            price=float(request.POST.get('price', 0)),
            is_free=request.POST.get('is_free') == 'on',
            status='draft'
        )
        
        # Assign teacher with full permissions
        CourseTeacher.objects.create(
            course=course,
            teacher=teacher,
            permission_level='full',
            can_create_live_classes=True,
            can_manage_schedule=True,
            assigned_by=user
        )
        
        message_app(request, messages.SUCCESS, f'Course "{course.title}" created successfully!')
        return redirect('teacher_course_edit', course_id=course.id)
    
    categories = Category.objects.all()
    context = {
        'categories': categories,
    }
    return render(request, 'teacher/course_create.html', context)


@login_required
def teacher_course_edit(request, course_id):
    """Edit course"""
    course = get_object_or_404(Course, id=course_id)
    user = request.user
    teacher, _ = Teacher.objects.get_or_create(
        user=user,
        defaults={'permission_level': 'standard'}
    )
    
    # Check permissions
    assignment = CourseTeacher.objects.filter(teacher=teacher, course=course).first()
    if not assignment or assignment.permission_level == 'view_only':
        message_app(request, messages.ERROR, 'You do not have permission to edit this course.')
        return redirect('teacher_courses')
    
    if request.method == 'POST':
        old_status = course.status
        course.title = request.POST.get('title', course.title)
        course.description = request.POST.get('description', course.description)
        course.short_description = request.POST.get('short_description', course.short_description)
        course.outcome = request.POST.get('outcome', course.outcome)
        course.category_id = request.POST.get('category') or course.category_id
        course.level = request.POST.get('level', course.level)
        course.course_type = request.POST.get('course_type', course.course_type)
        course.price = float(request.POST.get('price', course.price))
        course.is_free = request.POST.get('is_free') == 'on'
        new_status = request.POST.get('status', course.status)
        course.status = new_status
        
        # Set published_at when status changes to 'published'
        if new_status == 'published' and old_status != 'published' and not course.published_at:
            from django.utils import timezone
            course.published_at = timezone.now()
        
        if request.FILES.get('thumbnail'):
            course.thumbnail = request.FILES.get('thumbnail')
        
        course.save()
        message_app(request, messages.SUCCESS, 'Course updated successfully!')
        return redirect('teacher_course_edit', course_id=course.id)
    
    categories = Category.objects.all()
    modules = course.modules.prefetch_related('lessons').order_by('order')
    
    context = {
        'course': course,
        'categories': categories,
        'modules': modules,
        'assignment': assignment,
    }
    return render(request, 'teacher/course_edit.html', context)


@login_required
def teacher_lessons(request, course_id):
    """Manage lessons for a course"""
    course = get_object_or_404(Course, id=course_id)
    user = request.user
    teacher, _ = Teacher.objects.get_or_create(
        user=user,
        defaults={'permission_level': 'standard'}
    )
    
    # Check permissions
    assignment = CourseTeacher.objects.filter(teacher=teacher, course=course).first()
    if not assignment or assignment.permission_level == 'view_only':
        messages.error(request, 'You do not have permission to manage lessons.')
        return redirect('teacher_courses')
    
    modules = course.modules.prefetch_related('lessons').order_by('order')
    module_id = request.GET.get('module')
    
    context = {
        'course': course,
        'modules': modules,
        'selected_module_id': int(module_id) if module_id else None,
    }
    return render(request, 'teacher/lessons.html', context)


@login_required
def teacher_lesson_create(request, course_id):
    """Create new lesson"""
    course = get_object_or_404(Course, id=course_id)
    user = request.user
    teacher, _ = Teacher.objects.get_or_create(
        user=user,
        defaults={'permission_level': 'standard'}
    )
    
    # Check permissions
    assignment = CourseTeacher.objects.filter(teacher=teacher, course=course).first()
    if not assignment or assignment.permission_level == 'view_only':
        messages.error(request, 'You do not have permission to create lessons.')
        return redirect('teacher_courses')
    
    if request.method == 'POST':
        module_id = request.POST.get('module', '').strip()
        
        # Validate module_id is provided
        if not module_id:
            message_app(request, messages.ERROR, 'Please select a module for this lesson.')
            return redirect('teacher_lesson_create', course_id=course.id)
        
        # Validate module exists and belongs to course
        try:
            module = Module.objects.get(id=module_id, course=course)
        except Module.DoesNotExist:
            message_app(request, messages.ERROR, 'The selected module does not exist or does not belong to this course.')
            return redirect('teacher_lesson_create', course_id=course.id)
        
        # Validate required fields
        title = request.POST.get('title', '').strip()
        if not title:
            message_app(request, messages.ERROR, 'Lesson title is required.')
            return redirect('teacher_lesson_create', course_id=course.id)
        
        lesson = Lesson.objects.create(
            module=module,
            title=title,
            description=request.POST.get('description', ''),
            content_type=request.POST.get('content_type', 'video'),
            video_url=request.POST.get('video_url', ''),
            text_content=request.POST.get('text_content', ''),
            order=int(request.POST.get('order', 0)),
            estimated_minutes=int(request.POST.get('estimated_minutes', 10))
        )
        
        message_app(request, messages.SUCCESS, 'Lesson created successfully!')
        return redirect('teacher_lessons', course_id=course.id)
    
    modules = course.modules.all().order_by('order')
    context = {
        'course': course,
        'modules': modules,
    }
    return render(request, 'teacher/lesson_create.html', context)


@login_required
def teacher_lesson_edit(request, course_id, lesson_id):
    """Edit lesson"""
    course = get_object_or_404(Course, id=course_id)
    lesson = get_object_or_404(Lesson, id=lesson_id, module__course=course)
    user = request.user
    teacher, _ = Teacher.objects.get_or_create(
        user=user,
        defaults={'permission_level': 'standard'}
    )
    
    # Check permissions
    assignment = CourseTeacher.objects.filter(teacher=teacher, course=course).first()
    if not assignment or assignment.permission_level == 'view_only':
        messages.error(request, 'You do not have permission to edit lessons.')
        return redirect('teacher_courses')
    
    if request.method == 'POST':
        lesson.title = request.POST.get('title', lesson.title)
        lesson.description = request.POST.get('description', lesson.description)
        lesson.content_type = request.POST.get('content_type', lesson.content_type)
        lesson.video_url = request.POST.get('video_url', lesson.video_url)
        lesson.text_content = request.POST.get('text_content', lesson.text_content)
        lesson.order = int(request.POST.get('order', lesson.order))
        lesson.estimated_minutes = int(request.POST.get('estimated_minutes', lesson.estimated_minutes))
        
        module_id = request.POST.get('module')
        if module_id:
            lesson.module = get_object_or_404(Module, id=module_id, course=course)
        
        lesson.save()
        messages.success(request, 'Lesson updated successfully!')
        return redirect('teacher_lessons', course_id=course.id)
    
    modules = course.modules.all()
    context = {
        'course': course,
        'lesson': lesson,
        'modules': modules,
    }
    return render(request, 'teacher/lesson_edit.html', context)


@login_required
@require_POST
def teacher_lesson_delete(request, course_id, lesson_id):
    """Delete lesson"""
    course = get_object_or_404(Course, id=course_id)
    lesson = get_object_or_404(Lesson, id=lesson_id, module__course=course)
    user = request.user
    teacher, _ = Teacher.objects.get_or_create(
        user=user,
        defaults={'permission_level': 'standard'}
    )
    
    # Check permissions
    assignment = CourseTeacher.objects.filter(teacher=teacher, course=course).first()
    if not assignment or assignment.permission_level == 'view_only':
        messages.error(request, 'You do not have permission to delete lessons.')
        return redirect('teacher_courses')
    
    lesson.delete()
    messages.success(request, 'Lesson deleted successfully!')
    return redirect('teacher_lessons', course_id=course.id)


@login_required
def teacher_quizzes(request, course_id):
    """Manage quizzes for a course"""
    course = get_object_or_404(Course, id=course_id)
    user = request.user
    teacher, _ = Teacher.objects.get_or_create(
        user=user,
        defaults={'permission_level': 'standard'}
    )
    
    # Check permissions
    assignment = CourseTeacher.objects.filter(teacher=teacher, course=course).first()
    if not assignment or assignment.permission_level == 'view_only':
        messages.error(request, 'You do not have permission to manage quizzes.')
        return redirect('teacher_courses')
    
    quizzes = course.quizzes.all().order_by('-created_at')
    quiz_type = request.GET.get('type')
    
    if quiz_type:
        quizzes = quizzes.filter(quiz_type=quiz_type)
    
    context = {
        'course': course,
        'quizzes': quizzes,
        'selected_type': quiz_type,
    }
    return render(request, 'teacher/quizzes.html', context)


@login_required
def teacher_quiz_create(request, course_id):
    """Create new quiz"""
    course = get_object_or_404(Course, id=course_id)
    user = request.user
    teacher, _ = Teacher.objects.get_or_create(
        user=user,
        defaults={'permission_level': 'standard'}
    )
    
    # Check permissions
    assignment = CourseTeacher.objects.filter(teacher=teacher, course=course).first()
    if not assignment or assignment.permission_level == 'view_only':
        messages.error(request, 'You do not have permission to create quizzes.')
        return redirect('teacher_courses')
    
    if request.method == 'POST':
        quiz = Quiz.objects.create(
            course=course,
            title=request.POST.get('title'),
            description=request.POST.get('description', ''),
            quiz_type=request.POST.get('quiz_type', 'module'),
            passing_score=int(request.POST.get('passing_score', 70)),
            time_limit_minutes=int(request.POST.get('time_limit_minutes', 0)) or None,
            max_attempts=int(request.POST.get('max_attempts', 3))
        )
        
        messages.success(request, 'Quiz created successfully!')
        return redirect('teacher_quiz_questions', course_id=course.id, quiz_id=quiz.id)
    
    context = {
        'course': course,
    }
    return render(request, 'teacher/quiz_create.html', context)


@login_required
def teacher_quiz_edit(request, course_id, quiz_id):
    """Edit quiz"""
    course = get_object_or_404(Course, id=course_id)
    quiz = get_object_or_404(Quiz, id=quiz_id, course=course)
    user = request.user
    teacher, _ = Teacher.objects.get_or_create(
        user=user,
        defaults={'permission_level': 'standard'}
    )
    
    # Check permissions
    assignment = CourseTeacher.objects.filter(teacher=teacher, course=course).first()
    if not assignment or assignment.permission_level == 'view_only':
        messages.error(request, 'You do not have permission to edit quizzes.')
        return redirect('teacher_courses')
    
    if request.method == 'POST':
        quiz.title = request.POST.get('title', quiz.title)
        quiz.description = request.POST.get('description', quiz.description)
        quiz.quiz_type = request.POST.get('quiz_type', quiz.quiz_type)
        quiz.passing_score = int(request.POST.get('passing_score', quiz.passing_score))
        quiz.time_limit_minutes = int(request.POST.get('time_limit_minutes', 0)) or None
        quiz.max_attempts = int(request.POST.get('max_attempts', quiz.max_attempts))
        quiz.save()
        
        messages.success(request, 'Quiz updated successfully!')
        return redirect('teacher_quiz_edit', course_id=course.id, quiz_id=quiz.id)
    
    context = {
        'course': course,
        'quiz': quiz,
    }
    return render(request, 'teacher/quiz_edit.html', context)


@login_required
@require_POST
def teacher_quiz_delete(request, course_id, quiz_id):
    """Delete quiz"""
    course = get_object_or_404(Course, id=course_id)
    quiz = get_object_or_404(Quiz, id=quiz_id, course=course)
    user = request.user
    teacher, _ = Teacher.objects.get_or_create(
        user=user,
        defaults={'permission_level': 'standard'}
    )
    
    # Check permissions
    assignment = CourseTeacher.objects.filter(teacher=teacher, course=course).first()
    if not assignment or assignment.permission_level == 'view_only':
        messages.error(request, 'You do not have permission to delete quizzes.')
        return redirect('teacher_courses')
    
    # Delete quiz (cascade will automatically delete all related questions and answers)
    quiz.delete()
    messages.success(request, 'Quiz deleted successfully.')
    return redirect('teacher_quizzes', course_id=course.id)


@login_required
def teacher_quiz_questions(request, course_id, quiz_id):
    """Manage quiz questions"""
    course = get_object_or_404(Course, id=course_id)
    quiz = get_object_or_404(Quiz, id=quiz_id, course=course)
    user = request.user
    teacher, _ = Teacher.objects.get_or_create(
        user=user,
        defaults={'permission_level': 'standard'}
    )
    
    # Check permissions
    assignment = CourseTeacher.objects.filter(teacher=teacher, course=course).first()
    if not assignment or assignment.permission_level == 'view_only':
        messages.error(request, 'You do not have permission to manage quiz questions.')
        return redirect('teacher_courses')
    
    questions = quiz.questions.prefetch_related('answers').order_by('order')
    
    if request.method == 'POST':
        question_type = request.POST.get('question_type', 'multiple_choice')
        question_text = request.POST.get('question_text', '').strip()
        
        # Validation
        if not question_text:
            messages.error(request, 'Question text is required.')
            return redirect('teacher_quiz_questions', course_id=course.id, quiz_id=quiz.id)
        
        # Add new question
        question = Question.objects.create(
            quiz=quiz,
            question_text=question_text,
            question_type=question_type,
            explanation=request.POST.get('explanation', ''),
            points=int(request.POST.get('points', 1)),
            order=int(request.POST.get('order', questions.count()))
        )
        
        # Handle answers based on question type
        if question_type == 'short_answer':
            # Short Answer: Create a single answer with the correct answer text
            correct_answer_text = request.POST.get('correct_answer_text', '').strip()
            if not correct_answer_text:
                question.delete()  # Rollback question creation
                messages.error(request, 'Correct answer text is required for short answer questions.')
                return redirect('teacher_quiz_questions', course_id=course.id, quiz_id=quiz.id)
            
            Answer.objects.create(
                question=question,
                answer_text=correct_answer_text,
                is_correct=True,
                order=0
            )
        else:
            # Multiple Choice or True/False: Handle answer options
            answers_data = request.POST.getlist('answers[]')
            is_correct_data = request.POST.getlist('is_correct[]')
            
            if not answers_data or len([a for a in answers_data if a.strip()]) == 0:
                question.delete()  # Rollback question creation
                messages.error(request, 'At least one answer option is required.')
                return redirect('teacher_quiz_questions', course_id=course.id, quiz_id=quiz.id)
            
            # Validate correct answer selection
            if not is_correct_data:
                question.delete()  # Rollback question creation
                messages.error(request, 'Please select the correct answer.')
                return redirect('teacher_quiz_questions', course_id=course.id, quiz_id=quiz.id)
            
            # Validate minimum answers for MCQ
            if question_type == 'multiple_choice':
                filled_answers = [a for a in answers_data if a.strip()]
                if len(filled_answers) < 2:
                    question.delete()  # Rollback question creation
                    messages.error(request, 'Multiple choice questions require at least 2 answer options.')
                    return redirect('teacher_quiz_questions', course_id=course.id, quiz_id=quiz.id)
            
            # Validate True/False has exactly 2 answers and exactly one correct answer
            if question_type == 'true_false':
                filled_answers = [a for a in answers_data if a.strip()]
                if len(filled_answers) != 2:
                    question.delete()  # Rollback question creation
                    messages.error(request, 'True/False questions must have exactly 2 answer options.')
                    return redirect('teacher_quiz_questions', course_id=course.id, quiz_id=quiz.id)
                
                # Validate exactly one correct answer for True/False
                if len(is_correct_data) != 1:
                    question.delete()  # Rollback question creation
                    messages.error(request, 'True/False questions must have exactly one correct answer selected.')
                    return redirect('teacher_quiz_questions', course_id=course.id, quiz_id=quiz.id)
            
            # Validate MCQ has exactly one correct answer
            if question_type == 'multiple_choice':
                if len(is_correct_data) != 1:
                    question.delete()  # Rollback question creation
                    messages.error(request, 'Multiple choice questions must have exactly one correct answer selected.')
                    return redirect('teacher_quiz_questions', course_id=course.id, quiz_id=quiz.id)
            
            # Create answers
            for i, answer_text in enumerate(answers_data):
                if answer_text.strip():
                    is_correct = str(i) in is_correct_data
                    Answer.objects.create(
                        question=question,
                        answer_text=answer_text,
                        is_correct=is_correct,
                        order=i
                    )
        
        message_app(request, messages.SUCCESS, 'Question added successfully!')
        return redirect('teacher_quiz_questions', course_id=course.id, quiz_id=quiz.id)
    
    context = {
        'course': course,
        'quiz': quiz,
        'questions': questions,
    }
    return render(request, 'teacher/quiz_questions.html', context)


@login_required
def teacher_my_students(request):
    """View all students across assigned courses"""
    user = request.user
    teacher, _ = Teacher.objects.get_or_create(
        user=user,
        defaults={'permission_level': 'standard'}
    )
    
    # Get assigned courses
    assigned_courses = CourseTeacher.objects.filter(teacher=teacher).select_related('course')
    course_ids = [ca.course.id for ca in assigned_courses]
    
    # Get all enrollments
    enrollments = Enrollment.objects.filter(course_id__in=course_ids).select_related('user', 'course').distinct()
    
    # Filters
    course_filter = request.GET.get('course')
    search = request.GET.get('search')
    
    if course_filter:
        enrollments = enrollments.filter(course_id=course_filter)
    if search:
        enrollments = enrollments.filter(
            Q(user__username__icontains=search) |
            Q(user__email__icontains=search) |
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search)
        )
    
    # Get unique students
    students_dict = {}
    for enrollment in enrollments:
        student_id = enrollment.user.id
        if student_id not in students_dict:
            students_dict[student_id] = {
                'user': enrollment.user,
                'enrollments': [],
                'total_progress': 0,
                'courses_count': 0
            }
        students_dict[student_id]['enrollments'].append(enrollment)
        students_dict[student_id]['total_progress'] += enrollment.progress_percentage
        students_dict[student_id]['courses_count'] += 1
    
    students = list(students_dict.values())
    for student_data in students:
        student_data['avg_progress'] = student_data['total_progress'] / student_data['courses_count'] if student_data['courses_count'] > 0 else 0
    
    courses = [ca.course for ca in assigned_courses]
    
    context = {
        'students': students,
        'courses': courses,
        'selected_course_id': int(course_filter) if course_filter else None,
        'search_query': search,
    }
    return render(request, 'teacher/my_students.html', context)


@login_required
def teacher_students(request, course_id):
    """View students for a specific course"""
    course = get_object_or_404(Course, id=course_id)
    user = request.user
    teacher, _ = Teacher.objects.get_or_create(
        user=user,
        defaults={'permission_level': 'standard'}
    )
    
    # Check permissions
    assignment = CourseTeacher.objects.filter(teacher=teacher, course=course).first()
    if not assignment:
        messages.error(request, 'You do not have access to this course.')
        return redirect('teacher_courses')
    
    enrollments = Enrollment.objects.filter(course=course).select_related('user')
    
    # Filters
    status = request.GET.get('status')
    search = request.GET.get('search')
    
    if status:
        enrollments = enrollments.filter(status=status)
    if search:
        enrollments = enrollments.filter(
            Q(user__username__icontains=search) |
            Q(user__email__icontains=search)
        )
    
    context = {
        'course': course,
        'enrollments': enrollments,
        'selected_status': status,
        'search_query': search,
    }
    return render(request, 'teacher/course_students.html', context)


@login_required
def teacher_schedule(request):
    """Live class schedule"""
    user = request.user
    
    # Get or create teacher profile - handle gracefully if creation fails
    try:
        teacher_instance, created = Teacher.objects.get_or_create(
            user=user,
            defaults={'permission_level': 'standard'}
        )
    except Exception as e:
        # If we can't create/get teacher profile, show error and redirect
        messages.error(request, 'Unable to access teacher profile. Please contact support if this issue persists.')
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error getting/creating Teacher for user {user.id}: {e}")
        return redirect('teacher_dashboard')
    
    # Ensure teacher instance is valid
    if not teacher_instance or not hasattr(teacher_instance, 'id'):
        messages.error(request, 'Teacher profile not found. Please contact support.')
        return redirect('teacher_dashboard')
    
    live_classes = LiveClassSession.objects.filter(teacher=teacher_instance).select_related('course').order_by('-scheduled_start')
    
    # Filters
    status = request.GET.get('status')
    if status:
        live_classes = live_classes.filter(status=status)
    
    if request.method == 'POST':
        # Create new live class
        course_id = request.POST.get('course')
        course = get_object_or_404(Course, id=course_id)
        
        # Check if teacher has permission
        assignment = CourseTeacher.objects.filter(teacher=teacher_instance, course=course).first()
        if not assignment or not assignment.can_create_live_classes:
            message_app(request, messages.ERROR, 'You do not have permission to create live classes for this course.')
            return redirect('teacher_schedule')
        
        # Warn if course is not published - students won't be able to enroll
        if course.status != 'published':
            message_app(request, messages.WARNING, f'Warning: This course is in "{course.get_status_display()}" status. Students will not be able to see or enroll in live classes for unpublished courses. Consider publishing the course first.')
        
        # Validate required fields
        scheduled_start_str = request.POST.get('scheduled_start')
        if not scheduled_start_str:
            messages.error(request, 'Start time is required.')
            return redirect('teacher_schedule')
        
        try:
            duration_minutes = int(request.POST.get('duration_minutes', 60))
            if duration_minutes < 1:
                messages.error(request, 'Duration must be at least 1 minute.')
                return redirect('teacher_schedule')
        except (ValueError, TypeError):
            messages.error(request, 'Invalid duration value.')
            return redirect('teacher_schedule')
        
        # Parse and convert start time to timezone-aware datetime (UTC)
        from datetime import datetime, timedelta
        import pytz
        
        try:
            if 'T' in scheduled_start_str:
                # ISO format: '2024-01-01T10:00' or '2024-01-01T10:00Z' or '2024-01-01T10:00+00:00'
                if scheduled_start_str.endswith('Z'):
                    scheduled_start_str = scheduled_start_str[:-1] + '+00:00'
                scheduled_start = datetime.fromisoformat(scheduled_start_str.replace('Z', '+00:00'))
            else:
                # Format: '2024-01-01 10:00:00'
                scheduled_start = datetime.strptime(scheduled_start_str, '%Y-%m-%d %H:%M:%S')
            
            # Ensure timezone-aware (if naive, assume it's in teacher's timezone or UTC)
            if scheduled_start.tzinfo is None:
                # Try to get teacher's timezone, default to UTC
                teacher_tz = getattr(teacher_instance, 'timezone', 'UTC') or 'UTC'
                try:
                    tz = pytz.timezone(teacher_tz)
                except:
                    tz = pytz.UTC
                scheduled_start = tz.localize(scheduled_start)
            
            # Convert to UTC for storage
            if scheduled_start.tzinfo != pytz.UTC:
                scheduled_start_utc = scheduled_start.astimezone(pytz.UTC)
            else:
                scheduled_start_utc = scheduled_start
            
            # Compute end time: start + duration
            scheduled_end_utc = scheduled_start_utc + timedelta(minutes=duration_minutes)
            
            # Convert to naive datetime for scheduled_start/scheduled_end (legacy fields may expect naive)
            scheduled_start_naive = scheduled_start_utc.replace(tzinfo=None) if scheduled_start_utc.tzinfo else scheduled_start_utc
            scheduled_end_naive = scheduled_end_utc.replace(tzinfo=None) if scheduled_end_utc.tzinfo else scheduled_end_utc
            
            # VALIDATION: Ensure scheduled_end_naive is computed correctly
            if scheduled_end_naive is None:
                messages.error(request, 'Failed to compute session end time. Please try again.')
                return redirect('teacher_schedule')
            
            # Double-check: recompute if needed
            if scheduled_start_naive and duration_minutes:
                expected_end = scheduled_start_naive + timedelta(minutes=duration_minutes)
                if abs((scheduled_end_naive - expected_end).total_seconds()) > 1:  # Allow 1 second tolerance
                    scheduled_end_naive = expected_end
            
        except (ValueError, TypeError) as e:
            messages.error(request, f'Invalid date/time format: {str(e)}')
            return redirect('teacher_schedule')
        except Exception as e:
            messages.error(request, f'Error processing session time: {str(e)}')
            return redirect('teacher_schedule')
        
        # Get seat capacity and waitlist settings for Group Session
        try:
            total_seats = int(request.POST.get('total_seats', 10))
            if total_seats < 1:
                messages.error(request, 'Total seats must be at least 1.')
                return redirect('teacher_schedule')
        except (ValueError, TypeError):
            messages.error(request, 'Invalid total seats value.')
            return redirect('teacher_schedule')
        
        enable_waitlist = request.POST.get('enable_waitlist') == 'on'
        # CRITICAL: meeting_url column (db_column) in DB is NOT NULL, so always provide a value (empty string if not provided)
        # Get meeting link from form, fallback to empty string - NEVER allow None
        # Use or '' to ensure we always have a string, never None
        meeting_link = (request.POST.get('meeting_link') or '').strip()
        if not meeting_link:
            meeting_link = (request.POST.get('zoom_link') or '').strip()
        if not meeting_link:
            meeting_link = (request.POST.get('google_meet_link') or '').strip()
        # Final guarantee - ensure it's always a string, never None (defensive programming)
        meeting_link = str(meeting_link) if meeting_link else ''
        
        # Get teacher's timezone for snapshot
        teacher_tz = getattr(teacher_instance, 'timezone', 'UTC') or 'UTC'
        
        # Create session with all required fields
        # CRITICAL: scheduled_end, meeting_link, seats_taken, and reminder_sent MUST be set here before INSERT to avoid IntegrityError
        live_class = LiveClassSession.objects.create(
            course=course,
            teacher=teacher_instance,
            title=request.POST.get('title'),
            description=request.POST.get('description', ''),
            scheduled_start=scheduled_start_naive,
            scheduled_end=scheduled_end_naive,  # REQUIRED: Set before INSERT
            start_at_utc=scheduled_start_utc,
            end_at_utc=scheduled_end_utc,
            duration_minutes=duration_minutes,
            timezone_snapshot=teacher_tz,
            meeting_link=meeting_link,  # REQUIRED: meeting_url column (db_column) is NOT NULL - must be string, never None
            zoom_link=request.POST.get('zoom_link', ''),
            google_meet_link=request.POST.get('google_meet_link', ''),
            meeting_id=request.POST.get('meeting_id', ''),
            meeting_password=request.POST.get('meeting_password', ''),
            meeting_passcode=request.POST.get('meeting_password', ''),  # Also set new field
            total_seats=total_seats,
            seats_taken=0,  # REQUIRED: current_attendees column is NOT NULL, initialize to 0 for new sessions
            enable_waitlist=enable_waitlist,
            reminder_sent=False,  # REQUIRED: reminder_sent column is NOT NULL, initialize to False for new sessions
            max_attendees=total_seats,  # Sync for backwards compatibility
            capacity=total_seats,  # Phase 2: Set capacity
        )
        
        message_app(request, messages.SUCCESS, 'Live class scheduled successfully!')
        return redirect('teacher_schedule')
    
    # Get courses teacher can create live classes for
    # Include courses where teacher is assigned with permission, OR courses the teacher created themselves
    assigned_courses = CourseTeacher.objects.filter(
        teacher=teacher_instance,
        can_create_live_classes=True
    ).select_related('course')
    
    # Also include courses created by this teacher (they should have full control)
    teacher_created_courses = Course.objects.filter(
        instructor=user,
        course_type__in=['live', 'hybrid']
    ).exclude(
        id__in=assigned_courses.values_list('course_id', flat=True)
    )
    
    # Add teacher-created courses to the queryset (create CourseTeacher entries if needed)
    # Only create if teacher object is valid and saved
    if teacher_instance.id:
        for course in teacher_created_courses:
            try:
                # Verify teacher exists in database before creating relationship
                # Use the module-level Teacher import (already imported at top of file)
                if not Teacher.objects.filter(id=teacher_instance.id).exists():
                    continue
                    
                assignment, created = CourseTeacher.objects.get_or_create(
                    course=course,
                    teacher=teacher_instance,
                    defaults={
                        'permission_level': 'full',
                        'can_create_live_classes': True,
                        'can_manage_schedule': True,
                        'assigned_by': user
                    }
                )
                if not assignment.can_create_live_classes:
                    assignment.can_create_live_classes = True
                    assignment.save()
            except Exception as e:
                # Log error but don't break the page - database schema issue
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error creating CourseTeacher for course {course.id}, teacher {teacher_instance.id if hasattr(teacher_instance, 'id') else 'N/A'}: {e}")
                continue
    
    # Refresh the queryset to include newly created assignments
    assigned_courses = CourseTeacher.objects.filter(
        teacher=teacher_instance,
        can_create_live_classes=True
    ).select_related('course').distinct()
    
    context = {
        'live_classes': live_classes,
        'assigned_courses': assigned_courses,
        'selected_status': status,
    }
    return render(request, 'teacher/schedule.html', context)


@login_required
def teacher_profile_edit(request):
    """Edit teacher profile with photo upload"""
    user = request.user
    
    # Get or create teacher profile
    try:
        teacher, _ = Teacher.objects.get_or_create(
            user=user,
            defaults={'permission_level': 'standard'}
        )
    except Exception:
        messages.error(request, 'Unable to access teacher profile.')
        return redirect('teacher_dashboard')
    
    if request.method == 'POST':
        # Update basic fields
        teacher.bio = request.POST.get('bio', teacher.bio)
        teacher.specialization = request.POST.get('specialization', teacher.specialization)
        years_exp = request.POST.get('years_experience', '0')
        try:
            teacher.years_experience = int(years_exp) if years_exp else 0
        except ValueError:
            teacher.years_experience = 0
        
        # Update user fields
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        user.save()
        
        # Handle photo upload
        if 'photo' in request.FILES:
            photo_file = request.FILES['photo']
            
            # Validate file type
            if not photo_file.content_type.startswith('image/'):
                messages.error(request, 'Please upload a valid image file.')
            else:
                # Import utility function
                from myApp.utils.cloudinary_utils import upload_image_to_cloudinary, delete_image_from_cloudinary
                
                # Delete old photo from Cloudinary if exists
                if teacher.photo_url:
                    # Extract public_id from URL if possible
                    # Cloudinary URLs format: https://res.cloudinary.com/{cloud_name}/image/upload/{folder}/{public_id}.{format}
                    try:
                        # Extract the full path after /image/upload/
                        url_parts = teacher.photo_url.split('/image/upload/')
                        if len(url_parts) > 1:
                            # Get the path with version and transformations removed
                            path_part = url_parts[1].split('.')[0]  # Remove extension
                            # Remove version prefix if present (v1234567890/)
                            if '/' in path_part:
                                path_parts = path_part.split('/')
                                # Reconstruct public_id (should include folder)
                                old_public_id = '/'.join(path_parts)
                                if old_public_id:
                                    delete_image_from_cloudinary(old_public_id)
                    except Exception as e:
                        print(f"Could not delete old photo: {e}")  # Ignore deletion errors
                
                # Upload new photo to Cloudinary (converts to WebP automatically)
                upload_result = upload_image_to_cloudinary(
                    photo_file,
                    folder='teachers/profiles',
                    public_id=f'teacher_{teacher.id}_{user.username}',
                    should_convert_to_webp=True
                )
                
                if upload_result and upload_result.get('web_url'):
                    # Use web_url (optimized) for profile photo
                    teacher.photo_url = upload_result['web_url']
                    messages.success(request, 'Profile photo updated successfully!')
                else:
                    error_msg = 'Failed to upload photo. '
                    if upload_result is None:
                        error_msg += 'Cloudinary upload failed. Please check your Cloudinary account status.'
                    else:
                        error_msg += 'Please try again.'
                    messages.error(request, error_msg)
        
        teacher.save()
        messages.success(request, 'Profile updated successfully!')
        return redirect('teacher_profile_edit')
    
    context = {
        'teacher': teacher,
        'user': user,
    }
    return render(request, 'teacher/profile_edit.html', context)


@login_required
def teacher_live_class_detail(request, session_id):
    """Live class details page with enrolled students"""
    user = request.user
    
    # Get or create teacher profile
    try:
        teacher_instance, _ = Teacher.objects.get_or_create(
            user=user,
            defaults={'permission_level': 'standard'}
        )
    except Exception:
        messages.error(request, 'Unable to access teacher profile.')
        return redirect('teacher_dashboard')
    
    # Get the session
    session = get_object_or_404(
        LiveClassSession, 
        id=session_id,
        teacher=teacher_instance
    )
    
    # Get all bookings for this session
    bookings = LiveClassBooking.objects.filter(
        session=session,
        booking_type='group_session'
    ).select_related('student_user', 'student_user__profile').order_by('created_at')
    
    # Separate by status
    confirmed_bookings = bookings.filter(status__in=['confirmed', 'attended'])
    pending_bookings = bookings.filter(status='pending')
    cancelled_bookings = bookings.filter(status='cancelled')
    
    # Get waitlist entries
    waitlist_entries = []
    try:
        waitlist_entries = SessionWaitlist.objects.filter(
            session=session,
            status='waiting'
        ).select_related('student_user', 'student_user__profile').order_by('created_at')
    except Exception:
        pass
    
    # Statistics
    total_bookings = confirmed_bookings.count()
    total_seats = session.total_seats
    remaining_seats = session.remaining_seats
    attendance_count = bookings.filter(status='attended').count()
    
    context = {
        'session': session,
        'bookings': confirmed_bookings,
        'pending_bookings': pending_bookings,
        'cancelled_bookings': cancelled_bookings,
        'waitlist_entries': waitlist_entries,
        'total_bookings': total_bookings,
        'total_seats': total_seats,
        'remaining_seats': remaining_seats,
        'attendance_count': attendance_count,
    }
    return render(request, 'teacher/live_class_detail.html', context)


@login_required
def teacher_live_classes(request, course_id):
    """Live classes for a specific course"""
    course = get_object_or_404(Course, id=course_id)
    user = request.user
    teacher, _ = Teacher.objects.get_or_create(
        user=user,
        defaults={'permission_level': 'standard'}
    )
    
    # Check permissions
    assignment = CourseTeacher.objects.filter(teacher=teacher, course=course).first()
    if not assignment:
        messages.error(request, 'You do not have access to this course.')
        return redirect('teacher_courses')
    
    live_classes = LiveClassSession.objects.filter(
        teacher=teacher,
        course=course
    ).order_by('-scheduled_start')
    
    context = {
        'course': course,
        'live_classes': live_classes,
    }
    return render(request, 'teacher/course_live_classes.html', context)


@login_required
def teacher_announcements(request, course_id):
    """Course announcements"""
    course = get_object_or_404(Course, id=course_id)
    user = request.user
    teacher, _ = Teacher.objects.get_or_create(
        user=user,
        defaults={'permission_level': 'standard'}
    )
    
    # Check permissions
    assignment = CourseTeacher.objects.filter(teacher=teacher, course=course).first()
    if not assignment:
        messages.error(request, 'You do not have access to this course.')
        return redirect('teacher_courses')
    
    announcements = CourseAnnouncement.objects.filter(
        teacher=teacher,
        course=course
    ).order_by('-is_pinned', '-created_at')
    
    if request.method == 'POST':
        announcement = CourseAnnouncement.objects.create(
            course=course,
            teacher=teacher,
            title=request.POST.get('title'),
            message=request.POST.get('message'),
            is_pinned=request.POST.get('is_pinned') == 'on',
            send_to_all_students=request.POST.get('send_to_all_students') == 'on'
        )
        
        # Send notifications to enrolled students if requested
        if announcement.send_to_all_students:
            enrollments = Enrollment.objects.filter(course=course, status='active')
            for enrollment in enrollments:
                Notification.objects.create(
                    user=enrollment.user,
                    notification_type='announcement',
                    title=announcement.title,
                    message=announcement.message,
                    action_url=f'/student/courses/{course.slug}/'
                )
        
        messages.success(request, 'Announcement created successfully!')
        return redirect('teacher_announcements', course_id=course.id)
    
    context = {
        'course': course,
        'announcements': announcements,
    }
    return render(request, 'teacher/announcements.html', context)


@login_required
def teacher_ai_settings(request, course_id):
    """Configure AI Tutor settings for a course"""
    course = get_object_or_404(Course, id=course_id)
    user = request.user
    teacher, _ = Teacher.objects.get_or_create(
        user=user,
        defaults={'permission_level': 'standard'}
    )
    
    # Check permissions - only teachers with edit or full access can configure AI settings
    assignment = CourseTeacher.objects.filter(teacher=teacher, course=course).first()
    if not assignment or assignment.permission_level == 'view_only':
        messages.error(request, 'You do not have permission to configure AI settings for this course.')
        return redirect('teacher_courses')
    
    # Get or create AI settings
    ai_settings, created = AITutorSettings.objects.get_or_create(course=course)
    
    if request.method == 'POST':
        # Update AI settings
        ai_settings.model = request.POST.get('model', ai_settings.model)
        ai_settings.temperature = float(request.POST.get('temperature', ai_settings.temperature))
        ai_settings.max_tokens = int(request.POST.get('max_tokens', ai_settings.max_tokens))
        ai_settings.personality = request.POST.get('personality', ai_settings.personality)
        ai_settings.custom_system_prompt = request.POST.get('custom_system_prompt', '')
        ai_settings.custom_instructions = request.POST.get('custom_instructions', '')
        ai_settings.include_lesson_context = request.POST.get('include_lesson_context') == 'on'
        ai_settings.include_course_context = request.POST.get('include_course_context') == 'on'
        ai_settings.max_conversation_history = int(request.POST.get('max_conversation_history', ai_settings.max_conversation_history))
        ai_settings.updated_by = user
        ai_settings.save()
        
        messages.success(request, 'AI Tutor settings updated successfully!')
        return redirect('teacher_ai_settings', course_id=course.id)
    
    context = {
        'course': course,
        'ai_settings': ai_settings,
        'assignment': assignment,
    }
    return render(request, 'teacher/ai_settings.html', context)


@login_required
@require_GET
def api_teacher_activity_feed(request):
    """Live activity feed for teacher dashboard (AJAX)"""
    user = request.user
    teacher, _ = Teacher.objects.get_or_create(
        user=user,
        defaults={'permission_level': 'standard'}
    )
    
    # Get assigned courses
    assigned_courses = CourseTeacher.objects.filter(teacher=teacher).select_related('course')
    course_ids = [ca.course.id for ca in assigned_courses]
    
    activities = []
    
    # Recent lesson completions (last 24 hours)
    yesterday = timezone.now() - timezone.timedelta(hours=24)
    recent_completions = LessonProgress.objects.filter(
        enrollment__course_id__in=course_ids,
        completed_at__gte=yesterday
    ).select_related('enrollment__user', 'lesson').order_by('-completed_at')[:10]
    
    for completion in recent_completions:
        activities.append({
            'type': 'lesson_completion',
            'user': completion.enrollment.user.get_full_name() or completion.enrollment.user.username,
            'action': f'completed lesson "{completion.lesson.title}"',
            'course': completion.enrollment.course.title,
            'time': completion.completed_at.isoformat(),
        })
    
    # Recent quiz attempts
    recent_attempts = QuizAttempt.objects.filter(
        quiz__course_id__in=course_ids,
        completed_at__gte=yesterday
    ).select_related('user', 'quiz').order_by('-completed_at')[:10]
    
    for attempt in recent_attempts:
        activities.append({
            'type': 'quiz_attempt',
            'user': attempt.user.get_full_name() or attempt.user.username,
            'action': f'attempted quiz "{attempt.quiz.title}" ({attempt.score:.0f}%)',
            'course': attempt.quiz.course.title if attempt.quiz.course else '',
            'time': attempt.completed_at.isoformat() if attempt.completed_at else '',
        })
    
    # Recent certificates
    recent_certificates = Certificate.objects.filter(
        course_id__in=course_ids,
        issued_at__gte=yesterday
    ).select_related('user').order_by('-issued_at')[:10]
    
    for cert in recent_certificates:
        activities.append({
            'type': 'certificate',
            'user': cert.user.get_full_name() or cert.user.username,
            'action': f'earned certificate for "{cert.course.title}"',
            'course': cert.course.title,
            'time': cert.issued_at.isoformat(),
        })
    
    # New enrollments
    new_enrollments = Enrollment.objects.filter(
        course_id__in=course_ids,
        enrolled_at__gte=yesterday
    ).select_related('user').order_by('-enrolled_at')[:10]
    
    for enrollment in new_enrollments:
        activities.append({
            'type': 'enrollment',
            'user': enrollment.user.get_full_name() or enrollment.user.username,
            'action': f'enrolled in "{enrollment.course.title}"',
            'course': enrollment.course.title,
            'time': enrollment.enrolled_at.isoformat(),
        })
    
    # Sort by time (most recent first)
    activities.sort(key=lambda x: x['time'], reverse=True)
    
    return JsonResponse({'activities': activities[:20]})


# ============================================
# PARTNER VIEWS
# ============================================

@login_required
@role_required(['partner'])
def partner_overview(request):
    """Partner dashboard"""
    user = request.user
    profile = get_or_create_profile(user)
    
    # Superusers/admins automatically have partner access
    is_superuser_or_admin = user.is_superuser or user.is_staff or profile.role == 'admin'
    preview_role = request.session.get('preview_role')
    is_admin_preview = is_superuser_or_admin and (preview_role == 'partner' or (not preview_role and is_superuser_or_admin))
    
    if is_admin_preview:
        # For admins previewing, show platform-wide stats (read-only demo)
        partner = None
        cohorts = Cohort.objects.none()
        
        # Platform-wide stats (read-only for preview)
        total_students = User.objects.filter(profile__role='student').count()
        active_learners = Enrollment.objects.filter(status='active').count()
        
        # Platform completion rate
        total_enrollments = Enrollment.objects.count()
        completed_enrollments = Enrollment.objects.filter(status='completed').count()
        completion_rate = (completed_enrollments / total_enrollments * 100) if total_enrollments > 0 else 0
        
        certificates_earned = Certificate.objects.count()
        total_revenue = Payment.objects.filter(status='completed').aggregate(total=Sum('amount'))['total'] or 0
        commission = 0
        
        # Create a mock partner object for template compatibility
        class MockPartner:
            company_name = "Platform Overview (Preview)"
            is_active = True
        
        partner = MockPartner()
        is_preview_mode = True
        
    else:
        # Actual partner view
        try:
            partner = Partner.objects.get(user=user)
        except Partner.DoesNotExist:
            messages.error(request, 'You do not have a partner account. Please contact an administrator.')
            return redirect('home')
        
        # Cohorts
        cohorts = partner.cohorts.all()
        
        # Stats
        total_students = CohortMembership.objects.filter(cohort__partner=partner).count()
        
        # Active learners
        active_learners = Enrollment.objects.filter(
            partner=partner,
            status='active'
        ).count()
        
        # Completion rate
        partner_enrollments = Enrollment.objects.filter(partner=partner)
        completed = partner_enrollments.filter(status='completed').count()
        total = partner_enrollments.count()
        completion_rate = (completed / total * 100) if total > 0 else 0
        
        # Certificates earned
        certificates_earned = Certificate.objects.filter(
            enrollment__partner=partner
        ).count()
        
        # Revenue (if commission-based)
        total_revenue = Payment.objects.filter(
            partner=partner,
            status='completed'
        ).aggregate(total=Sum('amount'))['total'] or 0
        commission = total_revenue * partner.commission_rate
        is_preview_mode = False
    
    context = {
        'partner': partner,
        'cohorts': cohorts,
        'total_students': total_students,
        'active_learners': active_learners,
        'completion_rate': completion_rate,
        'certificates_earned': certificates_earned,
        'total_revenue': total_revenue,
        'commission': commission,
        'is_preview_mode': is_preview_mode,
    }
    return render(request, 'partner/overview.html', context)


@login_required
@role_required(['partner'])
def partner_cohorts(request):
    """Partner cohort management"""
    user = request.user
    profile = get_or_create_profile(user)
    
    # Superusers/admins automatically have partner access
    is_superuser_or_admin = user.is_superuser or user.is_staff or profile.role == 'admin'
    preview_role = request.session.get('preview_role')
    is_admin_preview = is_superuser_or_admin and (preview_role == 'partner' or (not preview_role and is_superuser_or_admin))
    
    if is_admin_preview:
        # For admins previewing, show all cohorts (read-only)
        cohorts = Cohort.objects.prefetch_related('courses', 'students').order_by('-start_date')
        
        class MockPartner:
            company_name = "Platform Overview (Preview)"
        
        partner = MockPartner()
    else:
        try:
            partner = Partner.objects.get(user=user)
            cohorts = partner.cohorts.prefetch_related('courses', 'students').order_by('-start_date')
        except Partner.DoesNotExist:
            messages.error(request, 'You do not have a partner account.')
            return redirect('home')
    
    context = {
        'partner': partner,
        'cohorts': cohorts,
        'is_preview_mode': is_admin_preview,
    }
    return render(request, 'partner/cohorts.html', context)


@login_required
@role_required(['partner'])
def partner_programs(request):
    """Partner programs and bundles management"""
    user = request.user
    profile = get_or_create_profile(user)
    
    # Superusers/admins automatically have partner access
    is_superuser_or_admin = user.is_superuser or user.is_staff or profile.role == 'admin'
    preview_role = request.session.get('preview_role')
    is_admin_preview = is_superuser_or_admin and (preview_role == 'partner' or (not preview_role and is_superuser_or_admin))
    
    if is_admin_preview:
        # Show all courses as programs (read-only)
        programs = Course.objects.filter(status='published').prefetch_related('cohorts').order_by('-created_at')
        
        class MockPartner:
            company_name = "Platform Overview (Preview)"
        
        partner = MockPartner()
    else:
        try:
            partner = Partner.objects.get(user=user)
            # Get courses associated with partner's cohorts
            programs = Course.objects.filter(
                cohorts__partner=partner
            ).distinct().prefetch_related('cohorts').order_by('-created_at')
        except Partner.DoesNotExist:
            messages.error(request, 'You do not have a partner account.')
            return redirect('home')
    
    context = {
        'partner': partner,
        'programs': programs,
        'is_preview_mode': is_admin_preview,
    }
    return render(request, 'partner/programs.html', context)


@login_required
@role_required(['partner'])
def partner_referrals(request):
    """Partner referrals and sales tracking"""
    user = request.user
    profile = get_or_create_profile(user)
    
    # Superusers/admins automatically have partner access
    is_superuser_or_admin = user.is_superuser or user.is_staff or profile.role == 'admin'
    preview_role = request.session.get('preview_role')
    is_admin_preview = is_superuser_or_admin and (preview_role == 'partner' or (not preview_role and is_superuser_or_admin))
    
    if is_admin_preview:
        # Show all payments (read-only)
        payments_list = list(Payment.objects.filter(status='completed').select_related('user', 'course').order_by('-created_at')[:50])
        total_revenue = Payment.objects.filter(status='completed').aggregate(total=Sum('amount'))['total'] or 0
        total_count = Payment.objects.filter(status='completed').count()
        
        class MockPartner:
            company_name = "Platform Overview (Preview)"
            commission_rate = 0.2
        
        partner = MockPartner()
        commission = total_revenue * partner.commission_rate
        
        # Add commission amount to each payment
        for payment in payments_list:
            payment.commission_amount = float(payment.amount) * partner.commission_rate
    else:
        try:
            partner = Partner.objects.get(user=user)
            # Get payments associated with partner
            payments_list = list(Payment.objects.filter(
                partner=partner,
                status='completed'
            ).select_related('user', 'course').order_by('-created_at')[:50])
            
            total_revenue = Payment.objects.filter(
                partner=partner,
                status='completed'
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            total_count = Payment.objects.filter(
                partner=partner,
                status='completed'
            ).count()
            
            commission = total_revenue * partner.commission_rate
            
            # Add commission amount to each payment
            for payment in payments_list:
                payment.commission_amount = float(payment.amount) * partner.commission_rate
        except Partner.DoesNotExist:
            messages.error(request, 'You do not have a partner account.')
            return redirect('home')
    
    # Calculate average sale
    avg_sale = (float(total_revenue) / total_count) if total_count > 0 else 0
    
    context = {
        'partner': partner,
        'payments': payments_list,
        'total_revenue': total_revenue,
        'total_count': total_count,
        'avg_sale': avg_sale,
        'commission': commission,
        'is_preview_mode': is_admin_preview,
    }
    return render(request, 'partner/referrals.html', context)


@login_required
@role_required(['partner'])
def partner_marketing(request):
    """Partner marketing assets"""
    user = request.user
    profile = get_or_create_profile(user)
    
    # Superusers/admins automatically have partner access
    is_superuser_or_admin = user.is_superuser or user.is_staff or profile.role == 'admin'
    preview_role = request.session.get('preview_role')
    is_admin_preview = is_superuser_or_admin and (preview_role == 'partner' or (not preview_role and is_superuser_or_admin))
    
    if is_admin_preview:
        # Show all cohorts with promo codes (read-only)
        cohorts = Cohort.objects.filter(promo_code__isnull=False).exclude(promo_code='').order_by('-created_at')
        
        class MockPartner:
            company_name = "Platform Overview (Preview)"
        
        partner = MockPartner()
    else:
        try:
            partner = Partner.objects.get(user=user)
            # Get cohorts with promo codes
            cohorts = partner.cohorts.filter(
                promo_code__isnull=False
            ).exclude(promo_code='').order_by('-created_at')
        except Partner.DoesNotExist:
            messages.error(request, 'You do not have a partner account.')
            return redirect('home')
    
    context = {
        'partner': partner,
        'cohorts': cohorts,
        'is_preview_mode': is_admin_preview,
    }
    return render(request, 'partner/marketing.html', context)


@login_required
@role_required(['partner'])
def partner_reports(request):
    """Partner reports and analytics"""
    user = request.user
    profile = get_or_create_profile(user)
    
    # Superusers/admins automatically have partner access
    is_superuser_or_admin = user.is_superuser or user.is_staff or profile.role == 'admin'
    preview_role = request.session.get('preview_role')
    is_admin_preview = is_superuser_or_admin and (preview_role == 'partner' or (not preview_role and is_superuser_or_admin))
    
    if is_admin_preview:
        # Platform-wide stats (read-only)
        total_students = User.objects.filter(profile__role='student').count()
        total_enrollments = Enrollment.objects.count()
        completed_enrollments = Enrollment.objects.filter(status='completed').count()
        active_enrollments = Enrollment.objects.filter(status='active').count()
        total_revenue = Payment.objects.filter(status='completed').aggregate(total=Sum('amount'))['total'] or 0
        certificates_earned = Certificate.objects.count()
        
        class MockPartner:
            company_name = "Platform Overview (Preview)"
            commission_rate = 0.2
        
        partner = MockPartner()
        commission = total_revenue * partner.commission_rate
    else:
        try:
            partner = Partner.objects.get(user=user)
            
            # Student stats
            total_students = CohortMembership.objects.filter(cohort__partner=partner).count()
            
            # Enrollment stats
            enrollments = Enrollment.objects.filter(partner=partner)
            total_enrollments = enrollments.count()
            completed_enrollments = enrollments.filter(status='completed').count()
            active_enrollments = enrollments.filter(status='active').count()
            
            # Revenue stats
            total_revenue = Payment.objects.filter(
                partner=partner,
                status='completed'
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            commission = total_revenue * partner.commission_rate
            
            # Certificates
            certificates_earned = Certificate.objects.filter(
                enrollment__partner=partner
            ).count()
        except Partner.DoesNotExist:
            messages.error(request, 'You do not have a partner account.')
            return redirect('home')
    
    completion_rate = (completed_enrollments / total_enrollments * 100) if total_enrollments > 0 else 0
    active_percentage = (active_enrollments / total_enrollments * 100) if total_enrollments > 0 else 0
    completed_percentage = (completed_enrollments / total_enrollments * 100) if total_enrollments > 0 else 0
    
    context = {
        'partner': partner,
        'total_students': total_students,
        'total_enrollments': total_enrollments,
        'completed_enrollments': completed_enrollments,
        'active_enrollments': active_enrollments,
        'completion_rate': completion_rate,
        'active_percentage': active_percentage,
        'completed_percentage': completed_percentage,
        'total_revenue': total_revenue,
        'commission': commission,
        'certificates_earned': certificates_earned,
        'is_preview_mode': is_admin_preview,
    }
    return render(request, 'partner/reports.html', context)


@login_required
@role_required(['partner'])
def partner_settings(request):
    """Partner settings"""
    user = request.user
    profile = get_or_create_profile(user)
    
    # Superusers/admins automatically have partner access
    is_superuser_or_admin = user.is_superuser or user.is_staff or profile.role == 'admin'
    preview_role = request.session.get('preview_role')
    is_admin_preview = is_superuser_or_admin and (preview_role == 'partner' or (not preview_role and is_superuser_or_admin))
    
    if is_admin_preview:
        class MockPartner:
            company_name = "Platform Overview (Preview)"
            contact_email = "preview@example.com"
            contact_phone = ""
            website = ""
            commission_rate = 0.2
            is_active = True
        
        partner = MockPartner()
    else:
        try:
            partner = Partner.objects.get(user=user)
        except Partner.DoesNotExist:
            messages.error(request, 'You do not have a partner account.')
            return redirect('home')
    
    if request.method == 'POST' and not is_admin_preview:
        # Update partner settings
        partner.company_name = request.POST.get('company_name', partner.company_name)
        partner.contact_email = request.POST.get('contact_email', partner.contact_email)
        partner.contact_phone = request.POST.get('contact_phone', partner.contact_phone)
        partner.website = request.POST.get('website', partner.website)
        partner.save()
        
        messages.success(request, 'Settings updated successfully.')
        return redirect('partner_settings')
    
    context = {
        'partner': partner,
        'is_preview_mode': is_admin_preview,
    }
    return render(request, 'partner/settings.html', context)


# ============================================
# API ENDPOINTS
# ============================================

@require_GET
def api_courses(request):
    """Public API for courses"""
    courses = Course.objects.filter(status='published').values(
        'id', 'title', 'slug', 'short_description', 'outcome',
        'level', 'price', 'currency', 'estimated_hours',
        'enrolled_count', 'average_rating'
    )
    return JsonResponse(list(courses), safe=False)


@login_required
@require_GET
def api_courses_filter(request):
    """API endpoint for filtering courses (AJAX)"""
    search = request.GET.get('search', '').strip()
    level = request.GET.get('level', '')
    category_slug = request.GET.get('category', '')
    
    # Base queryset
    courses = Course.objects.filter(status='published').select_related('category')
    
    # Apply filters
    if level:
        courses = courses.filter(level=level)
    if category_slug:
        courses = courses.filter(category__slug=category_slug)
    if search:
        courses = courses.filter(
            Q(title__icontains=search) | 
            Q(description__icontains=search) |
            Q(outcome__icontains=search)
        )
    
    # Get selected currency
    selected_currency = request.session.get('selected_currency', 'USD')
    
    # Get user's enrolled courses
    user = request.user
    enrolled_course_ids = list(Enrollment.objects.filter(user=user).values_list('course_id', flat=True))
    
    # Prepare course data
    course_list = []
    for course in courses[:100]:  # Limit to 100 for performance
        # Get pricing
        try:
            pricing = CoursePricing.objects.get(course=course, currency=selected_currency)
            display_price = float(pricing.price)
            display_currency = selected_currency
        except CoursePricing.DoesNotExist:
            display_price = float(course.price)
            display_currency = course.currency
        
        course_list.append({
            'id': course.id,
            'title': course.title,
            'slug': course.slug,
            'outcome': course.outcome or '',
            'level': course.level,
            'category_slug': course.category.slug if course.category else '',
            'category_name': course.category.name if course.category else '',
            'course_type': course.course_type,
            'estimated_hours': course.estimated_hours,
            'lessons_count': course.lessons_count,
            'has_certificate': course.has_certificate,
            'average_rating': float(course.average_rating) if course.average_rating else 0,
            'is_free': course.is_free,
            'display_price': display_price,
            'display_currency': display_currency,
            'is_enrolled': course.id in enrolled_course_ids,
            'thumbnail_url': course.thumbnail.url if course.thumbnail else '',
            'has_preview_video': bool(course.preview_video),
        })
    
    return JsonResponse({
        'success': True,
        'courses': course_list,
        'count': len(course_list)
    })


@login_required
@require_GET
def api_notifications(request):
    """Get user notifications"""
    notifications = Notification.objects.filter(
        user=request.user
    ).values('id', 'notification_type', 'title', 'message', 'is_read', 'created_at')[:20]
    return JsonResponse(list(notifications), safe=False)


@login_required
@require_POST
def api_mark_notification_read(request):
    """Mark notification as read"""
    data = json.loads(request.body)
    notification_id = data.get('notification_id')
    
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.is_read = True
    notification.read_at = timezone.now()
    notification.save()
    
    return JsonResponse({'success': True})


@login_required
@require_POST
def api_update_language(request):
    """Update user language preference"""
    data = json.loads(request.body)
    language = data.get('language')
    
    profile = get_or_create_profile(request.user)
    profile.preferred_language = language
    profile.save()
    
    return JsonResponse({'success': True})


# ============================================
# BOOKING SYSTEM - TEACHER AVAILABILITY
# ============================================

@login_required
def teacher_availability(request):
    """Manage teacher availability schedule"""
    user = request.user
    teacher, _ = Teacher.objects.get_or_create(
        user=user,
        defaults={'permission_level': 'standard'}
    )
    
    # Get all availability slots
    # Order by slot type, then by day/time (handles both recurring and one-time slots)
    availability_slots = TeacherAvailability.objects.filter(teacher=teacher).order_by(
        'slot_type',
        'day_of_week',
        'start_time',
        'start_datetime'
    )
    
    # Get teacher's courses for course-specific availability
    # Include courses where teacher is instructor OR assigned via CourseTeacher
    assigned_course_ids = CourseTeacher.objects.filter(teacher=teacher).values_list('course_id', flat=True)
    courses = Course.objects.filter(
        Q(instructor=user) | Q(id__in=assigned_course_ids)
    ).distinct().order_by('title')
    
    if request.method == 'POST':
        # Create new availability slot
        slot_type = request.POST.get('slot_type', 'recurring')
        timezone_str = request.POST.get('timezone', 'UTC')
        course_id = request.POST.get('course')
        
        if slot_type == 'one_time':
            # One-time slot
            from datetime import datetime
            start_datetime_str = request.POST.get('start_datetime')
            end_datetime_str = request.POST.get('end_datetime')
            
            if not start_datetime_str or not end_datetime_str:
                messages.error(request, 'Start datetime and end datetime are required for one-time slots.')
                return redirect('teacher_availability')
            
            try:
                start_datetime = datetime.fromisoformat(start_datetime_str.replace('Z', '+00:00'))
                end_datetime = datetime.fromisoformat(end_datetime_str.replace('Z', '+00:00'))
            except (ValueError, AttributeError) as e:
                messages.error(request, f'Invalid datetime format: {str(e)}')
                return redirect('teacher_availability')
            
            if end_datetime <= start_datetime:
                messages.error(request, 'End datetime must be after start datetime.')
                return redirect('teacher_availability')
            
            TeacherAvailability.objects.create(
                teacher=teacher,
                course_id=course_id if course_id else None,
                slot_type='one_time',
                start_datetime=start_datetime,
                end_datetime=end_datetime,
                timezone=timezone_str
            )
        else:
            # Recurring slot
            day_of_week_str = request.POST.get('day_of_week')
            if not day_of_week_str:
                messages.error(request, 'Day of week is required for recurring slots.')
                return redirect('teacher_availability')
            
            try:
                day_of_week = int(day_of_week_str)
            except (ValueError, TypeError):
                messages.error(request, 'Invalid day of week.')
                return redirect('teacher_availability')
            
            start_time = request.POST.get('start_time')
            end_time = request.POST.get('end_time')
            valid_from = request.POST.get('valid_from') or None
            valid_until = request.POST.get('valid_until') or None
            
            if not start_time or not end_time:
                messages.error(request, 'Start time and end time are required for recurring slots.')
                return redirect('teacher_availability')
            
            TeacherAvailability.objects.create(
                teacher=teacher,
                course_id=course_id if course_id else None,
                slot_type='recurring',
                day_of_week=day_of_week,
                start_time=start_time,
                end_time=end_time,
                timezone=timezone_str,
                valid_from=valid_from,
                valid_until=valid_until
            )
        
        messages.success(request, 'Availability slot added successfully!')
        return redirect('teacher_availability')
    
    context = {
        'availability_slots': availability_slots,
        'courses': courses,
    }
    return render(request, 'teacher/availability.html', context)


@login_required
@require_POST
def teacher_availability_toggle_block(request, availability_id):
    """Block or unblock an availability slot"""
    availability = get_object_or_404(TeacherAvailability, id=availability_id, teacher__user=request.user)
    availability.is_blocked = not availability.is_blocked
    if availability.is_blocked:
        availability.blocked_reason = request.POST.get('blocked_reason', '')
    else:
        availability.blocked_reason = ''
    availability.save()
    
    action = 'blocked' if availability.is_blocked else 'unblocked'
    messages.success(request, f'Availability slot {action} successfully!')
    return redirect('teacher_availability')


@login_required
@require_POST
def teacher_availability_delete(request, availability_id):
    """Delete availability slot"""
    availability = get_object_or_404(TeacherAvailability, id=availability_id, teacher__user=request.user)
    availability.delete()
    messages.success(request, 'Availability slot deleted successfully!')
    return redirect('teacher_availability')


@login_required
def teacher_schedule_calendar(request):
    """Teacher schedule calendar view"""
    user = request.user
    teacher, _ = Teacher.objects.get_or_create(
        user=user,
        defaults={'permission_level': 'standard'}
    )
    
    # Get all availability slots
    availability_slots = TeacherAvailability.objects.filter(teacher=teacher).order_by('day_of_week', 'start_time', 'start_datetime')
    
    # Get all live class sessions
    live_sessions = LiveClassSession.objects.filter(teacher=teacher).select_related('course').order_by('scheduled_start')
    
    # Get all bookings
    bookings = LiveClassBooking.objects.filter(
        teacher=teacher,
        booking_type='group_session'
    ).select_related('session', 'student_user').order_by('start_at_utc', 'session__scheduled_start')
    
    context = {
        'availability_slots': availability_slots,
        'live_sessions': live_sessions,
        'bookings': bookings,
        'now': timezone.now(),
    }
    return render(request, 'teacher/schedule_calendar.html', context)


@login_required
@require_POST
def teacher_toggle_online_status(request):
    """Toggle teacher online status"""
    teacher, _ = Teacher.objects.get_or_create(
        user=request.user,
        defaults={'permission_level': 'standard'}
    )
    is_online = request.POST.get('is_online') == 'true'
    teacher.update_online_status(is_online)
    
    return JsonResponse({
        'success': True,
        'is_online': teacher.is_online,
        'last_seen': teacher.last_seen.isoformat() if teacher.last_seen else None
    })


# ============================================
# BOOKING SYSTEM - STUDENT BOOKING
# ============================================

@login_required
def student_book_session(request, session_id):
    """Book a live class session (Phase 2: Using unified LiveClassBooking)"""
    user = request.user
    session = get_object_or_404(LiveClassSession, id=session_id)
    
    # Check if user is enrolled in the course
    enrollment = Enrollment.objects.filter(user=user, course=session.course, status='active').first()
    if not enrollment:
        message_app(request, messages.ERROR, 'You must be enrolled in this course to book a session.')
        return redirect('student_course_detail', slug=session.course.slug)
    
    # Check if session can be booked
    can_book, message = session.can_be_booked(user)
    if not can_book:
        messages.error(request, message)
        return redirect('student_course_detail', slug=session.course.slug)
    
    if request.method == 'POST':
        student_notes = request.POST.get('student_notes', '')
        
        # Check for conflicts using unified booking model
        start_utc = session.start_at_utc or session.scheduled_start
        end_utc = session.end_at_utc or (start_utc + timezone.timedelta(minutes=session.duration_minutes))
        
        conflicting_bookings = LiveClassBooking.objects.filter(
            student_user=user,
            start_at_utc__lt=end_utc,
            end_at_utc__gt=start_utc,
            status__in=['pending', 'confirmed']
        ).exclude(session=session)
        
        if conflicting_bookings.exists():
            messages.error(request, 'You already have a booking at this time.')
            return redirect('student_course_detail', slug=session.course.slug)
        
        # Check if already booked this session
        existing_booking = LiveClassBooking.objects.filter(
            student_user=user,
            session=session,
            booking_type='group_session',
            status__in=['pending', 'confirmed']
        ).first()
        
        if existing_booking:
            messages.error(request, 'You already have a booking for this session.')
            return redirect('student_course_detail', slug=session.course.slug)
        
        # Determine booking status based on seat availability and waitlist
        if session.total_seats and session.remaining_seats <= 0:
            # Check if waitlist is enabled
            if session.enable_waitlist:
                # Add to waitlist instead of creating booking
                waitlist_entry, created = SessionWaitlist.objects.get_or_create(
                    session=session,
                    student_user=user,
                    defaults={'status': 'waiting'}
                )
                if created:
                    message_app(request, messages.INFO, f'Added to waitlist for "{session.title}". You will be notified if a spot becomes available.')
                    Notification.objects.create(
                        user=user,
                        notification_type='booking_waitlisted',
                        title='Added to Waitlist',
                        message=f'You have been added to the waitlist for "{session.title}".'
                    )
                else:
                    messages.info(request, 'You are already on the waitlist for this session.')
                return redirect('student_bookings')
            else:
                messages.error(request, 'Session is full and waitlist is disabled.')
                return redirect('student_course_detail', slug=session.course.slug)
        
        # Check if approval is required (using TeacherBookingPolicy)
        requires_approval = False
        policy = TeacherBookingPolicy.objects.filter(
            teacher=session.teacher,
            course=session.course
        ).first()
        if not policy:
            policy = TeacherBookingPolicy.objects.filter(
                teacher=session.teacher,
                course__isnull=True
            ).first()
        if policy:
            requires_approval = policy.requires_approval_for_group
        
        # Create unified booking
        booking = LiveClassBooking.objects.create(
            booking_type='group_session',
            course=session.course,
            teacher=session.teacher,
            student_user=user,
            session=session,
            start_at_utc=start_utc,
            end_at_utc=end_utc,
            status='pending' if requires_approval else 'confirmed',
            student_note=student_notes,
            seats_reserved=1
        )
        
        if not requires_approval:
            booking.confirm()
            # Update session seats_taken
            session.seats_taken = (session.seats_taken or 0) + 1
            session.save(update_fields=['seats_taken'])
            message_app(request, messages.SUCCESS, f'Successfully booked "{session.title}"!')
        else:
            message_app(request, messages.SUCCESS, f'Booking request submitted for "{session.title}". The teacher will review your request.')
        
        # Create notification
        Notification.objects.create(
            user=user,
            notification_type='booking_confirmed' if not requires_approval else 'booking_pending',
            title=f'Booking {"Confirmed" if not requires_approval else "Pending"}',
            message=f'Your booking for "{session.title}" is {"confirmed" if not requires_approval else "pending approval"}.'
        )
        
        return redirect('student_bookings')
    
    context = {
        'session': session,
        'enrollment': enrollment,
    }
    return render(request, 'student/book_session.html', context)


@login_required
def student_live_class_detail_modal(request, session_id):
    """Get live class details for modal (AJAX)"""
    user = request.user
    session = get_object_or_404(
        LiveClassSession, 
        id=session_id
    )
    
    # Check enrollment status
    enrollment = Enrollment.objects.filter(
        user=user,
        course=session.course,
        status='active'
    ).first()
    
    # Check if student has a confirmed booking for this session
    # Meeting link should only be visible to students with confirmed/attended bookings
    has_confirmed_booking = LiveClassBooking.objects.filter(
        student_user=user,
        session=session,
        status__in=['confirmed', 'attended']  # Only show link for confirmed enrollments
    ).exists()
    
    # Check if can book
    can_book, booking_message = session.can_be_booked(user)
    
    # Get selected currency
    selected_currency = request.session.get('selected_currency', 'USD')
    
    # Get course pricing
    try:
        pricing = CoursePricing.objects.get(course=session.course, currency=selected_currency)
        course_price = pricing.price
        course_currency = selected_currency
    except CoursePricing.DoesNotExist:
        course_price = session.course.price
        course_currency = session.course.currency
    
    context = {
        'session': session,
        'enrollment': enrollment,
        'can_book': can_book,
        'booking_message': booking_message,
        'course_price': course_price,
        'course_currency': course_currency,
        'selected_currency': selected_currency,
        'has_confirmed_booking': has_confirmed_booking,  # Permission-based visibility for meeting link
    }
    return render(request, 'student/live_class_detail_modal.html', context)


@login_required
def student_live_classes(request):
    """View available live classes for enrollment"""
    user = request.user
    now = timezone.now()
    
    # Get all upcoming live classes that are open for booking
    # Only show classes for published courses - students shouldn't see draft courses
    live_classes = LiveClassSession.objects.filter(
        status='scheduled',
        scheduled_start__gt=now,
        course__status='published'  # Only show published courses
    ).select_related('course', 'teacher', 'teacher__user').order_by('scheduled_start')
    
    # Filter by course enrollment status
    enrolled_course_ids = set(Enrollment.objects.filter(
        user=user,
        status='active'
    ).values_list('course_id', flat=True))
    
    # Separate classes by enrollment requirement
    available_classes = []
    for session in live_classes:
        # Check if user is enrolled in the course
        session.user_is_enrolled = session.course.id in enrolled_course_ids
        # Check if session can be booked
        can_book, message = session.can_be_booked(user)
        session.can_book = can_book
        session.booking_message = message
        available_classes.append(session)
    
    # Filter by search
    search = request.GET.get('search', '')
    if search:
        available_classes = [
            s for s in available_classes
            if search.lower() in s.title.lower() or 
               search.lower() in s.course.title.lower() or
               search.lower() in s.teacher.user.get_full_name().lower()
        ]
    
    # Filter by teacher
    teacher_id = request.GET.get('teacher_id')
    if teacher_id:
        available_classes = [s for s in available_classes if s.teacher.id == int(teacher_id)]
    
    context = {
        'live_classes': available_classes,
        'search_query': search,
        'selected_teacher_id': teacher_id,
    }
    return render(request, 'student/live_classes.html', context)


@login_required
def student_teacher_profile(request, teacher_id):
    """View teacher profile with their courses"""
    user = request.user
    teacher = get_object_or_404(Teacher, id=teacher_id, is_approved=True)
    
    # Get teacher's courses (published only)
    teacher_courses = Course.objects.filter(
        course_teachers__teacher=teacher,
        status='published'
    ).distinct().select_related('category').prefetch_related('course_teachers')
    
    # Check which courses user is enrolled in
    enrolled_course_ids = set(Enrollment.objects.filter(
        user=user,
        status='active'
    ).values_list('course_id', flat=True))
    
    for course in teacher_courses:
        course.user_is_enrolled = course.id in enrolled_course_ids
    
    # Get teacher's upcoming live classes
    now = timezone.now()
    upcoming_classes = LiveClassSession.objects.filter(
        teacher=teacher,
        status='scheduled',
        scheduled_start__gt=now
    ).select_related('course').order_by('scheduled_start')[:5]
    
    # Get selected currency
    selected_currency = request.session.get('selected_currency', 'USD')
    
    # Add pricing info to courses
    course_ids = [c.id for c in teacher_courses]
    pricing_objects = CoursePricing.objects.filter(course_id__in=course_ids, currency=selected_currency).select_related('course')
    course_pricing_map = {}
    for pricing in pricing_objects:
        course_pricing_map[pricing.course_id] = pricing.price
    
    for course in teacher_courses:
        if course.id in course_pricing_map:
            course.display_price = course_pricing_map[course.id]
            course.display_currency = selected_currency
        else:
            course.display_price = course.price
            course.display_currency = course.currency
    
    context = {
        'teacher': teacher,
        'teacher_courses': teacher_courses,
        'upcoming_classes': upcoming_classes,
        'selected_currency': selected_currency,
    }
    return render(request, 'student/teacher_profile.html', context)


@login_required
def student_bookings(request):
    """View all student bookings (both Group Session and 1:1) - Phase 2: Using unified LiveClassBooking"""
    user = request.user
    
    # Get all bookings using unified model
    all_bookings = LiveClassBooking.objects.filter(
        student_user=user
    ).select_related(
        'session', 'session__course', 'session__teacher__user',
        'course', 'teacher', 'teacher__user'
    ).order_by('-created_at')
    
    # Separate by booking type and status
    upcoming_group = []
    past_group = []
    upcoming_one_on_one = []
    past_one_on_one = []
    
    now = timezone.now()
    for booking in all_bookings:
        if booking.booking_type == 'group_session':
            # Group session booking
            if booking.session:
                session_start = booking.start_at_utc or booking.session.scheduled_start
                if session_start >= now and booking.status in ['pending', 'confirmed']:
                    upcoming_group.append(booking)
                else:
                    past_group.append(booking)
        elif booking.booking_type == 'one_on_one':
            # 1:1 booking
            if booking.start_at_utc >= now and booking.status in ['pending', 'confirmed']:
                upcoming_one_on_one.append(booking)
            else:
                past_one_on_one.append(booking)
    
    # Combine all upcoming and past bookings
    upcoming_bookings = upcoming_group + upcoming_one_on_one
    past_bookings = past_group + past_one_on_one
    
    # Sort by date
    upcoming_bookings.sort(key=lambda x: x.start_at_utc or timezone.now(), reverse=False)
    past_bookings.sort(key=lambda x: x.start_at_utc or timezone.now(), reverse=True)
    
    context = {
        'upcoming_bookings': upcoming_bookings,
        'past_bookings': past_bookings,
        'upcoming_group': upcoming_group,
        'past_group': past_group,
        'upcoming_one_on_one': upcoming_one_on_one,
        'past_one_on_one': past_one_on_one,
    }
    return render(request, 'student/bookings.html', context)


@login_required
@require_POST
def student_booking_cancel(request, booking_id):
    """Cancel a booking - Phase 2: Using unified LiveClassBooking"""
    booking = get_object_or_404(LiveClassBooking, id=booking_id, student_user=request.user)
    
    # Check if booking can be cancelled (must be at least 24 hours before start)
    if booking.start_at_utc:
        hours_until = (booking.start_at_utc - timezone.now()).total_seconds() / 3600
        if hours_until < 24:
            message_app(request, messages.ERROR, 'This booking cannot be cancelled (must be cancelled at least 24 hours before the session).')
            return redirect('student_bookings')
    
    if booking.status not in ['pending', 'confirmed']:
        message_app(request, messages.ERROR, 'This booking cannot be cancelled.')
        return redirect('student_bookings')
    
    notes = request.POST.get('notes', '')
    booking.cancel(cancelled_by=request.user, reason='student', note=notes)
    
    # Update session seats_taken if group session
    if booking.booking_type == 'group_session' and booking.session:
        session = booking.session
        if session.seats_taken > 0:
            session.seats_taken -= 1
            session.save(update_fields=['seats_taken'])
    
    messages.success(request, 'Booking cancelled successfully.')
    
    # Create notification
    session_title = booking.session.title if booking.session else '1:1 Session'
    Notification.objects.create(
        user=request.user,
        notification_type='booking_cancelled',
        title='Booking Cancelled',
        message=f'Your booking for "{session_title}" has been cancelled.'
    )
    
    return redirect('student_bookings')


@login_required
def student_booking_reschedule(request, booking_id):
    """Reschedule a booking to a different session - Phase 2: Using unified LiveClassBooking"""
    booking = get_object_or_404(LiveClassBooking, id=booking_id, student_user=request.user, booking_type='group_session')
    
    if not booking.session:
        message_app(request, messages.ERROR, 'This booking cannot be rescheduled.')
        return redirect('student_bookings')
    
    if booking.status not in ['confirmed', 'pending']:
        message_app(request, messages.ERROR, 'This booking cannot be rescheduled.')
        return redirect('student_bookings')
    
    # Get available sessions for the same course
    available_sessions = LiveClassSession.objects.filter(
        course=booking.course,
        status='scheduled',
        scheduled_start__gte=timezone.now()
    ).exclude(id=booking.session.id).order_by('scheduled_start')
    
    if request.method == 'POST':
        new_session_id = request.POST.get('new_session_id')
        notes = request.POST.get('notes', '')
        
        new_session = get_object_or_404(LiveClassSession, id=new_session_id, course=booking.course)
        
        # Check if new session can be booked
        can_book, message = new_session.can_be_booked(request.user)
        if not can_book:
            messages.error(request, message)
            return redirect('student_booking_reschedule', booking_id=booking.id)
        
        # Create new booking for new session
        start_utc = new_session.start_at_utc or new_session.scheduled_start
        end_utc = new_session.end_at_utc or (start_utc + timezone.timedelta(minutes=new_session.duration_minutes))
        
        new_booking = LiveClassBooking.objects.create(
            booking_type='group_session',
            course=booking.course,
            teacher=booking.teacher,
            student_user=request.user,
            session=new_session,
            start_at_utc=start_utc,
            end_at_utc=end_utc,
            status=booking.status,  # Preserve original status
            student_note=notes or booking.student_note,
            seats_reserved=1
        )
        
        # Mark old booking as rescheduled
        booking.status = 'rescheduled'
        booking.teacher_note = f'Rescheduled to session on {new_session.scheduled_start}'
        booking.save()
        
        # Update session seats
        if booking.session:
            if booking.session.seats_taken > 0:
                booking.session.seats_taken -= 1
                booking.session.save(update_fields=['seats_taken'])
        
        if new_booking.status == 'confirmed':
            new_session.seats_taken = (new_session.seats_taken or 0) + 1
            new_session.save(update_fields=['seats_taken'])
        
        message_app(request, messages.SUCCESS, f'Booking rescheduled to {new_session.scheduled_start.strftime("%B %d, %Y at %I:%M %p")}.')
        
        # Create notification
        Notification.objects.create(
            user=request.user,
            notification_type='booking_rescheduled',
            title='Booking Rescheduled',
            message=f'Your booking has been rescheduled to "{new_session.title}".'
        )
        return redirect('student_bookings')
    
    context = {
        'booking': booking,
        'available_sessions': available_sessions,
    }
    return render(request, 'student/reschedule_booking.html', context)


# ============================================
# BOOKING SYSTEM - BOOKING MANAGEMENT (Teacher)
# ============================================

@login_required
def teacher_session_bookings(request, session_id):
    """View all bookings for a session (teacher view) - Phase 2: Using unified LiveClassBooking"""
    session = get_object_or_404(LiveClassSession, id=session_id, teacher__user=request.user)
    bookings = LiveClassBooking.objects.filter(
        session=session,
        booking_type='group_session'
    ).select_related('student_user', 'student_user__profile').order_by('created_at')
    
    context = {
        'session': session,
        'bookings': bookings,
    }
    return render(request, 'teacher/session_bookings.html', context)


@login_required
@require_POST
def teacher_booking_cancel(request, booking_id):
    """Teacher cancels a booking - Phase 2: Using unified LiveClassBooking"""
    booking = get_object_or_404(LiveClassBooking, id=booking_id, booking_type='group_session')
    
    if not booking.session:
        messages.error(request, 'Invalid booking.')
        return redirect('teacher_dashboard')
    
    session = booking.session
    
    # Check if user is teacher for this session
    if session.teacher.user != request.user:
        messages.error(request, 'You do not have permission to cancel this booking.')
        return redirect('teacher_live_classes', course_id=session.course.id)
    
    notes = request.POST.get('notes', '')
    booking.cancel(cancelled_by=request.user, reason='teacher', note=notes)
    
    # Update session seats_taken
    if session.seats_taken > 0:
        session.seats_taken -= 1
        session.save(update_fields=['seats_taken'])
    
    message_app(request, messages.SUCCESS, 'Booking cancelled successfully.')
    
    # Create notification for student
    Notification.objects.create(
        user=booking.student_user,
        notification_type='booking_cancelled',
        title='Booking Cancelled by Teacher',
        message=f'Your booking for "{session.title}" has been cancelled by the teacher.'
    )
    
    return redirect('teacher_session_bookings', session_id=session.id)


@login_required
@require_POST
def teacher_mark_attendance(request, booking_id):
    """Mark student attendance - Phase 2: Using unified LiveClassBooking"""
    booking = get_object_or_404(LiveClassBooking, id=booking_id, booking_type='group_session')
    
    if not booking.session:
        messages.error(request, 'Invalid booking.')
        return redirect('teacher_dashboard')
    
    session = booking.session
    
    # Check if user is teacher for this session
    if session.teacher.user != request.user:
        message_app(request, messages.ERROR, 'You do not have permission to mark attendance.')
        return redirect('teacher_live_classes', course_id=session.course.id)
    
    attended = request.POST.get('attended') == 'true'
    booking.status = 'attended' if attended else 'no_show'
    booking.save(update_fields=['status'])
    
    message_app(request, messages.SUCCESS, f'Attendance marked as {"Attended" if attended else "No Show"}.')
    return redirect('teacher_session_bookings', session_id=session.id)


# ============================================
# 1:1 BOOKING SYSTEM - STUDENT BOOKING
# ============================================

@login_required
def student_book_one_on_one(request, course_id):
    """View available slots and book a 1:1 session"""
    user = request.user
    course = get_object_or_404(Course, id=course_id)
    
    # Check if course has 1:1 booking enabled
    if course.booking_type != 'one_on_one':
        messages.error(request, '1:1 booking is not enabled for this course.')
        return redirect('student_course_detail', slug=course.slug)
    
    # Check if user is enrolled
    enrollment = Enrollment.objects.filter(user=user, course=course, status='active').first()
    if not enrollment:
        message_app(request, messages.ERROR, 'You must be enrolled in this course to book a session.')
        return redirect('student_course_detail', slug=course.slug)
    
    # Get available teachers for this course
    course_teachers = CourseTeacher.objects.filter(
        course=course,
        teacher__is_approved=True
    ).select_related('teacher', 'teacher__user')
    
    # Get available slots for these teachers
    available_slots = TeacherAvailability.objects.filter(
        course=course,
        teacher__in=[ct.teacher for ct in course_teachers],
        is_active=True,
        is_blocked=False
    ).select_related('teacher', 'teacher__user').order_by('start_datetime', 'day_of_week', 'start_time')
    
    # Filter out slots that are already booked or unavailable
    available_slots = [slot for slot in available_slots if slot.is_available_for_booking]
    
    # Filter by teacher if requested
    teacher_id = request.GET.get('teacher_id')
    if teacher_id:
        available_slots = [slot for slot in available_slots if slot.teacher.id == int(teacher_id)]
    
    context = {
        'course': course,
        'enrollment': enrollment,
        'available_slots': available_slots,
        'course_teachers': course_teachers,
        'selected_teacher_id': teacher_id,
    }
    return render(request, 'student/book_one_on_one.html', context)


@login_required
@require_POST
def student_book_one_on_one_submit(request, availability_id):
    """Submit a 1:1 booking request"""
    user = request.user
    availability = get_object_or_404(TeacherAvailability, id=availability_id)
    
    # Check if slot can be booked
    can_book, message = availability.can_be_booked(user=user, course=availability.course)
    if not can_book:
        messages.error(request, message)
        return redirect('student_book_one_on_one', course_id=availability.course.id)
    
    # Get course to check enrollment
    course = availability.course
    enrollment = Enrollment.objects.filter(user=user, course=course, status='active').first()
    if not enrollment:
        message_app(request, messages.ERROR, 'You must be enrolled in this course.')
        return redirect('student_course_detail', slug=course.slug)
    
    # Check if approval is required (using TeacherBookingPolicy)
    requires_approval = False
    policy = TeacherBookingPolicy.objects.filter(
        teacher=availability.teacher,
        course=course
    ).first()
    if not policy:
        policy = TeacherBookingPolicy.objects.filter(
            teacher=availability.teacher,
            course__isnull=True
        ).first()
    if policy:
        requires_approval = policy.requires_approval_for_one_on_one
    else:
        # Fallback to course-level setting
        requires_approval = course.requires_booking_approval
        course_teacher = CourseTeacher.objects.filter(course=course, teacher=availability.teacher).first()
        if course_teacher and course_teacher.get_requires_approval():
            requires_approval = True
    
    # Get start/end times from availability slot
    if availability.slot_type == 'one_time':
        start_utc = availability.start_datetime
        end_utc = availability.end_datetime
    else:
        # For recurring slots, we need to calculate the next occurrence
        # For now, use current time + duration as placeholder
        # In production, you'd calculate the actual next occurrence
        start_utc = timezone.now() + timezone.timedelta(days=1)
        end_utc = start_utc + timezone.timedelta(hours=1)
    
    # Create unified booking
    student_notes = request.POST.get('student_notes', '')
    
    booking = LiveClassBooking.objects.create(
        booking_type='one_on_one',
        course=course,
        teacher=availability.teacher,
        student_user=user,
        session=None,  # 1:1 bookings don't have a session
        start_at_utc=start_utc,
        end_at_utc=end_utc,
        status='pending' if requires_approval else 'confirmed',
        student_note=student_notes,
        seats_reserved=1
    )
    
    if not requires_approval:
        # Auto-confirm if no approval needed
        booking.confirm()
        message_app(request, messages.SUCCESS, f'Successfully booked 1:1 session with {availability.teacher.user.get_full_name()}!')
    else:
        message_app(request, messages.SUCCESS, f'Booking request submitted! {availability.teacher.user.get_full_name()} will review your request.')
    
    # Create notification
    Notification.objects.create(
        user=user,
        notification_type='booking_confirmed' if not requires_approval else 'booking_pending',
        title=f'1:1 Booking {"Confirmed" if not requires_approval else "Pending"}',
        message=f'Your 1:1 booking with {availability.teacher.user.get_full_name()} is {"confirmed" if not requires_approval else "pending approval"}.'
    )
    
    # Notify teacher if approval is required
    if requires_approval:
        Notification.objects.create(
            user=availability.teacher.user,
            notification_type='booking_pending',
            title='New 1:1 Booking Request',
            message=f'{user.get_full_name()} has requested a 1:1 session. Please review and approve or decline.',
            action_url=f'/teacher/one-on-one-bookings/{booking.id}/'
        )
    
    return redirect('student_bookings')


@login_required
def student_booking_one_on_one_cancel(request, booking_id):
    """Cancel a 1:1 booking - Phase 2: Using unified LiveClassBooking"""
    booking = get_object_or_404(LiveClassBooking, id=booking_id, student_user=request.user, booking_type='one_on_one')
    
    # Check if booking can be cancelled (must be at least 24 hours before start)
    if booking.start_at_utc:
        hours_until = (booking.start_at_utc - timezone.now()).total_seconds() / 3600
        if hours_until < 24:
            message_app(request, messages.ERROR, 'This booking cannot be cancelled (must be cancelled at least 24 hours before the session).')
            return redirect('student_bookings')
    
    if booking.status not in ['pending', 'confirmed']:
        message_app(request, messages.ERROR, 'This booking cannot be cancelled.')
        return redirect('student_bookings')
    
    notes = request.POST.get('notes', '') if request.method == 'POST' else ''
    booking.cancel(cancelled_by=request.user, reason='student', note=notes)
    
    messages.success(request, '1:1 booking cancelled successfully.')
    
    # Create notification
    Notification.objects.create(
        user=request.user,
        notification_type='booking_cancelled',
        title='1:1 Booking Cancelled',
        message=f'Your 1:1 booking has been cancelled.'
    )
    
    return redirect('student_bookings')


# ============================================
# 1:1 BOOKING SYSTEM - TEACHER APPROVAL & MANAGEMENT
# ============================================

@login_required
def teacher_one_on_one_bookings(request):
    """View all 1:1 booking requests for teacher - Phase 2: Using unified LiveClassBooking"""
    user = request.user
    teacher, _ = Teacher.objects.get_or_create(user=user, defaults={'permission_level': 'standard'})
    
    # Get all 1:1 bookings for this teacher
    bookings = LiveClassBooking.objects.filter(
        teacher=teacher,
        booking_type='one_on_one'
    ).select_related('student_user', 'course').order_by('-created_at')
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        bookings = bookings.filter(status=status_filter)
    
    # Separate pending, confirmed, and past bookings
    now = timezone.now()
    pending_bookings = bookings.filter(status='pending')
    confirmed_bookings = bookings.filter(status='confirmed', start_at_utc__gte=now)
    past_bookings = bookings.filter(
        Q(status__in=['confirmed', 'attended', 'no_show', 'cancelled']) |
        Q(start_at_utc__lt=now)
    )
    
    context = {
        'pending_bookings': pending_bookings,
        'confirmed_bookings': confirmed_bookings,
        'past_bookings': past_bookings,
        'status_filter': status_filter,
    }
    return render(request, 'teacher/one_on_one_bookings.html', context)


@login_required
@require_POST
def teacher_one_on_one_approve(request, booking_id):
    """Approve a 1:1 booking request - Phase 2: Using unified LiveClassBooking"""
    booking = get_object_or_404(LiveClassBooking, id=booking_id, booking_type='one_on_one')
    
    # Check if user is the teacher
    if booking.teacher.user != request.user:
        messages.error(request, 'You do not have permission to approve this booking.')
        return redirect('teacher_one_on_one_bookings')
    
    if booking.status != 'pending':
        messages.error(request, 'This booking cannot be approved.')
        return redirect('teacher_one_on_one_bookings')
    
    # Optionally set meeting link (store in teacher_note for now, or add meeting_link field to LiveClassBooking)
    meeting_link = request.POST.get('meeting_link', '')
    if meeting_link:
        booking.teacher_note = f'Meeting link: {meeting_link}'
    
    booking.confirm(decided_by=request.user)
    
    messages.success(request, 'Booking approved successfully.')
    
    # Notify student
    Notification.objects.create(
        user=booking.student_user,
        notification_type='booking_confirmed',
        title='1:1 Booking Approved',
        message=f'Your 1:1 booking with {request.user.get_full_name()} has been approved.'
    )
    
    return redirect('teacher_one_on_one_bookings')


@login_required
@require_POST
def teacher_one_on_one_decline(request, booking_id):
    """Decline a 1:1 booking request - Phase 2: Using unified LiveClassBooking"""
    booking = get_object_or_404(LiveClassBooking, id=booking_id, booking_type='one_on_one')
    
    # Check if user is the teacher
    if booking.teacher.user != request.user:
        messages.error(request, 'You do not have permission to decline this booking.')
        return redirect('teacher_one_on_one_bookings')
    
    if booking.status != 'pending':
        messages.error(request, 'This booking cannot be declined.')
        return redirect('teacher_one_on_one_bookings')
    
    reason = request.POST.get('reason', '')
    booking.decline(decided_by=request.user, reason=reason)
    
    messages.success(request, 'Booking declined.')
    
    # Notify student
    Notification.objects.create(
        user=booking.student_user,
        notification_type='booking_cancelled',
        title='1:1 Booking Declined',
        message=f'Your 1:1 booking request with {request.user.get_full_name()} has been declined.'
    )
    
    return redirect('teacher_one_on_one_bookings')


@login_required
@require_POST
def teacher_one_on_one_cancel(request, booking_id):
    """Teacher cancels a 1:1 booking - Phase 2: Using unified LiveClassBooking"""
    booking = get_object_or_404(LiveClassBooking, id=booking_id, booking_type='one_on_one')
    
    # Check if user is the teacher
    if booking.teacher.user != request.user:
        messages.error(request, 'You do not have permission to cancel this booking.')
        return redirect('teacher_one_on_one_bookings')
    
    notes = request.POST.get('notes', '')
    booking.cancel(cancelled_by=request.user, reason='teacher', note=notes)
    
    messages.success(request, 'Booking cancelled.')
    
    # Notify student
    Notification.objects.create(
        user=booking.student_user,
        notification_type='booking_cancelled',
        title='1:1 Booking Cancelled',
        message=f'Your 1:1 booking with {request.user.get_full_name()} has been cancelled by the teacher.'
    )
    
    return redirect('teacher_one_on_one_bookings')
