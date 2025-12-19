from django.contrib import admin
from django.utils.html import format_html
from .models import (
    UserProfile, Category, Course, Module, Lesson,
    Quiz, Question, Answer, Enrollment, LessonProgress, QuizAttempt,
    Certificate, PlacementTest, TutorConversation, TutorMessage,
    Partner, Cohort, CohortMembership, Payment, Review, FAQ,
    Notification, SiteSettings
)


# ============================================
# INLINE ADMINS
# ============================================

class ModuleInline(admin.TabularInline):
    model = Module
    extra = 1
    ordering = ['order']


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1
    ordering = ['order']


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1
    ordering = ['order']


class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 4
    ordering = ['order']


class TutorMessageInline(admin.TabularInline):
    model = TutorMessage
    extra = 0
    readonly_fields = ['role', 'content', 'created_at']


# ============================================
# USER ADMIN
# ============================================

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'country', 'current_streak', 'total_learning_minutes', 'created_at']
    list_filter = ['role', 'country', 'preferred_language']
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('User Info', {
            'fields': ('user', 'role', 'avatar', 'bio', 'phone', 'country')
        }),
        ('Preferences', {
            'fields': ('preferred_language', 'timezone', 'learning_goal', 'daily_goal_minutes')
        }),
        ('Stats', {
            'fields': ('current_streak', 'longest_streak', 'last_activity_date', 'total_learning_minutes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


# ============================================
# COURSE ADMIN
# ============================================

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'icon', 'order']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['order', 'name']


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'level', 'status', 'price', 'enrolled_count', 'completion_rate_display', 'created_at']
    list_filter = ['status', 'level', 'category', 'is_free', 'has_certificate']
    search_fields = ['title', 'description']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ['enrolled_count', 'completion_rate', 'average_rating', 'lessons_count']
    inlines = [ModuleInline]
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('title', 'slug', 'description', 'short_description', 'outcome')
        }),
        ('Media', {
            'fields': ('thumbnail', 'preview_video')
        }),
        ('Classification', {
            'fields': ('category', 'level', 'instructor', 'language', 'available_languages')
        }),
        ('Pricing', {
            'fields': ('price', 'currency', 'is_free')
        }),
        ('Content', {
            'fields': ('estimated_hours', 'lessons_count')
        }),
        ('Features', {
            'fields': ('has_certificate', 'has_ai_tutor', 'has_quizzes')
        }),
        ('Status & SEO', {
            'fields': ('status', 'meta_title', 'meta_description', 'published_at')
        }),
        ('Stats', {
            'fields': ('enrolled_count', 'completion_rate', 'average_rating'),
            'classes': ('collapse',)
        }),
    )
    
    def completion_rate_display(self, obj):
        return f"{obj.completion_rate:.1f}%"
    completion_rate_display.short_description = 'Completion Rate'


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'order', 'is_locked']
    list_filter = ['course', 'is_locked']
    search_fields = ['title', 'course__title']
    inlines = [LessonInline]
    ordering = ['course', 'order']


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ['title', 'module', 'content_type', 'order', 'estimated_minutes', 'is_preview', 'is_milestone']
    list_filter = ['content_type', 'is_preview', 'is_milestone', 'module__course']
    search_fields = ['title', 'module__title', 'module__course__title']
    ordering = ['module__course', 'module__order', 'order']


# ============================================
# QUIZ ADMIN
# ============================================

@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ['title', 'quiz_type', 'course', 'passing_score', 'total_attempts', 'pass_rate_display']
    list_filter = ['quiz_type', 'course']
    search_fields = ['title', 'course__title']
    inlines = [QuestionInline]
    
    def pass_rate_display(self, obj):
        return f"{obj.pass_rate:.1f}%"
    pass_rate_display.short_description = 'Pass Rate'


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['quiz', 'question_text_short', 'question_type', 'points', 'order']
    list_filter = ['question_type', 'quiz']
    search_fields = ['question_text', 'quiz__title']
    inlines = [AnswerInline]
    
    def question_text_short(self, obj):
        return obj.question_text[:100] + '...' if len(obj.question_text) > 100 else obj.question_text
    question_text_short.short_description = 'Question'


