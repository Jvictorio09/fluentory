from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import timedelta
import uuid
import qrcode
from io import BytesIO
from django.core.files import File


# ============================================
# USER PROFILES & ROLES
# ============================================

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('admin', 'Admin'),
        ('partner', 'Partner'),
        ('instructor', 'Instructor'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    bio = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, blank=True)
    preferred_language = models.CharField(max_length=10, default='en')
    timezone = models.CharField(max_length=50, default='UTC')
    
    # Learning preferences
    learning_goal = models.TextField(blank=True)
    daily_goal_minutes = models.PositiveIntegerField(default=30)
    
    # Streak tracking
    current_streak = models.PositiveIntegerField(default=0)
    longest_streak = models.PositiveIntegerField(default=0)
    last_activity_date = models.DateField(null=True, blank=True)
    total_learning_minutes = models.PositiveIntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.role}"
    
    def update_streak(self):
        """Update learning streak based on activity"""
        today = timezone.now().date()
        if self.last_activity_date:
            days_diff = (today - self.last_activity_date).days
            if days_diff == 1:
                self.current_streak += 1
            elif days_diff > 1:
                self.current_streak = 1
        else:
            self.current_streak = 1
        
        self.longest_streak = max(self.longest_streak, self.current_streak)
        self.last_activity_date = today
        self.save()


# ============================================
# TEACHERS
# ============================================

class Teacher(models.Model):
    """Teacher profile with approval status"""
    PERMISSION_LEVEL_CHOICES = [
        ('standard', 'Standard'),
        ('premium', 'Premium'),
        ('admin', 'Admin'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher_profile')
    
    # Permission level
    permission_level = models.CharField(
        max_length=20,
        choices=PERMISSION_LEVEL_CHOICES,
        default='standard',
        help_text='Permission level for the teacher'
    )
    
    # Status
    is_approved = models.BooleanField(default=False)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_teachers')
    
    # Online status
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(null=True, blank=True)
    online_status_updated_at = models.DateTimeField(null=True, blank=True, help_text='When online status was last updated')
    
    # Bio
    bio = models.TextField(blank=True)
    specialization = models.CharField(max_length=200, blank=True)
    years_experience = models.PositiveIntegerField(default=0)
    
    # Profile Photo (stored as Cloudinary URL)
    photo_url = models.URLField(blank=True, null=True, help_text='Profile photo URL from Cloudinary')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - Teacher"
    
    def update_online_status(self, is_online_value):
        """Update online status and timestamp"""
        from django.utils import timezone
        self.is_online = is_online_value
        self.last_seen = timezone.now()
        self.online_status_updated_at = timezone.now()
        self.save(update_fields=['is_online', 'last_seen', 'online_status_updated_at'])
    
    @property
    def is_recently_online(self):
        """Check if teacher was online in the last 15 minutes"""
        from django.utils import timezone
        from datetime import timedelta
        if not self.last_seen:
            return False
        return self.last_seen > timezone.now() - timedelta(minutes=15)


class CourseTeacher(models.Model):
    """Course-Teacher relationship with permissions"""
    PERMISSION_CHOICES = [
        ('view_only', 'View Only'),
        ('edit', 'Can Edit'),
        ('full', 'Full Access'),
    ]
    
    course = models.ForeignKey('Course', on_delete=models.CASCADE, related_name='course_teachers')
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='course_assignments')
    
    # Permissions
    permission_level = models.CharField(max_length=20, choices=PERMISSION_CHOICES, default='view_only')
    can_create_live_classes = models.BooleanField(default=False)
    can_manage_schedule = models.BooleanField(default=False, help_text='Can manage schedule and availability for this course')
    requires_booking_approval = models.BooleanField(null=True, blank=True, help_text='Override course-level approval setting for this teacher. If null, uses course setting.')
    
    # Timestamps
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        unique_together = ['course', 'teacher']
    
    def __str__(self):
        return f"{self.teacher.user.username} - {self.course.title} ({self.permission_level})"
    
    def get_requires_approval(self):
        """Get approval requirement, checking teacher override first, then course setting"""
        if self.requires_booking_approval is not None:
            return self.requires_booking_approval
        return self.course.requires_booking_approval


# ============================================
# COURSES & CONTENT
# ============================================

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, default='fa-book')  # FontAwesome icon class
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name


class Course(models.Model):
    LEVEL_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ]
    
    COURSE_TYPE_CHOICES = [
        ('recorded', 'Recorded'),
        ('live', 'Live'),
        ('hybrid', 'Hybrid'),
    ]
    
    BOOKING_TYPE_CHOICES = [
        ('none', 'No Booking System'),
        ('group_session', 'Group Session (Seat-Based)'),
        ('one_on_one', '1:1 Booking (Availability-Based)'),
    ]
    
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    short_description = models.CharField(max_length=300)  # For cards
    outcome = models.CharField(max_length=300)  # What students will achieve
    
    # Media
    thumbnail = models.ImageField(upload_to='courses/thumbnails/', blank=True, null=True)
    preview_video = models.URLField(blank=True)  # 30-sec preview URL
    
    # Classification
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='courses')
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='beginner')
    course_type = models.CharField(max_length=20, choices=COURSE_TYPE_CHOICES, default='recorded', help_text='Type of course: Recorded (self-paced), Live (scheduled sessions), or Hybrid (combination)')
    
    # Booking System
    booking_type = models.CharField(max_length=20, choices=BOOKING_TYPE_CHOICES, default='none', help_text='Type of booking system enabled for this course: Group Session (seat-based) or 1:1 (availability-based)')
    requires_booking_approval = models.BooleanField(default=False, help_text='For 1:1 bookings: Requires teacher approval before confirmation')
    
    # Instructor
    instructor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='courses_taught')
    
    # Pricing
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='USD')
    is_free = models.BooleanField(default=False)
    
    # Duration & Content
    estimated_hours = models.PositiveIntegerField(default=10)
    lessons_count = models.PositiveIntegerField(default=0)  # Computed field
    
    # Languages
    language = models.CharField(max_length=10, default='en')
    available_languages = models.JSONField(default=list)  # ['en', 'es', 'fr']
    
    # Features
    has_certificate = models.BooleanField(default=True)
    has_ai_tutor = models.BooleanField(default=True)
    has_quizzes = models.BooleanField(default=True)
    
    # Status & SEO
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    meta_title = models.CharField(max_length=70, blank=True)
    meta_description = models.CharField(max_length=160, blank=True)
    
    # Stats (updated periodically)
    enrolled_count = models.PositiveIntegerField(default=0)
    completion_rate = models.FloatField(default=0)  # Percentage
    average_rating = models.FloatField(default=0, validators=[MinValueValidator(0), MaxValueValidator(5)])
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    def update_lesson_count(self):
        self.lessons_count = self.modules.aggregate(
            total=models.Sum('lessons__id')
        )['total'] or 0
        self.save()
    
    def get_price(self, currency='USD'):
        """Get price in specified currency, fallback to default currency"""
        if self.is_free:
            return 0
        
        # Try to get multi-currency pricing
        try:
            pricing = self.pricing.get(currency=currency)
            return float(pricing.price)
        except:
            # Fallback to default currency if available
            if currency == self.currency:
                return float(self.price)
            # Try to get default currency pricing
            try:
                default_pricing = self.pricing.get(currency=self.currency)
                return float(default_pricing.price)
            except:
                # Final fallback to model's price field
                return float(self.price)
    
    def has_currency_price(self, currency):
        """Check if course has a price set for a specific currency"""
        if self.is_free:
            return True
        return self.pricing.filter(currency=currency).exists()


class CoursePricing(models.Model):
    """Multi-currency pricing for courses"""
    CURRENCY_CHOICES = [
        ('USD', 'USD - US Dollar'),
        ('EUR', 'EUR - Euro'),
        ('SAR', 'SAR - Saudi Riyal'),
        ('AED', 'AED - UAE Dirham'),
        ('JOD', 'JOD - Jordanian Dinar'),
        ('GBP', 'GBP - British Pound'),
    ]
    
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='pricing')
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['course', 'currency']
        verbose_name = 'Course Pricing'
        verbose_name_plural = 'Course Pricing'
        ordering = ['currency']
    
    def __str__(self):
        return f"{self.course.title} - {self.currency} {self.price}"


class Module(models.Model):
    """Course modules/chapters"""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    
    # Unlock conditions
    is_locked = models.BooleanField(default=False)
    unlock_after_module = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.course.title} - {self.title}"


