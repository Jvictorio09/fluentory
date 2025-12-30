from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
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
    TeacherAvailability, Booking, BookingReminder
)


# ============================================
# HELPER FUNCTIONS
# ============================================

def get_site_settings():
    """Get site settings singleton"""
    return SiteSettings.get_settings()


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
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('home')
        return wrapper
    return decorator


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
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name or user.username}!')
            
            # Redirect based on role
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect_by_role(user)
        else:
            messages.error(request, 'Invalid username or password.')
    
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


def logout_view(request):
    """User logout"""
    logout(request)
    messages.info(request, 'You have been logged out.')
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
    
    # Check if user is a teacher (approved)
    if role == 'instructor' or (hasattr(user, 'teacher_profile') and user.teacher_profile.is_approved):
        return redirect('teacher_dashboard')
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
    
    try:
        # Ensure database connection is alive
        connection.ensure_connection()
        
        profile = get_or_create_profile(user)
        
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
    
    # Base queryset
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
    
    # Course modules and lessons
    modules = course.modules.prefetch_related('lessons').order_by('order')
    
    # Reviews
    reviews = course.reviews.filter(is_approved=True).select_related('user').order_by('-created_at')[:10]
    
    # Similar courses
    similar_courses = Course.objects.filter(
        category=course.category,
        status='published'
    ).exclude(id=course.id)[:4]
    
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
    
    context = {
        'course': course,
        'enrollment': enrollment,
        'modules': modules,
        'reviews': reviews,
        'similar_courses': similar_courses,
        'selected_currency': selected_currency,
        'course_price': course_price,
        'course_currency': course_currency,
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
    
    # Update enrollment's current position
    if current_lesson:
        enrollment.current_lesson = current_lesson
        enrollment.current_module = current_lesson.module
        enrollment.save()
    
    # Get or create lesson progress
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
    
    # AI Tutor conversation
    conversation = TutorConversation.objects.filter(
        user=user,
        lesson=current_lesson
    ).first()
    
    tutor_messages = []
    conversation_id = None
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


@login_required
@require_POST
def enroll_course(request):
    """Enroll in a course (AJAX)"""
    data = json.loads(request.body)
    course_id = data.get('course_id')
    
    course = get_object_or_404(Course, id=course_id, status='published')
    
    # Check if already enrolled
    if Enrollment.objects.filter(user=request.user, course=course).exists():
        return JsonResponse({'success': False, 'error': 'Already enrolled'})
    
    # Create enrollment
    enrollment = Enrollment.objects.create(
        user=request.user,
        course=course
    )
    
    # Update course stats
    course.enrolled_count += 1
    course.save()
    
    return JsonResponse({
        'success': True,
        'enrollment_id': enrollment.id,
        'redirect_url': f'/student/player/{enrollment.id}/'
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
            answer_id = request.POST.get(f'question_{question.id}')
            if answer_id:
                answers[str(question.id)] = answer_id
                correct = question.answers.filter(is_correct=True).first()
                if correct and str(correct.id) == answer_id:
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
    
    context = {
        'attempt': attempt,
        'quiz': attempt.quiz,
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
            'color': 'red'
        })
    
    if failed_payments > 0:
        action_items.append({
            'type': 'warning',
            'title': f'{failed_payments} payment failures in queue',
            'description': 'Requires manual review',
            'icon': 'fa-credit-card',
            'color': 'orange'
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
    
    # Check if user is teacher
    if not hasattr(user, 'teacher_profile') or not user.teacher_profile.is_approved:
        # Check if user has instructor role
        if profile.role != 'instructor':
            messages.error(request, 'You do not have permission to access the teacher dashboard.')
            return redirect('student_home')
        # Create teacher profile if doesn't exist
        teacher, _ = Teacher.objects.get_or_create(user=user)
        teacher.is_approved = True
        teacher.save()
    else:
        teacher = user.teacher_profile
    
    # Update online status
    teacher.is_online = True
    teacher.last_seen = timezone.now()
    teacher.save()
    
    # Get assigned courses
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
def teacher_courses(request):
    """My Courses - view all assigned courses"""
    user = request.user
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
def teacher_course_create(request):
    """Create new course (only for teachers with 'full' permission)"""
    user = request.user
    teacher, _ = Teacher.objects.get_or_create(user=user)
    
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
            assigned_by=user
        )
        
        messages.success(request, f'Course "{course.title}" created successfully!')
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
    teacher, _ = Teacher.objects.get_or_create(user=user)
    
    # Check permissions
    assignment = CourseTeacher.objects.filter(teacher=teacher, course=course).first()
    if not assignment or assignment.permission_level == 'view_only':
        messages.error(request, 'You do not have permission to edit this course.')
        return redirect('teacher_courses')
    
    if request.method == 'POST':
        course.title = request.POST.get('title', course.title)
        course.description = request.POST.get('description', course.description)
        course.short_description = request.POST.get('short_description', course.short_description)
        course.outcome = request.POST.get('outcome', course.outcome)
        course.category_id = request.POST.get('category') or course.category_id
        course.level = request.POST.get('level', course.level)
        course.course_type = request.POST.get('course_type', course.course_type)
        course.price = float(request.POST.get('price', course.price))
        course.is_free = request.POST.get('is_free') == 'on'
        course.status = request.POST.get('status', course.status)
        
        if request.FILES.get('thumbnail'):
            course.thumbnail = request.FILES.get('thumbnail')
        
        course.save()
        messages.success(request, 'Course updated successfully!')
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
    teacher, _ = Teacher.objects.get_or_create(user=user)
    
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
    teacher, _ = Teacher.objects.get_or_create(user=user)
    
    # Check permissions
    assignment = CourseTeacher.objects.filter(teacher=teacher, course=course).first()
    if not assignment or assignment.permission_level == 'view_only':
        messages.error(request, 'You do not have permission to create lessons.')
        return redirect('teacher_courses')
    
    if request.method == 'POST':
        module_id = request.POST.get('module')
        module = get_object_or_404(Module, id=module_id, course=course)
        
        lesson = Lesson.objects.create(
            module=module,
            title=request.POST.get('title'),
            description=request.POST.get('description', ''),
            content_type=request.POST.get('content_type', 'video'),
            video_url=request.POST.get('video_url', ''),
            text_content=request.POST.get('text_content', ''),
            order=int(request.POST.get('order', 0)),
            estimated_minutes=int(request.POST.get('estimated_minutes', 10))
        )
        
        messages.success(request, 'Lesson created successfully!')
        return redirect('teacher_lessons', course_id=course.id)
    
    modules = course.modules.all()
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
    teacher, _ = Teacher.objects.get_or_create(user=user)
    
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
    teacher, _ = Teacher.objects.get_or_create(user=user)
    
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
    teacher, _ = Teacher.objects.get_or_create(user=user)
    
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
    teacher, _ = Teacher.objects.get_or_create(user=user)
    
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
    teacher, _ = Teacher.objects.get_or_create(user=user)
    
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
        return redirect('teacher_quiz_questions', course_id=course.id, quiz_id=quiz.id)
    
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
    teacher, _ = Teacher.objects.get_or_create(user=user)
    
    # Check permissions
    assignment = CourseTeacher.objects.filter(teacher=teacher, course=course).first()
    if not assignment or assignment.permission_level == 'view_only':
        messages.error(request, 'You do not have permission to delete quizzes.')
        return redirect('teacher_courses')
    
    quiz.delete()
    messages.success(request, 'Quiz deleted successfully!')
    return redirect('teacher_quizzes', course_id=course.id)


@login_required
def teacher_quiz_questions(request, course_id, quiz_id):
    """Manage quiz questions"""
    course = get_object_or_404(Course, id=course_id)
    quiz = get_object_or_404(Quiz, id=quiz_id, course=course)
    user = request.user
    teacher, _ = Teacher.objects.get_or_create(user=user)
    
    # Check permissions
    assignment = CourseTeacher.objects.filter(teacher=teacher, course=course).first()
    if not assignment or assignment.permission_level == 'view_only':
        messages.error(request, 'You do not have permission to manage quiz questions.')
        return redirect('teacher_courses')
    
    questions = quiz.questions.prefetch_related('answers').order_by('order')
    
    if request.method == 'POST':
        # Add new question
        question = Question.objects.create(
            quiz=quiz,
            question_text=request.POST.get('question_text'),
            question_type=request.POST.get('question_type', 'multiple_choice'),
            explanation=request.POST.get('explanation', ''),
            points=int(request.POST.get('points', 1)),
            order=int(request.POST.get('order', questions.count()))
        )
        
        # Add answers
        answers_data = request.POST.getlist('answers[]')
        is_correct_data = request.POST.getlist('is_correct[]')
        
        for i, answer_text in enumerate(answers_data):
            if answer_text.strip():
                Answer.objects.create(
                    question=question,
                    answer_text=answer_text,
                    is_correct=str(i) in is_correct_data,
                    order=i
                )
        
        messages.success(request, 'Question added successfully!')
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
    teacher, _ = Teacher.objects.get_or_create(user=user)
    
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
    teacher, _ = Teacher.objects.get_or_create(user=user)
    
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
    teacher, _ = Teacher.objects.get_or_create(user=user)
    
    live_classes = LiveClassSession.objects.filter(teacher=teacher).select_related('course').order_by('-scheduled_start')
    
    # Filters
    status = request.GET.get('status')
    if status:
        live_classes = live_classes.filter(status=status)
    
    if request.method == 'POST':
        # Create new live class
        course_id = request.POST.get('course')
        course = get_object_or_404(Course, id=course_id)
        
        # Check if teacher has permission
        assignment = CourseTeacher.objects.filter(teacher=teacher, course=course).first()
        if not assignment or not assignment.can_create_live_classes:
            messages.error(request, 'You do not have permission to create live classes for this course.')
            return redirect('teacher_schedule')
        
        from datetime import datetime
        scheduled_start_str = request.POST.get('scheduled_start')
        if 'T' in scheduled_start_str:
            scheduled_start = datetime.fromisoformat(scheduled_start_str.replace('Z', '+00:00'))
        else:
            scheduled_start = datetime.strptime(scheduled_start_str, '%Y-%m-%d %H:%M:%S')
        
        live_class = LiveClassSession.objects.create(
            course=course,
            teacher=teacher,
            title=request.POST.get('title'),
            description=request.POST.get('description', ''),
            scheduled_start=scheduled_start,
            duration_minutes=int(request.POST.get('duration_minutes', 60)),
            zoom_link=request.POST.get('zoom_link', ''),
            google_meet_link=request.POST.get('google_meet_link', ''),
            meeting_id=request.POST.get('meeting_id', ''),
            meeting_password=request.POST.get('meeting_password', ''),
            max_attendees=int(request.POST.get('max_attendees', 0)) or None
        )
        
        messages.success(request, 'Live class scheduled successfully!')
        return redirect('teacher_schedule')
    
    # Get assigned courses for dropdown
    assigned_courses = CourseTeacher.objects.filter(
        teacher=teacher,
        can_create_live_classes=True
    ).select_related('course')
    
    context = {
        'live_classes': live_classes,
        'assigned_courses': assigned_courses,
        'selected_status': status,
    }
    return render(request, 'teacher/schedule.html', context)


@login_required
def teacher_live_classes(request, course_id):
    """Live classes for a specific course"""
    course = get_object_or_404(Course, id=course_id)
    user = request.user
    teacher, _ = Teacher.objects.get_or_create(user=user)
    
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
    teacher, _ = Teacher.objects.get_or_create(user=user)
    
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
    teacher, _ = Teacher.objects.get_or_create(user=user)
    
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
    teacher, _ = Teacher.objects.get_or_create(user=user)
    
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
    
    # Check if user is admin in preview mode or actual partner
    is_admin_preview = profile.role == 'admin' and request.session.get('preview_role') == 'partner'
    
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
    
    # Check if user is admin in preview mode
    is_admin_preview = profile.role == 'admin' and request.session.get('preview_role') == 'partner'
    
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
    
    is_admin_preview = profile.role == 'admin' and request.session.get('preview_role') == 'partner'
    
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
    
    is_admin_preview = profile.role == 'admin' and request.session.get('preview_role') == 'partner'
    
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
    
    is_admin_preview = profile.role == 'admin' and request.session.get('preview_role') == 'partner'
    
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
    
    is_admin_preview = profile.role == 'admin' and request.session.get('preview_role') == 'partner'
    
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
    
    is_admin_preview = profile.role == 'admin' and request.session.get('preview_role') == 'partner'
    
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
    teacher, _ = Teacher.objects.get_or_create(user=user)
    
    # Get all availability slots
    availability_slots = TeacherAvailability.objects.filter(teacher=teacher).order_by('day_of_week', 'start_time')
    
    # Get teacher's courses for course-specific availability
    courses = Course.objects.filter(instructor=user).order_by('title')
    
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
            
            start_datetime = datetime.fromisoformat(start_datetime_str.replace('Z', '+00:00')) if start_datetime_str else None
            end_datetime = datetime.fromisoformat(end_datetime_str.replace('Z', '+00:00')) if end_datetime_str else None
            
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
            day_of_week = int(request.POST.get('day_of_week'))
            start_time = request.POST.get('start_time')
            end_time = request.POST.get('end_time')
            valid_from = request.POST.get('valid_from') or None
            valid_until = request.POST.get('valid_until') or None
            
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
    teacher, _ = Teacher.objects.get_or_create(user=user)
    
    # Get all availability slots
    availability_slots = TeacherAvailability.objects.filter(teacher=teacher).order_by('day_of_week', 'start_time', 'start_datetime')
    
    # Get all live class sessions
    live_sessions = LiveClassSession.objects.filter(teacher=teacher).select_related('course').order_by('scheduled_start')
    
    # Get all bookings
    bookings = Booking.objects.filter(session__teacher=teacher).select_related('session', 'user').order_by('session__scheduled_start')
    
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
    teacher, _ = Teacher.objects.get_or_create(user=request.user)
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
    """Book a live class session"""
    user = request.user
    session = get_object_or_404(LiveClassSession, id=session_id)
    
    # Check if user is enrolled in the course
    enrollment = Enrollment.objects.filter(user=user, course=session.course, status='active').first()
    if not enrollment:
        messages.error(request, 'You must be enrolled in this course to book a session.')
        return redirect('student_course_detail', slug=session.course.slug)
    
    # Check if session can be booked
    can_book, message = session.can_be_booked(user)
    if not can_book:
        messages.error(request, message)
        return redirect('student_course_detail', slug=session.course.slug)
    
    if request.method == 'POST':
        student_notes = request.POST.get('student_notes', '')
        
        # Check for conflicts (user already has a booking at this time)
        conflicting_bookings = Booking.objects.filter(
            user=user,
            session__scheduled_start__date=session.scheduled_start.date(),
            session__scheduled_start__time__gte=session.scheduled_start.time(),
            session__scheduled_start__time__lt=session.scheduled_end.time(),
            status__in=['confirmed', 'pending']
        ).exclude(session=session)
        
        if conflicting_bookings.exists():
            messages.error(request, 'You already have a booking at this time.')
            return redirect('student_course_detail', slug=session.course.slug)
        
        # Determine booking status
        if session.max_attendees and session.available_spots <= 0:
            status = 'waitlisted'
        else:
            status = 'confirmed'
        
        booking = Booking.objects.create(
            user=user,
            session=session,
            status=status,
            student_notes=student_notes
        )
        
        if status == 'confirmed':
            booking.confirm()
            messages.success(request, f'Successfully booked "{session.title}"!')
        else:
            messages.info(request, f'Added to waitlist for "{session.title}". You will be notified if a spot becomes available.')
        
        # Create notification
        Notification.objects.create(
            user=user,
            notification_type='booking_confirmed' if status == 'confirmed' else 'booking_waitlisted',
            title=f'Booking {status.title()}',
            message=f'Your booking for "{session.title}" is {status}.'
        )
        
        return redirect('student_bookings')
    
    context = {
        'session': session,
        'enrollment': enrollment,
    }
    return render(request, 'student/book_session.html', context)


@login_required
def student_bookings(request):
    """View all student bookings"""
    user = request.user
    bookings = Booking.objects.filter(user=user).select_related('session', 'session__course', 'session__teacher__user').order_by('-booked_at')
    
    # Separate by status
    upcoming_bookings = bookings.filter(session__scheduled_start__gte=timezone.now(), status__in=['confirmed', 'waitlisted'])
    past_bookings = bookings.filter(Q(session__scheduled_start__lt=timezone.now()) | Q(status__in=['cancelled', 'attended', 'no_show']))
    
    context = {
        'upcoming_bookings': upcoming_bookings,
        'past_bookings': past_bookings,
    }
    return render(request, 'student/bookings.html', context)


@login_required
@require_POST
def student_booking_cancel(request, booking_id):
    """Cancel a booking"""
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    if not booking.can_cancel:
        messages.error(request, 'This booking cannot be cancelled (must be cancelled at least 24 hours before the session).')
        return redirect('student_bookings')
    
    notes = request.POST.get('notes', '')
    booking.cancel(reason='student', notes=notes)
    
    messages.success(request, 'Booking cancelled successfully.')
    
    # Create notification
    Notification.objects.create(
        user=request.user,
        notification_type='booking_cancelled',
        title='Booking Cancelled',
        message=f'Your booking for "{booking.session.title}" has been cancelled.'
    )
    
    return redirect('student_bookings')


@login_required
def student_booking_reschedule(request, booking_id):
    """Reschedule a booking to a different session"""
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    if booking.status not in ['confirmed', 'pending']:
        messages.error(request, 'This booking cannot be rescheduled.')
        return redirect('student_bookings')
    
    # Get available sessions for the same course
    available_sessions = LiveClassSession.objects.filter(
        course=booking.session.course,
        status='scheduled',
        scheduled_start__gte=timezone.now()
    ).exclude(id=booking.session.id).order_by('scheduled_start')
    
    if request.method == 'POST':
        new_session_id = request.POST.get('new_session_id')
        notes = request.POST.get('notes', '')
        
        new_session = get_object_or_404(LiveClassSession, id=new_session_id, course=booking.session.course)
        
        # Check if new session can be booked
        can_book, message = new_session.can_be_booked(request.user)
        if not can_book:
            messages.error(request, message)
            return redirect('student_booking_reschedule', booking_id=booking.id)
        
        new_booking = booking.reschedule_to(new_session, notes)
        
        if new_booking:
            messages.success(request, f'Booking rescheduled to {new_session.scheduled_start.strftime("%B %d, %Y at %I:%M %p")}.')
            
            # Create notification
            Notification.objects.create(
                user=request.user,
                notification_type='booking_rescheduled',
                title='Booking Rescheduled',
                message=f'Your booking has been rescheduled to "{new_session.title}".'
            )
            return redirect('student_bookings')
        else:
            messages.error(request, 'Failed to reschedule booking.')
    
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
    """View all bookings for a session (teacher view)"""
    session = get_object_or_404(LiveClassSession, id=session_id, teacher__user=request.user)
    bookings = Booking.objects.filter(session=session).select_related('user', 'user__profile').order_by('booked_at')
    
    context = {
        'session': session,
        'bookings': bookings,
    }
    return render(request, 'teacher/session_bookings.html', context)


@login_required
@require_POST
def teacher_booking_cancel(request, booking_id):
    """Teacher cancels a booking"""
    booking = get_object_or_404(Booking, id=booking_id)
    session = booking.session
    
    # Check if user is teacher for this session
    if session.teacher.user != request.user:
        messages.error(request, 'You do not have permission to cancel this booking.')
        return redirect('teacher_live_classes', course_id=session.course.id)
    
    notes = request.POST.get('notes', '')
    booking.cancel(reason='teacher', notes=notes)
    
    messages.success(request, 'Booking cancelled successfully.')
    
    # Create notification for student
    Notification.objects.create(
        user=booking.user,
        notification_type='booking_cancelled',
        title='Booking Cancelled by Teacher',
        message=f'Your booking for "{session.title}" has been cancelled by the teacher.'
    )
    
    return redirect('teacher_session_bookings', session_id=session.id)


@login_required
@require_POST
def teacher_mark_attendance(request, booking_id):
    """Mark student attendance"""
    booking = get_object_or_404(Booking, id=booking_id)
    session = booking.session
    
    # Check if user is teacher for this session
    if session.teacher.user != request.user:
        messages.error(request, 'You do not have permission to mark attendance.')
        return redirect('teacher_live_classes', course_id=session.course.id)
    
    attended = request.POST.get('attended') == 'true'
    booking.attended = attended
    booking.status = 'attended' if attended else 'no_show'
    booking.attended_at = timezone.now() if attended else None
    booking.save()
    
    messages.success(request, f'Attendance marked as {"Attended" if attended else "No Show"}.')
    return redirect('teacher_session_bookings', session_id=session.id)
