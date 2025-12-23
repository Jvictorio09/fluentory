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
    UserProfile, Category, Course, Module, Lesson,
    Quiz, Question, Answer, Enrollment, LessonProgress, QuizAttempt,
    Certificate, PlacementTest, TutorConversation, TutorMessage,
    Partner, Cohort, CohortMembership, Payment, Review, FAQ,
    Notification, SiteSettings, Media
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
    """Decorator to check user role. Allows superusers/admins even without profile."""
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            
            # Allow superusers/staff to access admin views even without profile
            if 'admin' in allowed_roles and (request.user.is_superuser or request.user.is_staff):
                return view_func(request, *args, **kwargs)
            
            # Get or create profile
            profile = get_or_create_profile(request.user)
            
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
    if request.user.is_authenticated:
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
    return redirect('home')


def redirect_by_role(user):
    """Redirect user based on their role"""
    # Allow superusers/staff to access admin dashboard
    if user.is_superuser or user.is_staff:
        return redirect('dashboard:overview')
    
    profile = get_or_create_profile(user)
    role = profile.role
    if role == 'admin':
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
    
    context = {
        'courses': courses,
        'categories': categories,
        'enrolled_course_ids': enrolled_course_ids,
        'selected_level': level,
        'selected_category': category_slug,
        'search_query': search,
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
    
    context = {
        'course': course,
        'enrollment': enrollment,
        'modules': modules,
        'reviews': reviews,
        'similar_courses': similar_courses,
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
    ).select_related('course', 'current_lesson').order_by('-enrolled_at')
    
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
    if conversation:
        tutor_messages = conversation.messages.all()[:20]
    
    context = {
        'enrollment': enrollment,
        'course': course,
        'current_lesson': current_lesson,
        'progress': progress,
        'modules': modules,
        'completed_lesson_ids': completed_lesson_ids,
        'tutor_messages': tutor_messages,
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
    """AI Tutor chat endpoint"""
    data = json.loads(request.body)
    message = data.get('message')
    lesson_id = data.get('lesson_id')
    conversation_id = data.get('conversation_id')
    
    user = request.user
    lesson = get_object_or_404(Lesson, id=lesson_id) if lesson_id else None
    
    # Get or create conversation
    if conversation_id:
        conversation = get_object_or_404(TutorConversation, id=conversation_id, user=user)
    else:
        conversation = TutorConversation.objects.create(
            user=user,
            lesson=lesson,
            course=lesson.module.course if lesson else None,
            title=f"Chat about {lesson.title}" if lesson else "General Chat"
        )
    
    # Save user message
    TutorMessage.objects.create(
        conversation=conversation,
        role='user',
        content=message
    )
    
    # Get conversation history
    history = conversation.messages.all().order_by('created_at')[:10]
    
    # Build context
    context_text = ""
    if lesson:
        context_text = f"""
        Course: {lesson.module.course.title}
        Module: {lesson.module.title}
        Lesson: {lesson.title}
        Lesson Content: {lesson.text_content[:1000] if lesson.text_content else 'Video lesson'}
        """
    
    # Build messages for OpenAI
    messages_for_ai = [
        {
            "role": "system",
            "content": f"""You are a helpful AI tutor for Fluentory, an online learning platform.
            Be encouraging, clear, and concise. Help students understand concepts from their lessons.
            Current context: {context_text}
            """
        }
    ]
    
    for msg in history:
        messages_for_ai.append({
            "role": msg.role if msg.role != 'assistant' else 'assistant',
            "content": msg.content
        })
    
    # Call OpenAI
    try:
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages_for_ai,
            max_tokens=500,
            temperature=0.7
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
# PARTNER VIEWS
# ============================================

@login_required
@role_required(['partner'])
def partner_overview(request):
    """Partner dashboard"""
    user = request.user
    partner = get_object_or_404(Partner, user=user)
    
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
    
    context = {
        'partner': partner,
        'cohorts': cohorts,
        'total_students': total_students,
        'active_learners': active_learners,
        'completion_rate': completion_rate,
        'certificates_earned': certificates_earned,
        'total_revenue': total_revenue,
        'commission': commission,
    }
    return render(request, 'partner/overview.html', context)


@login_required
@role_required(['partner'])
def partner_cohorts(request):
    """Partner cohort management"""
    partner = get_object_or_404(Partner, user=request.user)
    cohorts = partner.cohorts.prefetch_related('courses', 'students').order_by('-start_date')
    
    context = {
        'partner': partner,
        'cohorts': cohorts,
    }
    return render(request, 'partner/cohorts.html', context)


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