class Lesson(models.Model):
    CONTENT_TYPE_CHOICES = [
        ('video', 'Video'),
        ('text', 'Text/Article'),
        ('quiz', 'Quiz'),
        ('assignment', 'Assignment'),
        ('interactive', 'Interactive'),
    ]
    
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPE_CHOICES, default='video')
    
    # Content
    video_url = models.URLField(blank=True)
    video_duration = models.PositiveIntegerField(default=0)  # In seconds
    text_content = models.TextField(blank=True)  # Rich text/HTML
    
    # Order & Settings
    order = models.PositiveIntegerField(default=0)
    estimated_minutes = models.PositiveIntegerField(default=10)
    is_preview = models.BooleanField(default=False)  # Free preview lesson
    
    # Unlock conditions
    is_milestone = models.BooleanField(default=False)
    unlock_quiz = models.ForeignKey('Quiz', on_delete=models.SET_NULL, null=True, blank=True, related_name='unlocking_lesson')
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.module.title} - {self.title}"


# ============================================
# QUIZZES & ASSESSMENTS
# ============================================

class Quiz(models.Model):
    QUIZ_TYPE_CHOICES = [
        ('lesson', 'Lesson Quiz'),
        ('module', 'Module Quiz'),
        ('final', 'Final Assessment'),
        ('placement', 'Placement Test'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    quiz_type = models.CharField(max_length=20, choices=QUIZ_TYPE_CHOICES, default='lesson')
    
    # Association
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True, related_name='quizzes')
    module = models.ForeignKey(Module, on_delete=models.CASCADE, null=True, blank=True, related_name='quizzes')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, null=True, blank=True, related_name='quizzes')
    
    # Settings
    passing_score = models.PositiveIntegerField(default=70)  # Percentage
    time_limit_minutes = models.PositiveIntegerField(null=True, blank=True)
    max_attempts = models.PositiveIntegerField(default=3)
    randomize_questions = models.BooleanField(default=True)
    show_correct_answers = models.BooleanField(default=True)
    
    # Stats
    total_attempts = models.PositiveIntegerField(default=0)
    pass_rate = models.FloatField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = 'Quizzes'
    
    def __str__(self):
        return self.title


class Question(models.Model):
    QUESTION_TYPE_CHOICES = [
        ('multiple_choice', 'Multiple Choice'),
        ('true_false', 'True/False'),
        ('fill_blank', 'Fill in the Blank'),
        ('matching', 'Matching'),
        ('short_answer', 'Short Answer'),
    ]
    
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPE_CHOICES, default='multiple_choice')
    explanation = models.TextField(blank=True)  # Shown after answering
    points = models.PositiveIntegerField(default=1)
    order = models.PositiveIntegerField(default=0)
    
    # For AI tutor integration
    hint = models.TextField(blank=True)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.quiz.title} - Q{self.order}"


class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    answer_text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.answer_text[:50]}..."


# ============================================
# ENROLLMENTS & PROGRESS
# ============================================

class Enrollment(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('paused', 'Paused'),
        ('expired', 'Expired'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    progress_percentage = models.FloatField(default=0)
    
    # Current position
    current_module = models.ForeignKey(Module, on_delete=models.SET_NULL, null=True, blank=True)
    current_lesson = models.ForeignKey(Lesson, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Access control
    enrolled_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Gifted/Partner access
    is_gifted = models.BooleanField(default=False)
    gifted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='gifts_sent')
    partner = models.ForeignKey('Partner', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Notes (for teacher/admin use)
    teacher_notes = models.TextField(blank=True, default='', help_text='Teacher notes (internal)')
    
    class Meta:
        unique_together = ['user', 'course']
    
    def __str__(self):
        return f"{self.user.username} - {self.course.title}"
    
    def update_progress(self):
        """Calculate and update progress percentage"""
        total_lessons = Lesson.objects.filter(module__course=self.course).count()
        completed_lessons = LessonProgress.objects.filter(
            enrollment=self,
            completed=True
        ).count()
        
        if total_lessons > 0:
            self.progress_percentage = (completed_lessons / total_lessons) * 100
            if self.progress_percentage >= 100:
                self.status = 'completed'
                self.completed_at = timezone.now()
            self.save()


class LessonProgress(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name='lesson_progress')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    
    # Progress
    started_at = models.DateTimeField(auto_now_add=True)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Video progress
    video_position = models.PositiveIntegerField(default=0)  # Seconds
    time_spent = models.PositiveIntegerField(default=0)  # Seconds
    
    # Notes
    notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['enrollment', 'lesson']
    
    def __str__(self):
        return f"{self.enrollment.user.username} - {self.lesson.title}"
    
    def mark_complete(self):
        self.completed = True
        self.completed_at = timezone.now()
        self.save()
        self.enrollment.update_progress()


class QuizAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_attempts')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, null=True, blank=True)
    
    # Results
    score = models.FloatField(default=0)  # Percentage
    passed = models.BooleanField(default=False)
    
    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    time_taken = models.PositiveIntegerField(default=0)  # Seconds
    
    # Answers stored as JSON
    answers = models.JSONField(default=dict)  # {question_id: answer_id}
    
    def __str__(self):
        return f"{self.user.username} - {self.quiz.title} - {self.score}%"


# ============================================
# CERTIFICATES
# ============================================

class Certificate(models.Model):
    certificate_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='certificates')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='certificates')
    enrollment = models.OneToOneField(Enrollment, on_delete=models.CASCADE, null=True, blank=True)
    
    # Certificate details
    issued_at = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=300)  # "Certificate of Completion"
    
    # QR Code
    qr_code = models.ImageField(upload_to='certificates/qr/', blank=True, null=True)
    verification_url = models.URLField(blank=True)
    
    # PDF
    pdf_file = models.FileField(upload_to='certificates/pdf/', blank=True, null=True)
    
    # Verification
    is_verified = models.BooleanField(default=True)
    verified_count = models.PositiveIntegerField(default=0)  # How many times verified
    
    class Meta:
        unique_together = ['user', 'course']
    
    def __str__(self):
        return f"{self.user.username} - {self.course.title}"
    
    def generate_qr_code(self, base_url='https://fluentory.com'):
        """Generate QR code for certificate verification"""
        self.verification_url = f"{base_url}/verify/{self.certificate_id}/"
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(self.verification_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        
        self.qr_code.save(f'qr_{self.certificate_id}.png', File(buffer), save=False)
        self.save()


# ============================================
# PLACEMENT TESTS
# ============================================

class PlacementTest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='placement_tests')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)  # The placement quiz
    
    # Results
    score = models.FloatField(default=0)
    recommended_level = models.CharField(max_length=20)  # beginner/intermediate/advanced
    
    # Recommendations
    recommended_courses = models.ManyToManyField(Course, blank=True)
    
    # Timing
    taken_at = models.DateTimeField(auto_now_add=True)
    
    # Detailed results as JSON
    category_scores = models.JSONField(default=dict)  # {category: score}
    
    def __str__(self):
        return f"{self.user.username} - {self.recommended_level}"


# ============================================
# AI TUTOR
# ============================================

