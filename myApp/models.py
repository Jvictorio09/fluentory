from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
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
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher_profile')
    
    # Status
    is_approved = models.BooleanField(default=False)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_teachers')
    
    # Online status
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(null=True, blank=True)
    
    # Bio
    bio = models.TextField(blank=True)
    specialization = models.CharField(max_length=200, blank=True)
    years_experience = models.PositiveIntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - Teacher"


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
    
    # Timestamps
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        unique_together = ['course', 'teacher']
    
    def __str__(self):
        return f"{self.teacher.user.username} - {self.course.title} ({self.permission_level})"


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
    """Scheduled live class sessions"""
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('live', 'Live'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='live_classes')
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='live_classes')
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Scheduling
    scheduled_start = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=60)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    
    # Video conferencing links
    zoom_link = models.URLField(blank=True)
    google_meet_link = models.URLField(blank=True)
    meeting_id = models.CharField(max_length=100, blank=True)
    meeting_password = models.CharField(max_length=50, blank=True)
    
    # Attendance
    max_attendees = models.PositiveIntegerField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-scheduled_start']
    
    def __str__(self):
        return f"{self.course.title} - {self.title} - {self.scheduled_start}"


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