# ============================================
# ENROLLMENT & PROGRESS ADMIN
# ============================================

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ['user', 'course', 'status', 'progress_display', 'enrolled_at', 'is_gifted']
    list_filter = ['status', 'course', 'is_gifted', 'partner']
    search_fields = ['user__username', 'user__email', 'course__title']
    readonly_fields = ['progress_percentage', 'enrolled_at']
    
    def progress_display(self, obj):
        color = '#22c55e' if obj.progress_percentage >= 70 else '#eab308' if obj.progress_percentage >= 30 else '#ef4444'
        return format_html(
            '<div style="width:100px;background:#e5e7eb;border-radius:5px;">'
            '<div style="width:{}%;background:{};height:20px;border-radius:5px;text-align:center;color:white;font-size:12px;line-height:20px;">{:.0f}%</div>'
            '</div>',
            obj.progress_percentage, color, obj.progress_percentage
        )
    progress_display.short_description = 'Progress'


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ['enrollment', 'lesson', 'completed', 'time_spent_display', 'started_at']
    list_filter = ['completed', 'enrollment__course']
    search_fields = ['enrollment__user__username', 'lesson__title']
    
    def time_spent_display(self, obj):
        minutes = obj.time_spent // 60
        seconds = obj.time_spent % 60
        return f"{minutes}m {seconds}s"
    time_spent_display.short_description = 'Time Spent'


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ['user', 'quiz', 'score_display', 'passed', 'started_at']
    list_filter = ['passed', 'quiz', 'quiz__course']
    search_fields = ['user__username', 'quiz__title']
    
    def score_display(self, obj):
        color = '#22c55e' if obj.passed else '#ef4444'
        return format_html('<span style="color:{}">{:.1f}%</span>', color, obj.score)
    score_display.short_description = 'Score'


# ============================================
# CERTIFICATE ADMIN
# ============================================

@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ['certificate_id', 'user', 'course', 'issued_at', 'verified_count', 'is_verified']
    list_filter = ['is_verified', 'course', 'issued_at']
    search_fields = ['certificate_id', 'user__username', 'course__title']
    readonly_fields = ['certificate_id', 'qr_code', 'verification_url', 'verified_count']
    
    actions = ['generate_qr_codes']
    
    def generate_qr_codes(self, request, queryset):
        for cert in queryset:
            cert.generate_qr_code()
        self.message_user(request, f"Generated QR codes for {queryset.count()} certificates")
    generate_qr_codes.short_description = "Generate QR codes for selected certificates"


# ============================================
# PLACEMENT TEST ADMIN
# ============================================

@admin.register(PlacementTest)
class PlacementTestAdmin(admin.ModelAdmin):
    list_display = ['user', 'score_display', 'recommended_level', 'taken_at']
    list_filter = ['recommended_level', 'taken_at']
    search_fields = ['user__username', 'user__email']
    
    def score_display(self, obj):
        return f"{obj.score:.1f}%"
    score_display.short_description = 'Score'


# ============================================
# AI TUTOR ADMIN
# ============================================

@admin.register(TutorConversation)
class TutorConversationAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'course', 'lesson', 'message_count', 'started_at']
    list_filter = ['course', 'language']
    search_fields = ['user__username', 'title']
    inlines = [TutorMessageInline]
    
    def message_count(self, obj):
        return obj.messages.count()
    message_count.short_description = 'Messages'


# ============================================
# PARTNER ADMIN
# ============================================

@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'user', 'total_students', 'total_revenue', 'commission_rate', 'is_active']
    list_filter = ['is_active', 'joined_at']
    search_fields = ['company_name', 'user__username', 'contact_email']


@admin.register(Cohort)
class CohortAdmin(admin.ModelAdmin):
    list_display = ['name', 'partner', 'start_date', 'end_date', 'student_count', 'promo_code']
    list_filter = ['partner', 'start_date']
    search_fields = ['name', 'partner__company_name']
    filter_horizontal = ['courses']  # 'students' uses a through model, can't use filter_horizontal
    
    def student_count(self, obj):
        return obj.students.count()
    student_count.short_description = 'Students'


# ============================================
# PAYMENT ADMIN
# ============================================

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['payment_id', 'user', 'course', 'amount_display', 'status', 'payment_method', 'created_at']
    list_filter = ['status', 'payment_method', 'currency', 'created_at']
    search_fields = ['payment_id', 'user__username', 'stripe_payment_id']
    readonly_fields = ['payment_id', 'created_at']
    
    def amount_display(self, obj):
        return f"{obj.amount} {obj.currency}"
    amount_display.short_description = 'Amount'


# ============================================
# REVIEW ADMIN
# ============================================

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['user', 'course', 'rating_display', 'is_approved', 'is_featured', 'created_at']
    list_filter = ['rating', 'is_approved', 'is_featured', 'course']
    search_fields = ['user__username', 'course__title', 'title', 'content']
    
    def rating_display(self, obj):
        return '★' * obj.rating + '☆' * (5 - obj.rating)
    rating_display.short_description = 'Rating'


# ============================================
# FAQ ADMIN
# ============================================

@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ['question', 'category', 'has_video', 'order', 'is_featured', 'is_active']
    list_filter = ['category', 'is_featured', 'is_active']
    search_fields = ['question', 'answer']
    list_editable = ['order', 'is_featured', 'is_active']
    
    def has_video(self, obj):
        return bool(obj.video_url)
    has_video.boolean = True
    has_video.short_description = 'Video'


# ============================================
# NOTIFICATION ADMIN
# ============================================

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'notification_type', 'title', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['user__username', 'title', 'message']


# ============================================
# SITE SETTINGS ADMIN
# ============================================

@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ['site_name', 'tagline', 'support_email']
    
    def has_add_permission(self, request):
        # Only allow one instance
        return not SiteSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        return False