class TutorConversation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tutor_conversations')
    lesson = models.ForeignKey(Lesson, on_delete=models.SET_NULL, null=True, blank=True)
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Context
    title = models.CharField(max_length=200, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Settings
    language = models.CharField(max_length=10, default='en')
    
    def __str__(self):
        return f"{self.user.username} - {self.title or 'Conversation'}"


class TutorMessage(models.Model):
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'AI Tutor'),
        ('system', 'System'),
    ]
    
    conversation = models.ForeignKey(TutorConversation, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Token tracking
    tokens_used = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."


class AITutorSettings(models.Model):
    """AI Tutor configuration settings for a course - configurable by teachers"""
    
    MODEL_CHOICES = [
        ('gpt-4o-mini', 'GPT-4o Mini (Fast & Efficient)'),
        ('gpt-4o', 'GPT-4o (More Capable)'),
        ('gpt-3.5-turbo', 'GPT-3.5 Turbo (Legacy)'),
    ]
    
    PERSONALITY_CHOICES = [
        ('friendly', 'Friendly & Encouraging'),
        ('professional', 'Professional & Formal'),
        ('casual', 'Casual & Conversational'),
        ('enthusiastic', 'Enthusiastic & Motivational'),
        ('patient', 'Patient & Supportive'),
        ('custom', 'Custom (Use Custom Prompt)'),
    ]
    
    course = models.OneToOneField(Course, on_delete=models.CASCADE, related_name='ai_tutor_settings')
    
    # Model Configuration
    model = models.CharField(max_length=50, choices=MODEL_CHOICES, default='gpt-4o-mini', 
                            help_text='OpenAI model to use for AI tutor')
    temperature = models.FloatField(default=0.7, validators=[MinValueValidator(0.0), MaxValueValidator(2.0)],
                                   help_text='Creativity level (0.0 = focused, 2.0 = creative)')
    max_tokens = models.PositiveIntegerField(default=500, 
                                            help_text='Maximum tokens in AI response')
    
    # Personality & Prompt
    personality = models.CharField(max_length=20, choices=PERSONALITY_CHOICES, default='friendly',
                                  help_text='Default personality style for the AI tutor')
    custom_system_prompt = models.TextField(blank=True,
                                           help_text='Custom system prompt (overrides personality if set). Use {course_title}, {lesson_title} as placeholders.')
    custom_instructions = models.TextField(blank=True,
                                          help_text='Additional instructions for the AI tutor (e.g., teaching style, focus areas)')
    
    # Behavior Settings
    include_lesson_context = models.BooleanField(default=True,
                                                 help_text='Include lesson content in AI context')
    include_course_context = models.BooleanField(default=True,
                                                help_text='Include course description in AI context')
    max_conversation_history = models.PositiveIntegerField(default=10,
                                                          help_text='Number of previous messages to include in context')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='ai_settings_updated')
    
    class Meta:
        verbose_name = 'AI Tutor Settings'
        verbose_name_plural = 'AI Tutor Settings'
    
    def __str__(self):
        return f"AI Settings for {self.course.title}"
    
    def get_system_prompt(self, lesson=None):
        """Generate system prompt based on personality or custom prompt"""
        if self.custom_system_prompt:
            prompt = self.custom_system_prompt
            # Replace placeholders
            prompt = prompt.replace('{course_title}', self.course.title)
            if lesson:
                prompt = prompt.replace('{lesson_title}', lesson.title)
            return prompt
        
        # Default prompts based on personality
        base_prompts = {
            'friendly': """You are a friendly and encouraging AI tutor for Fluentory, an online learning platform.
            Be warm, supportive, and patient. Help students understand concepts from their lessons in a clear and approachable way.
            Encourage questions and provide explanations that build confidence.""",
            
            'professional': """You are a professional AI tutor for Fluentory, an online learning platform.
            Provide clear, concise, and structured explanations. Maintain a formal but approachable tone.
            Focus on accuracy and depth of understanding.""",
            
            'casual': """You're a casual and conversational AI tutor for Fluentory, an online learning platform.
            Keep it relaxed and easy-going while still being helpful. Use simple language and relatable examples.
            Make learning feel natural and engaging.""",
            
            'enthusiastic': """You are an enthusiastic and motivational AI tutor for Fluentory, an online learning platform.
            Be energetic and positive! Celebrate progress and encourage students to push forward.
            Use encouraging language and show excitement about their learning journey.""",
            
            'patient': """You are a patient and supportive AI tutor for Fluentory, an online learning platform.
            Take time to explain concepts thoroughly. Be understanding when students struggle.
            Break down complex ideas into simpler parts and offer multiple explanations if needed.""",
        }
        
        prompt = base_prompts.get(self.personality, base_prompts['friendly'])
        
        # Add custom instructions if provided
        if self.custom_instructions:
            prompt += f"\n\nAdditional instructions: {self.custom_instructions}"
        
        return prompt


# ============================================
# PARTNERS & COHORTS
# ============================================

class Partner(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='partner_profile')
    company_name = models.CharField(max_length=200)
    company_logo = models.ImageField(upload_to='partners/logos/', blank=True, null=True)
    
    # Contact
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20, blank=True)
    website = models.URLField(blank=True)
    
    # Revenue sharing
    commission_rate = models.FloatField(default=0.2)  # 20% default
    
    # Stats
    total_students = models.PositiveIntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Status
    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.company_name


class Cohort(models.Model):
    partner = models.ForeignKey(Partner, on_delete=models.CASCADE, related_name='cohorts')
    name = models.CharField(max_length=200)  # e.g., "Dubai Jan 2026"
    description = models.TextField(blank=True)
    
    # Courses/Bundles
    courses = models.ManyToManyField(Course, related_name='cohorts')
    
    # Access window
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    
    # Promo
    promo_code = models.CharField(max_length=50, unique=True, blank=True, null=True)
    discount_percentage = models.PositiveIntegerField(default=0)
    
    # Students
    students = models.ManyToManyField(User, through='CohortMembership', related_name='cohorts')
    
    # Stats
    capacity = models.PositiveIntegerField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.partner.company_name} - {self.name}"


class CohortMembership(models.Model):
    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)
    
    # Progress
    completion_percentage = models.FloatField(default=0)
    certificates_earned = models.PositiveIntegerField(default=0)
    
    class Meta:
        unique_together = ['cohort', 'user']


# ============================================
# PAYMENTS & TRANSACTIONS
# ============================================

class Payment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('card', 'Credit/Debit Card'),
        ('paypal', 'PayPal'),
        ('bank', 'Bank Transfer'),
        ('partner', 'Partner Invoice'),
    ]
    
    payment_id = models.UUIDField(default=uuid.uuid4, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    
    # What they paid for
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Amount
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    
    # External references
    stripe_payment_id = models.CharField(max_length=100, blank=True)
    
    # Partner/Promo
    partner = models.ForeignKey(Partner, on_delete=models.SET_NULL, null=True, blank=True)
    promo_code = models.CharField(max_length=50, blank=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.amount} {self.currency} - {self.status}"


# ============================================
# REVIEWS & RATINGS
# ============================================

class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='reviews')
    
    rating = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    title = models.CharField(max_length=200)
    content = models.TextField()
    
    # Status
    is_approved = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'course']
    
    def __str__(self):
        return f"{self.user.username} - {self.course.title} - {self.rating}★"


# ============================================
# FAQ & SUPPORT
# ============================================

class FAQ(models.Model):
    question = models.CharField(max_length=300)
    answer = models.TextField()
    video_url = models.URLField(blank=True)  # Video answer
    video_thumbnail = models.ImageField(upload_to='faq/thumbnails/', blank=True, null=True)
    
    # Organization
    category = models.CharField(max_length=100, blank=True)
    order = models.PositiveIntegerField(default=0)
    
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order']
        verbose_name = 'FAQ'
        verbose_name_plural = 'FAQs'
    
    def __str__(self):
        return self.question


# ============================================
# NOTIFICATIONS
# ============================================

class Notification(models.Model):
    TYPE_CHOICES = [
        ('milestone', 'Milestone Reached'),
        ('certificate', 'Certificate Earned'),
        ('reminder', 'Learning Reminder'),
        ('announcement', 'Announcement'),
        ('payment', 'Payment Update'),
        ('course', 'Course Update'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Link to action
    action_url = models.URLField(blank=True)
    
    # Status
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"


# ============================================
# LIVE CLASSES
# ============================================

class LiveClassSession(models.Model):
    """Group Session (Seat-Based) - Scheduled live class sessions with seat capacity"""
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('live', 'Live'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('booking_closed', 'Booking Closed'),  # Automatically closed when full
    ]
    
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='live_classes')
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='live_classes')
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Scheduling (Phase 2: Unified UTC-based)
    scheduled_start = models.DateTimeField(help_text='Legacy field - use start_at_utc')
    scheduled_end = models.DateTimeField(null=True, blank=True, help_text='Legacy field - computed as scheduled_start + duration_minutes')
    start_at_utc = models.DateTimeField(null=True, blank=True, help_text='Session start time in UTC')
    end_at_utc = models.DateTimeField(null=True, blank=True, help_text='Session end time in UTC')
    timezone_snapshot = models.CharField(max_length=50, blank=True, help_text='Teacher timezone at creation time (e.g., "America/New_York")')
    duration_minutes = models.PositiveIntegerField(default=60)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    
    # Video conferencing links (Phase 2: Enhanced)
    meeting_provider = models.CharField(max_length=20, choices=[
        ('zoom', 'Zoom'),
        ('google_meet', 'Google Meet'),
        ('microsoft_teams', 'Microsoft Teams'),
        ('custom', 'Custom'),
    ], default='zoom', blank=True)
    # Note: Database has BOTH meeting_link AND meeting_url columns (both NOT NULL)
    # We use meeting_link as the primary field and sync meeting_url via save method
    meeting_link = models.URLField(blank=True, help_text='Zoom / Google Meet / Custom meeting link', default='')
    zoom_link = models.URLField(blank=True)  # Legacy field, use meeting_link instead
    google_meet_link = models.URLField(blank=True)  # Legacy field, use meeting_link instead
    meeting_id = models.CharField(max_length=100, blank=True)
    meeting_passcode = models.CharField(max_length=50, blank=True, help_text='Meeting passcode/password')
    meeting_password = models.CharField(max_length=50, blank=True)  # Legacy field, use meeting_passcode
    
    # Seat-based booking (Group Session) - Phase 2: Unified naming
    total_seats = models.PositiveIntegerField(null=False, default=10, help_text='Total seat capacity for this group session')
    capacity = models.PositiveIntegerField(null=True, blank=True, help_text='Phase 2: Alias for total_seats')
    # Note: Database has BOTH seats_taken AND current_attendees columns (both NOT NULL)
    # We use seats_taken as the primary field and sync current_attendees via save method
    seats_taken = models.PositiveIntegerField(default=0, help_text='Cached count of confirmed bookings (updated via signal)')
    enable_waitlist = models.BooleanField(default=False, help_text='Allow waitlist after all seats are taken')
    reminder_sent = models.BooleanField(default=False, help_text='Whether reminder notification has been sent to attendees')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    
    # Legacy field for backwards compatibility
    max_attendees = models.PositiveIntegerField(null=True, blank=True)
    
    class Meta:
        ordering = ['-scheduled_start']
        verbose_name = 'Group Session'
        verbose_name_plural = 'Group Sessions'
    
    def __str__(self):
        return f"{self.title} - {self.course.title} - {self.scheduled_start}"
    
    def save(self, *args, **kwargs):
        from datetime import timedelta
        
        # Compute scheduled_end if not set (optional, but recommended)
        # scheduled_end is nullable, but we try to compute it from scheduled_start + duration when possible
        # Priority: use explicitly set value, then compute from scheduled_start + duration
        if self.scheduled_start and self.duration_minutes:
            # If scheduled_end is None or not set, compute it
            # Use getattr with default None to check actual value (not just attribute existence)
            current_scheduled_end = getattr(self, 'scheduled_end', None)
            if current_scheduled_end is None:
                # Compute scheduled_end from scheduled_start + duration_minutes
                self.scheduled_end = self.scheduled_start + timedelta(minutes=self.duration_minutes)
        
        # Sync max_attendees with total_seats for backwards compatibility
        if self.max_attendees is None:
            self.max_attendees = self.total_seats
        elif self.total_seats != self.max_attendees:
            # If total_seats is set differently, use it
            self.max_attendees = self.total_seats
        
        # Phase 2: Auto-populate start_at_utc and end_at_utc from scheduled_start if not set
        if self.scheduled_start and not self.start_at_utc:
            # Ensure scheduled_start is timezone-aware for start_at_utc
            if hasattr(self.scheduled_start, 'tzinfo') and self.scheduled_start.tzinfo is None:
                from django.utils import timezone as tz
                # Assume UTC if naive
                self.start_at_utc = tz.make_aware(self.scheduled_start, tz.utc)
            else:
                self.start_at_utc = self.scheduled_start
        
        # Compute end_at_utc if not set
        if self.start_at_utc and not self.end_at_utc:
            self.end_at_utc = self.start_at_utc + timedelta(minutes=self.duration_minutes)
        
        # FINAL CHECK: Try to compute scheduled_end if still not set (use end_at_utc as fallback if needed)
        # This is a safety net in case scheduled_start wasn't available earlier
        # Note: scheduled_end is nullable, so it's okay if it remains None
        if getattr(self, 'scheduled_end', None) is None:
            if self.end_at_utc:
                # Convert end_at_utc to naive datetime for scheduled_end
                self.scheduled_end = self.end_at_utc.replace(tzinfo=None) if hasattr(self.end_at_utc, 'replace') and self.end_at_utc.tzinfo else self.end_at_utc
            elif self.scheduled_start and self.duration_minutes:
                # Last resort: compute from scheduled_start + duration
                self.scheduled_end = self.scheduled_start + timedelta(minutes=self.duration_minutes)
        
        # Sync capacity with total_seats
        if self.capacity is None:
            self.capacity = self.total_seats
        
        # Sync timezone snapshot if not set (use teacher's timezone or default UTC)
        if not self.timezone_snapshot and hasattr(self, 'teacher') and self.teacher:
            # Get teacher's timezone if available, otherwise default to UTC
            self.timezone_snapshot = getattr(self.teacher, 'timezone', 'UTC') or 'UTC'
        
        # CRITICAL: Ensure meeting_link (maps to meeting_url column) is never None
        # meeting_url column in database is NOT NULL, so must have a value (empty string is acceptable)
        # Multiple defensive checks to ensure it's always a string, never None
        if not hasattr(self, 'meeting_link'):
            self.meeting_link = ''
        elif self.meeting_link is None:
            self.meeting_link = ''
        # Final guarantee: convert to string and ensure it's never None or empty (use empty string)
        self.meeting_link = str(self.meeting_link) if self.meeting_link else ''
        
        # CRITICAL: Ensure seats_taken is never None - MUST be set BEFORE super().save()
        # Database has BOTH seats_taken AND current_attendees columns (both NOT NULL)
        # We write to seats_taken directly, then sync current_attendees after save
        if not hasattr(self, 'seats_taken') or self.seats_taken is None:
            self.seats_taken = 0
        # Double-check: ensure it's definitely not None
        if self.seats_taken is None:
            self.seats_taken = 0
        
        # CRITICAL: Ensure reminder_sent is never None
        # reminder_sent column in database is NOT NULL, so must have a value (False for new sessions)
        if not hasattr(self, 'reminder_sent') or self.reminder_sent is None:
            self.reminder_sent = False
        
        # CRITICAL FIX: Database has BOTH meeting_link AND meeting_url columns (both NOT NULL)
        # We write to meeting_link directly (no db_column), then sync meeting_url after save
        meeting_value = self.meeting_link or ''
        
        # Save the model - meeting_link, seats_taken, and reminder_sent are now guaranteed to be set
        # scheduled_end is computed when possible but is nullable
        super().save(*args, **kwargs)
        
        # After save, sync both meeting_url and current_attendees columns
        # This ensures both pairs of columns have the same values
        from django.db import connection
        with connection.cursor() as cursor:
            # Sync meeting_url with meeting_link
            cursor.execute(
                'UPDATE "myApp_liveclasssession" SET "meeting_url" = %s WHERE "id" = %s',
                [meeting_value, self.id]
            )
            # Sync current_attendees with seats_taken
            seats_value = self.seats_taken or 0
            cursor.execute(
                'UPDATE "myApp_liveclasssession" SET "current_attendees" = %s WHERE "id" = %s',
                [seats_value, self.id]
            )
    
    # Note: scheduled_end is now a real database field, not a property
    # The property has been removed to avoid conflicts with the field
    
    @property
    def is_past(self):
        """Check if session is in the past"""
        return self.scheduled_start < timezone.now()
    
    @property
    def booked_seats(self):
        """Get number of confirmed bookings (seats taken)"""
        # Use unified LiveClassBooking model
        try:
            from django.db.models import Sum
            total = self.live_class_bookings.filter(status__in=['confirmed', 'attended']).aggregate(
                total=Sum('seats_reserved')
            )['total']
            if total is not None:
                return total
        except Exception:
            # If query fails, return cached value
            pass
        # Fallback to cached seats_taken value
        return self.seats_taken or 0
    
    @property
    def seats_taken_cached(self):
        """Get cached seats_taken value (updated via signal)"""
        return self.seats_taken
    
    @property
    def waitlisted_count(self):
        """Get number of waitlisted bookings"""
        # Use unified LiveClassBooking model - but it doesn't have 'waitlisted' status
        # Check waitlist_entries instead, or return 0 if not available
        try:
            # Try using SessionWaitlist if available
            if hasattr(self, 'waitlist_entries'):
                return self.waitlist_entries.filter(status='waiting').count()
        except Exception:
            pass
        # If no waitlist model, return 0
        return 0
    
    @property
    def remaining_seats(self):
        """Get number of remaining seats in real-time"""
        return max(0, self.total_seats - self.booked_seats)
    
    @property
    def available_spots(self):
        """Legacy property for backwards compatibility"""
        return self.remaining_seats
    
    @property
    def is_full(self):
        """Check if all seats are taken"""
        return self.remaining_seats <= 0
    
    @property
    def booking_open(self):
        """Check if booking is still open"""
        if self.status not in ['scheduled']:
            return False
        if self.is_past:
            return False
        if self.is_full and not self.enable_waitlist:
            return False
        return True
    
    def can_be_booked(self, user=None):
        """Check if session can be booked by a user"""
        if self.status not in ['scheduled']:
            return False, "Session is not available for booking"
        if self.is_past:
            return False, "Session has already passed"
        if self.is_full and not self.enable_waitlist:
            return False, "Session is full and waitlist is disabled"
        if user:
            # Check if user already has a booking (1 seat per user per session)
            # Use LiveClassBooking instead of legacy Booking
            try:
                existing_booking = self.live_class_bookings.filter(
                    student_user=user, 
                    status__in=['confirmed', 'pending']
                ).first()
                if existing_booking:
                    return False, "You already have a booking for this session"
            except Exception:
                # If query fails, allow booking (fail open)
                pass
        return True, "Available"
    
    def update_booking_status(self):
        """Automatically close booking when full if waitlist is disabled"""
        if self.is_full and not self.enable_waitlist and self.status == 'scheduled':
            self.status = 'booking_closed'
            self.save(update_fields=['status'])


class TeacherAvailability(models.Model):
    """Teacher's available time slots for live sessions"""
    TYPE_CHOICES = [
        ('recurring', 'Recurring (Weekly)'),
        ('one_time', 'One-Time Slot'),
    ]
    
    DAY_CHOICES = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]
    
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='availability_slots')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='teacher_availability', null=True, blank=True, help_text='Leave blank for all courses')
    
    # Type: recurring or one-time
    slot_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='recurring')
    
    # For recurring slots (day of week)
    day_of_week = models.IntegerField(choices=DAY_CHOICES, null=True, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    
    # For one-time slots (specific datetime)
    start_datetime = models.DateTimeField(null=True, blank=True)
    end_datetime = models.DateTimeField(null=True, blank=True)
    
    timezone = models.CharField(max_length=50, default='UTC')
    
    # Date range for recurring slots
    valid_from = models.DateField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_blocked = models.BooleanField(default=False, help_text='Block this time slot from being booked')
    blocked_reason = models.TextField(blank=True, help_text='Reason for blocking this slot')
    
    # Calendar integration (future use)
    google_calendar_event_id = models.CharField(max_length=200, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = 'Teacher Availabilities'
        ordering = ['day_of_week', 'start_time', 'start_datetime']
    
    def __str__(self):
        if self.slot_type == 'one_time':
            course_name = f" - {self.course.title}" if self.course else ""
            return f"{self.teacher.user.get_full_name()} - {self.start_datetime}{course_name}"
        else:
            day_name = self.get_day_of_week_display() if self.day_of_week is not None else "N/A"
            course_name = f" - {self.course.title}" if self.course else ""
            return f"{self.teacher.user.get_full_name()} - {day_name} {self.start_time}-{self.end_time}{course_name}"
    
    def clean(self):
        """Validate that required fields are set based on slot_type"""
        from django.core.exceptions import ValidationError
        if self.slot_type == 'recurring':
            if self.day_of_week is None or not self.start_time or not self.end_time:
                raise ValidationError('Recurring slots require day_of_week, start_time, and end_time.')
        elif self.slot_type == 'one_time':
            if not self.start_datetime or not self.end_datetime:
                raise ValidationError('One-time slots require start_datetime and end_datetime.')
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    @property
    def is_booked(self):
        """Check if this slot is already booked"""
        if self.slot_type == 'one_time':
            # For one-time slots, check if there's a confirmed booking
            # Use LiveClassBooking instead of legacy Booking
            try:
                return self.live_class_bookings.filter(status='confirmed').exists()
            except Exception:
                return False
        else:
            # For recurring slots, check if the slot is blocked or has active bookings
            return self.is_blocked or not self.is_active
    
    @property
    def is_available_for_booking(self):
        """Check if slot is available for 1:1 booking"""
        if not self.is_active:
            return False
        if self.is_blocked:
            return False
        if self.slot_type == 'one_time':
            # Check if it's in the past
            if self.start_datetime and self.start_datetime < timezone.now():
                return False
            # Check if already booked
            if self.is_booked:
                return False
        else:
            # For recurring slots, check valid_from/valid_until
            today = timezone.now().date()
            if self.valid_from and today < self.valid_from:
                return False
            if self.valid_until and today > self.valid_until:
                return False
        
        return True
    
    def can_be_booked(self, user=None, course=None):
        """Check if this availability slot can be booked by a user"""
        if not self.is_available_for_booking:
            return False, "Slot is not available for booking"
        
        # Check course match if specified
        if course and self.course and self.course != course:
            return False, "Slot is not available for this course"
        
        if user:
            # Check if user already has a booking for this slot
            # Use OneOnOneBooking instead of legacy Booking
            existing_booking = self.bookings.filter(
                user=user,
                status__in=['pending', 'confirmed']
            ).first()
            if existing_booking:
                return False, "You already have a booking for this slot"
            
            # Check for time conflicts with other bookings
            if self.slot_type == 'one_time':
                # Check if user has other bookings at the same time
                conflicting_bookings = OneOnOneBooking.objects.filter(
                    user=user,
                    status__in=['pending', 'confirmed'],
                    availability_slot__slot_type='one_time',
                    availability_slot__start_datetime__date=self.start_datetime.date(),
                    availability_slot__start_datetime__time__gte=self.start_datetime.time(),
                    availability_slot__start_datetime__time__lt=self.end_datetime.time(),
                ).exclude(availability_slot=self)
                
                if conflicting_bookings.exists():
                    return False, "You already have a booking at this time"
        
        return True, "Available"
    
    def get_duration_minutes(self):
        """Calculate duration in minutes"""
        if self.slot_type == 'one_time':
            if self.start_datetime and self.end_datetime:
                delta = self.end_datetime - self.start_datetime
                return int(delta.total_seconds() / 60)
        elif self.start_time and self.end_time:
            # For recurring slots, calculate from time fields
            from datetime import datetime, date
            start_dt = datetime.combine(date.today(), self.start_time)
            end_dt = datetime.combine(date.today(), self.end_time)
            if end_dt < start_dt:
                end_dt += timedelta(days=1)
            delta = end_dt - start_dt
            return int(delta.total_seconds() / 60)
        return 60  # Default 1 hour


class Booking(models.Model):
    """Group Session Booking (Seat-Based) - Student bookings for group sessions"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('waitlisted', 'Waitlisted'),
        ('cancelled', 'Cancelled'),
        ('attended', 'Attended'),
        ('no_show', 'No Show'),
    ]
    
    CANCELLATION_REASON_CHOICES = [
        ('student', 'Cancelled by student'),
        ('teacher', 'Cancelled by teacher'),
        ('system', 'Cancelled by system'),
        ('conflict', 'Scheduling conflict'),
        ('emergency', 'Emergency'),
    ]
    
    booking_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group_bookings')
    session = models.ForeignKey(LiveClassSession, on_delete=models.CASCADE, related_name='bookings')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Booking details
    booked_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.CharField(max_length=20, choices=CANCELLATION_REASON_CHOICES, blank=True)
    cancellation_notes = models.TextField(blank=True)
    
    # Reschedule
    original_session = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='rescheduled_bookings')
    rescheduled_at = models.DateTimeField(null=True, blank=True)
    
    # Attendance
    attended = models.BooleanField(default=False)
    attended_at = models.DateTimeField(null=True, blank=True)
    
    # Notes
    student_notes = models.TextField(blank=True, help_text='Student notes or questions')
    
    # Seat assignment (each booking consumes exactly 1 seat)
    seats_booked = models.PositiveIntegerField(default=1, help_text='Number of seats (always 1 per booking)')
    
    class Meta:
        ordering = ['-booked_at']
        unique_together = [['user', 'session']]  # One booking per user per session (1 seat per booking)
        verbose_name = 'Group Session Booking'
        verbose_name_plural = 'Group Session Bookings'
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.session.title} - {self.get_status_display()}"
    
    @property
    def booking_type(self):
        """Return booking type for UI display"""
        return 'group_session'
    
    @property
    def booking_type(self):
        """Return booking type for UI display"""
        return 'group_session'
    
    def confirm(self):
        """Confirm the booking and update session seat count"""
        if self.status == 'pending':
            self.status = 'confirmed'
            self.confirmed_at = timezone.now()
            self.save()
            # Update session booking status
            self.session.update_booking_status()
            return True
        elif self.status == 'waitlisted':
            # Check if seats are available before confirming from waitlist
            if self.session.remaining_seats > 0:
                self.status = 'confirmed'
                self.confirmed_at = timezone.now()
                self.save()
                self.session.update_booking_status()
                return True
        return False
    
    def cancel(self, reason='student', notes=''):
        """Cancel the booking and free up seat"""
        if self.status in ['pending', 'confirmed', 'waitlisted']:
            self.status = 'cancelled'
            self.cancelled_at = timezone.now()
            self.cancellation_reason = reason
            self.cancellation_notes = notes
            self.save()
            
            # If there's a waitlist, confirm next booking automatically
            if self.session.enable_waitlist:
                # Use waitlist_entries instead of bookings (Booking table doesn't exist)
                try:
                    next_waitlisted = self.session.waitlist_entries.filter(status='waiting').order_by('created_at').first()
                    if next_waitlisted:
                        # Offer seat to waitlisted student
                        next_waitlisted.offer_seat()
                except Exception:
                    # If waitlist model doesn't exist or query fails, skip
                    pass
            
            # Reopen booking if it was closed
            if self.session.status == 'booking_closed' and self.session.remaining_seats > 0:
                self.session.status = 'scheduled'
                self.session.save(update_fields=['status'])
            
            return True
        return False
    
    def reschedule_to(self, new_session, notes=''):
        """Reschedule booking to a new session"""
        if self.status in ['confirmed', 'pending']:
            # Check if new session can accept booking
            can_book, message = new_session.can_be_booked(self.user)
            if not can_book:
                return None
            
            # Create new booking
            new_booking = Booking.objects.create(
                user=self.user,
                session=new_session,
                status='confirmed' if new_session.remaining_seats > 0 else 'waitlisted',
                original_session=self,
                rescheduled_at=timezone.now(),
                student_notes=notes
            )
            
            # Confirm if there's a seat
            if new_booking.status == 'confirmed':
                new_booking.confirm()
            
            # Cancel old booking
            self.cancel(reason='conflict', notes=f'Rescheduled to session on {new_session.scheduled_start}')
            return new_booking
        return None
    
    @property
    def can_cancel(self):
        """Check if booking can be cancelled"""
        if self.status not in ['pending', 'confirmed', 'waitlisted']:
            return False
        # Allow cancellation up to 24 hours before session
        hours_until = (self.session.scheduled_start - timezone.now()).total_seconds() / 3600
        return hours_until >= 24


class OneOnOneBooking(models.Model):
    """1:1 Booking (Availability-Based) - Student bookings from teacher availability slots"""
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),  # Waiting for teacher approval (if required)
        ('confirmed', 'Confirmed'),
        ('declined', 'Declined by Teacher'),
        ('cancelled', 'Cancelled'),
        ('attended', 'Attended'),
        ('no_show', 'No Show'),
    ]
    
    CANCELLATION_REASON_CHOICES = [
        ('student', 'Cancelled by student'),
        ('teacher', 'Cancelled by teacher'),
        ('system', 'Cancelled by system'),
        ('conflict', 'Scheduling conflict'),
        ('emergency', 'Emergency'),
    ]
    
    booking_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='one_on_one_bookings')
    availability_slot = models.ForeignKey(TeacherAvailability, on_delete=models.CASCADE, related_name='bookings')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='one_on_one_bookings', null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Booking details
    booked_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    declined_at = models.DateTimeField(null=True, blank=True)
    declined_reason = models.TextField(blank=True, help_text='Reason for declining (if applicable)')
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.CharField(max_length=20, choices=CANCELLATION_REASON_CHOICES, blank=True)
    cancellation_notes = models.TextField(blank=True)
    
    # Meeting link (set by teacher or auto-generated)
    meeting_link = models.URLField(blank=True, help_text='Zoom / Google Meet / Custom meeting link for 1:1 session')
    
    # Reschedule
    original_booking = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='rescheduled_bookings')
    rescheduled_at = models.DateTimeField(null=True, blank=True)
    
    # Attendance
    attended = models.BooleanField(default=False)
    attended_at = models.DateTimeField(null=True, blank=True)
    
    # Notes
    student_notes = models.TextField(blank=True, help_text='Student notes or questions')
    teacher_notes = models.TextField(blank=True, help_text='Teacher notes (internal)')
    
    # Recurring series (if booking is part of a series)
    is_recurring = models.BooleanField(default=False)
    recurring_series_id = models.UUIDField(null=True, blank=True, help_text='ID to group recurring bookings together')
    recurring_cadence = models.CharField(max_length=20, blank=True, choices=[
        ('weekly', 'Weekly'),
        ('biweekly', 'Bi-Weekly'),
        ('monthly', 'Monthly'),
        ('custom', 'Custom'),
    ])
    next_booking_date = models.DateTimeField(null=True, blank=True, help_text='Next booking in series')
    
    class Meta:
        ordering = ['-booked_at']
        unique_together = [['user', 'availability_slot']]  # One booking per user per slot
        verbose_name = '1:1 Booking'
        verbose_name_plural = '1:1 Bookings'
    
    def __str__(self):
        slot_display = self.availability_slot.start_datetime if self.availability_slot.slot_type == 'one_time' else f"{self.availability_slot.get_day_of_week_display()} {self.availability_slot.start_time}"
        return f"{self.user.get_full_name()} - {slot_display} - {self.get_status_display()}"
    
    @property
    def booking_type(self):
        """Return booking type for UI display"""
        return 'one_on_one'
    
    @property
    def session_datetime(self):
        """Get the actual datetime for this booking"""
        if self.availability_slot.slot_type == 'one_time':
            return self.availability_slot.start_datetime
        # For recurring slots, we'd need to calculate the next occurrence
        # This is a simplified version - in production you'd calculate based on the booking date
        return None
    
    @property
    def requires_approval(self):
        """Check if this booking requires teacher approval"""
        if self.course:
            # Check course-level setting
            if self.course.requires_booking_approval:
                return True
            # Check teacher-level override
            course_teacher = CourseTeacher.objects.filter(
                course=self.course,
                teacher=self.availability_slot.teacher
            ).first()
            if course_teacher and course_teacher.get_requires_approval():
                return True
        return False
    
    def confirm(self, approved_by=None):
        """Confirm the booking (auto or after teacher approval)"""
        if self.status == 'pending':
            # Remove slot from availability (prevent double booking)
            self.availability_slot.is_active = False
            self.availability_slot.save(update_fields=['is_active'])
            
            self.status = 'confirmed'
            self.confirmed_at = timezone.now()
            self.save()
            return True
        return False
    
    def decline(self, reason='', declined_by=None):
        """Decline the booking"""
        if self.status == 'pending':
            self.status = 'declined'
            self.declined_at = timezone.now()
            self.declined_reason = reason
            self.save()
            # Slot remains available for others
            return True
        return False
    
    def cancel(self, reason='student', notes=''):
        """Cancel the booking and free up the slot"""
        if self.status in ['pending', 'confirmed']:
            self.status = 'cancelled'
            self.cancelled_at = timezone.now()
            self.cancellation_reason = reason
            self.cancellation_notes = notes
            self.save()
            
            # Free up the availability slot for others
            if self.availability_slot.slot_type == 'one_time':
                # For one-time slots, reactivate them
                self.availability_slot.is_active = True
                self.availability_slot.save(update_fields=['is_active'])
            # For recurring slots, the slot pattern remains but this instance is cancelled
            
            return True
        return False
    
    @property
    def can_cancel(self):
        """Check if booking can be cancelled"""
        if self.status not in ['pending', 'confirmed']:
            return False
        # Allow cancellation up to 24 hours before session
        session_dt = self.session_datetime
        if not session_dt:
            return True  # Can cancel if no specific datetime yet
        
        hours_until = (session_dt - timezone.now()).total_seconds() / 3600
        return hours_until >= 24
    
    def get_scheduled_time(self):
        """Get the scheduled time for display"""
        if self.availability_slot.slot_type == 'one_time':
            return self.availability_slot.start_datetime
        else:
            # For recurring, we need to compute the next occurrence
            # Simplified: return the slot pattern
            return f"{self.availability_slot.get_day_of_week_display()} {self.availability_slot.start_time}"


class BookingReminder(models.Model):
    """Track sent reminders for bookings (both Group and 1:1)"""
    REMINDER_TYPE_CHOICES = [
        ('24h', '24 Hours Before'),
        ('1h', '1 Hour Before'),
        ('confirmed', 'Booking Confirmed'),
        ('cancelled', 'Booking Cancelled'),
        ('rescheduled', 'Booking Rescheduled'),
    ]
    
    # Support both booking types
    group_booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='reminders', null=True, blank=True)
    one_on_one_booking = models.ForeignKey(OneOnOneBooking, on_delete=models.CASCADE, related_name='reminders', null=True, blank=True)
    
    reminder_type = models.CharField(max_length=20, choices=REMINDER_TYPE_CHOICES)
    sent_at = models.DateTimeField(auto_now_add=True)
    sent_via = models.CharField(max_length=20, default='email', choices=[('email', 'Email'), ('sms', 'SMS'), ('push', 'Push Notification')])
    
    class Meta:
        ordering = ['-sent_at']
    
    def clean(self):
        """Ensure exactly one booking is set"""
        from django.core.exceptions import ValidationError
        if not self.group_booking and not self.one_on_one_booking:
            raise ValidationError('Either group_booking or one_on_one_booking must be set')
        if self.group_booking and self.one_on_one_booking:
            raise ValidationError('Cannot set both group_booking and one_on_one_booking')
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        booking = self.group_booking or self.one_on_one_booking
        return f"{booking} - {self.get_reminder_type_display()} - {self.sent_at}"


# ============================================
# ANNOUNCEMENTS
# ============================================

class CourseAnnouncement(models.Model):
    """Course announcements by teachers"""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='announcements')
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='announcements')
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Visibility
    is_pinned = models.BooleanField(default=False)
    send_to_all_students = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_pinned', '-created_at']
    
    def __str__(self):
        return f"{self.course.title} - {self.title}"


# ============================================
# MESSAGING
# ============================================

class StudentMessage(models.Model):
    """Teacher-student messaging"""
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='sent_messages')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='messages', null=True, blank=True)
    
    subject = models.CharField(max_length=200)
    message = models.TextField()
    
    # Status
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Reply chain
    reply_to = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='replies')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.teacher.user.username} → {self.student.username}: {self.subject}"


# ============================================
# SITE SETTINGS & ANALYTICS
# ============================================

class SiteSettings(models.Model):
    """Singleton for site-wide settings"""
    site_name = models.CharField(max_length=100, default='Fluentory')
    tagline = models.CharField(max_length=200, default='Global Learning Platform')
    
    # Hero content
    hero_headline = models.CharField(max_length=200, default='The Modern Way To Learn Globally.')
    hero_subheadline = models.TextField(default='Placement-based learning. Milestone quizzes. Verified certification. Built for outcomes.')
    hero_background_image = models.ImageField(upload_to='site/hero/', blank=True, null=True, help_text='Background image for hero section')
    
    # Stats (displayed on landing)
    total_lessons_completed = models.PositiveIntegerField(default=120000)
    average_satisfaction = models.FloatField(default=4.8)
    countries_count = models.PositiveIntegerField(default=40)
    
    # Announcement bar
    announcement_text = models.CharField(max_length=200, blank=True)
    announcement_link = models.URLField(blank=True)
    show_announcement = models.BooleanField(default=True)
    
    # Section Images
    how_it_works_image = models.ImageField(upload_to='site/sections/', blank=True, null=True, help_text='Image for How It Works section')
    ai_tutor_image = models.ImageField(upload_to='site/sections/', blank=True, null=True, help_text='Image for AI Tutor section')
    certificates_image = models.ImageField(upload_to='site/sections/', blank=True, null=True, help_text='Image for Certificates section')
    pricing_image = models.ImageField(upload_to='site/sections/', blank=True, null=True, help_text='Image for Pricing section')
    faq_video_thumbnail = models.ImageField(upload_to='site/sections/', blank=True, null=True, help_text='Video thumbnail for FAQ section')
    
    # Contact
    support_email = models.EmailField(default='support@fluentory.com')
    
    # Social links
    linkedin_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    facebook_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    
    class Meta:
        verbose_name = 'Site Settings'
        verbose_name_plural = 'Site Settings'
    
    def __str__(self):
        return self.site_name
    
    @classmethod
    def get_settings(cls):
        settings, _ = cls.objects.get_or_create(pk=1)
        return settings


# ============================================
# MEDIA MANAGEMENT
# ============================================

class Media(models.Model):
    MEDIA_TYPE_CHOICES = [
        ('image', 'Image'),
        ('video', 'Video'),
        ('document', 'Document'),
    ]
    
    CATEGORY_CHOICES = [
        ('course', 'Course'),
        ('logo', 'Logo'),
        ('avatar', 'Avatar'),
        ('certificate', 'Certificate'),
        ('faq', 'FAQ'),
        ('general', 'General'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    file = models.ImageField(upload_to='media/%Y/%m/')
    media_type = models.CharField(max_length=20, choices=MEDIA_TYPE_CHOICES, default='image')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='general')
    
    # Metadata
    alt_text = models.CharField(max_length=200, blank=True, help_text='For accessibility and SEO')
    tags = models.CharField(max_length=500, blank=True, help_text='Comma-separated tags')
    
    # Dimensions (auto-filled on save)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    file_size = models.PositiveIntegerField(null=True, blank=True, help_text='Size in bytes')
    
    # Usage tracking
    usage_count = models.PositiveIntegerField(default=0, help_text='Number of times used')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='uploaded_media')
    
    class Meta:
        verbose_name = 'Media'
        verbose_name_plural = 'Media'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        # Auto-fill dimensions and file size if image
        if self.file and self.media_type == 'image':
            try:
                from PIL import Image
                import os
                
                # Get file size
                if self.file:
                    self.file_size = self.file.size
                    
                    # Get image dimensions
                    img = Image.open(self.file)
                    self.width, self.height = img.size
            except Exception:
                pass
        
        super().save(*args, **kwargs)
    
    def get_file_size_display(self):
        """Return human-readable file size"""
        if not self.file_size:
            return 'Unknown'
        for unit in ['B', 'KB', 'MB', 'GB']:
            if self.file_size < 1024.0:
                return f"{self.file_size:.1f} {unit}"
            self.file_size /= 1024.0
        return f"{self.file_size:.1f} TB"
    
    def get_tags_list(self):
        """Return tags as a list"""
        if not self.tags:
            return []
        return [tag.strip() for tag in self.tags.split(',') if tag.strip()]


# ============================================
# PHASE 2: UNIFIED BOOKING SYSTEM
# ============================================

class TeacherBookingPolicy(models.Model):
    """Teacher booking policies for approval rules and limits"""
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='booking_policies')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='booking_policies', null=True, blank=True, 
                                help_text='If null, applies as default policy for teacher')
    
    # Approval requirements
    requires_approval_for_one_on_one = models.BooleanField(default=False, help_text='Require approval for 1:1 bookings')
    requires_approval_for_group = models.BooleanField(default=False, help_text='Require approval for group session bookings (usually false)')
    
    # Time constraints
    min_notice_hours = models.PositiveIntegerField(default=24, help_text='Minimum hours notice before booking allowed')
    cancel_window_hours = models.PositiveIntegerField(default=24, help_text='Hours before start when cancellation is allowed')
    buffer_before_minutes = models.PositiveIntegerField(default=0, help_text='Buffer time before session (minutes)')
    buffer_after_minutes = models.PositiveIntegerField(default=0, help_text='Buffer time after session (minutes)')
    
    # Limits
    max_bookings_per_day = models.PositiveIntegerField(null=True, blank=True, help_text='Optional limit on bookings per day')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Teacher Booking Policy'
        verbose_name_plural = 'Teacher Booking Policies'
        unique_together = [['teacher', 'course']]  # One policy per teacher per course
    
    def __str__(self):
        if self.course:
            return f"{self.teacher.user.get_full_name()} - {self.course.title} Policy"
        return f"{self.teacher.user.get_full_name()} - Default Policy"
    
    def get_requires_approval(self, booking_type):
        """Get approval requirement for booking type"""
        if booking_type == 'one_on_one':
            return self.requires_approval_for_one_on_one
        elif booking_type == 'group_session':
            return self.requires_approval_for_group
        return False


class LiveClassBooking(models.Model):
    """Unified booking model for both Group Sessions and 1:1 bookings"""
    BOOKING_TYPE_CHOICES = [
        ('group_session', 'Group Session'),
        ('one_on_one', '1:1 Booking'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),  # Student requested, waiting for approval
        ('confirmed', 'Confirmed'),
        ('declined', 'Declined'),
        ('cancelled', 'Cancelled'),
        ('attended', 'Attended'),
        ('no_show', 'No Show'),
        ('rescheduled', 'Rescheduled'),  # Old booking marked as this
    ]
    
    CANCEL_REASON_CHOICES = [
        ('student', 'Cancelled by student'),
        ('teacher', 'Cancelled by teacher'),
        ('admin', 'Cancelled by admin'),
        ('system', 'Cancelled by system'),
        ('conflict', 'Scheduling conflict'),
        ('emergency', 'Emergency'),
    ]
    
    # Core fields
    booking_type = models.CharField(max_length=20, choices=BOOKING_TYPE_CHOICES)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='live_class_bookings')
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='live_class_bookings')
    student_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='live_class_bookings')
    
    # Scheduling (UTC-based)
    start_at_utc = models.DateTimeField(help_text='Session start time in UTC')
    end_at_utc = models.DateTimeField(help_text='Session end time in UTC')
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Notes
    student_note = models.TextField(blank=True, help_text='Student notes or questions')
    teacher_note = models.TextField(blank=True, help_text='Teacher notes (internal)')
    
    # Group-specific fields
    session = models.ForeignKey(LiveClassSession, on_delete=models.CASCADE, related_name='live_class_bookings', 
                                null=True, blank=True, help_text='FK to LiveClassSession (nullable for 1:1)')
    seats_reserved = models.PositiveIntegerField(default=1, help_text='Number of seats reserved (default 1)')
    
    # Approval & audit fields
    decision_at = models.DateTimeField(null=True, blank=True, help_text='When approval decision was made')
    decided_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                    related_name='booking_decisions', help_text='Teacher or admin who decided')
    
    cancelled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                     related_name='booking_cancellations', help_text='Who cancelled the booking')
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancel_reason = models.CharField(max_length=20, choices=CANCEL_REASON_CHOICES, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Live Class Booking'
        verbose_name_plural = 'Live Class Bookings'
        indexes = [
            models.Index(fields=['booking_type', 'status']),
            models.Index(fields=['student_user', 'start_at_utc']),
            models.Index(fields=['teacher', 'start_at_utc']),
        ]
        # Unique constraints: prevent duplicate bookings
        # For group sessions: one booking per student per session per time
        # For 1:1: one booking per student per teacher per time
        constraints = [
            models.UniqueConstraint(
                fields=['student_user', 'session', 'start_at_utc'],
                condition=models.Q(booking_type='group_session'),
                name='unique_group_booking'
            ),
            models.UniqueConstraint(
                fields=['student_user', 'teacher', 'start_at_utc'],
                condition=models.Q(booking_type='one_on_one'),
                name='unique_one_on_one_booking'
            ),
        ]
        # Unique constraints: prevent duplicate bookings
        # Note: Django doesn't support conditional unique_together, so we use database-level constraints
        # For group sessions: (student_user, session, start_at_utc) should be unique
        # For 1:1 bookings: (student_user, teacher, start_at_utc) should be unique
        # We'll enforce this in the save() method or via database constraints
    
    def __str__(self):
        return f"{self.student_user.get_full_name()} - {self.get_booking_type_display()} - {self.get_status_display()}"
    
    def confirm(self, decided_by=None):
        """Confirm the booking"""
        if self.status == 'pending':
            self.status = 'confirmed'
            self.decision_at = timezone.now()
            if decided_by:
                self.decided_by = decided_by
            self.save()
            return True
        return False
    
    def decline(self, decided_by=None, reason=''):
        """Decline the booking"""
        if self.status == 'pending':
            self.status = 'declined'
            self.decision_at = timezone.now()
            if decided_by:
                self.decided_by = decided_by
            if reason:
                self.teacher_note = reason
            self.save()
            return True
        return False
    
    def cancel(self, cancelled_by=None, reason='student', note=''):
        """Cancel the booking"""
        if self.status in ['pending', 'confirmed']:
            self.status = 'cancelled'
            self.cancelled_at = timezone.now()
            if cancelled_by:
                self.cancelled_by = cancelled_by
            self.cancel_reason = reason
            if note:
                self.teacher_note = note
            self.save()
            return True
        return False


class BookingSeries(models.Model):
    """Recurring booking series for both group and 1:1 bookings"""
    TYPE_CHOICES = [
        ('one_on_one_series', '1:1 Series'),
        ('group_series', 'Group Series'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]
    
    FREQUENCY_CHOICES = [
        ('weekly', 'Weekly'),
        ('biweekly', 'Bi-Weekly'),
        ('monthly', 'Monthly'),
        ('custom', 'Custom'),
    ]
    
    student_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='booking_series')
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='booking_series')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='booking_series')
    
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Recurrence rules
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='weekly')
    interval = models.PositiveIntegerField(default=1, help_text='Interval for frequency (e.g., every 2 weeks)')
    days_of_week = models.CharField(max_length=50, blank=True, help_text='Comma-separated days (0=Monday, 6=Sunday) for weekly recurrences')
    occurrence_count = models.PositiveIntegerField(null=True, blank=True, help_text='Total number of occurrences')
    until_date = models.DateTimeField(null=True, blank=True, help_text='Series end date')
    
    # Default meeting info snapshot
    default_meeting_link = models.URLField(blank=True)
    default_meeting_id = models.CharField(max_length=100, blank=True)
    default_meeting_passcode = models.CharField(max_length=50, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Booking Series'
        verbose_name_plural = 'Booking Series'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.student_user.get_full_name()} - {self.get_type_display()} - {self.get_status_display()}"


class BookingSeriesItem(models.Model):
    """Individual booking occurrence within a series"""
    series = models.ForeignKey(BookingSeries, on_delete=models.CASCADE, related_name='items')
    booking = models.ForeignKey(LiveClassBooking, on_delete=models.CASCADE, related_name='series_items')
    occurrence_index = models.PositiveIntegerField(help_text='Occurrence number in series (1, 2, 3, ...)')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Booking Series Item'
        verbose_name_plural = 'Booking Series Items'
        unique_together = [['series', 'occurrence_index']]
        ordering = ['occurrence_index']
    
    def __str__(self):
        return f"{self.series} - Occurrence {self.occurrence_index}"


class SessionWaitlist(models.Model):
    """Waitlist for group sessions"""
    STATUS_CHOICES = [
        ('waiting', 'Waiting'),
        ('offered', 'Offered'),
        ('accepted', 'Accepted'),
        ('expired', 'Expired'),
    ]
    
    session = models.ForeignKey(LiveClassSession, on_delete=models.CASCADE, related_name='waitlist_entries')
    student_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='waitlist_entries')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waiting')
    created_at = models.DateTimeField(auto_now_add=True)
    offered_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    expired_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Session Waitlist'
        verbose_name_plural = 'Session Waitlists'
        unique_together = [['session', 'student_user']]  # One waitlist entry per student per session
        ordering = ['created_at']  # FIFO order
    
    def __str__(self):
        return f"{self.student_user.get_full_name()} - {self.session.title} - {self.get_status_display()}"
    
    def offer_seat(self):
        """Offer seat to this waitlist entry"""
        if self.status == 'waiting':
            self.status = 'offered'
            self.offered_at = timezone.now()
            self.save()
            # TODO: Send notification
            return True
        return False
    
    def accept_offer(self):
        """Accept the offered seat"""
        if self.status == 'offered':
            self.status = 'accepted'
            self.accepted_at = timezone.now()
            self.save()
            # TODO: Create booking
            return True
        return False
    
    def expire_offer(self):
        """Mark offer as expired"""
        if self.status == 'offered':
            self.status = 'expired'
            self.expired_at = timezone.now()
            self.save()
            # TODO: Offer to next in line
            return True
        return False


# ============================================
# SIGNALS - Auto-create profiles
# ============================================

from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()
