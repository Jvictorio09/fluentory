from django.contrib import admin
from django.utils.html import format_html
from .models import (
    UserProfile, Category, Course, Module, Lesson,
    Quiz, Question, Answer, Enrollment, LessonProgress, QuizAttempt,
    Certificate, PlacementTest, TutorConversation, TutorMessage,
    Partner, Cohort, CohortMembership, Payment, Review, FAQ,
    Notification, SiteSettings, Media,
    TeacherAvailability, Booking, OneOnOneBooking, BookingReminder,
    GiftEnrollment, LiveClassSession, LiveClassTeacherAssignment,
    Lead, LeadTimelineEvent, GiftEnrollmentLeadLink, EnrollmentLeadLink
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
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('site_name', 'tagline')
        }),
        ('Hero Section', {
            'fields': ('hero_headline', 'hero_subheadline', 'hero_background_image')
        }),
        ('Section Images', {
            'fields': ('how_it_works_image', 'ai_tutor_image', 'certificates_image', 'pricing_image', 'faq_video_thumbnail'),
            'description': 'Upload images for each section of the landing page'
        }),
        ('Stats', {
            'fields': ('total_lessons_completed', 'average_satisfaction', 'countries_count')
        }),
        ('Announcement Bar', {
            'fields': ('announcement_text', 'announcement_link', 'show_announcement')
        }),
        ('Contact & Social', {
            'fields': ('support_email', 'linkedin_url', 'instagram_url', 'facebook_url', 'twitter_url')
        }),
    )
    
    def has_add_permission(self, request):
        # Only allow one instance
        return not SiteSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        return False


# ============================================
# MEDIA ADMIN
# ============================================

@admin.register(Media)
class MediaAdmin(admin.ModelAdmin):
    list_display = ['title', 'media_type', 'category', 'file_size_display', 'usage_count', 'created_at', 'created_by']
    list_filter = ['media_type', 'category', 'created_at']
    search_fields = ['title', 'description', 'alt_text', 'tags']
    readonly_fields = ['width', 'height', 'file_size', 'usage_count', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('title', 'description', 'file')
        }),
        ('Classification', {
            'fields': ('media_type', 'category')
        }),
        ('Metadata', {
            'fields': ('alt_text', 'tags')
        }),
        ('File Information', {
            'fields': ('width', 'height', 'file_size', 'usage_count'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    def file_size_display(self, obj):
        return obj.get_file_size_display()
    file_size_display.short_description = 'File Size'
    
    def save_model(self, request, obj, form, change):
        if not change:  # New object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


# ============================================
# BOOKING SYSTEM ADMIN
# ============================================

@admin.register(TeacherAvailability)
class TeacherAvailabilityAdmin(admin.ModelAdmin):
    list_display = ['teacher', 'course', 'day_of_week', 'start_time', 'end_time', 'timezone', 'is_active']
    list_filter = ['day_of_week', 'is_active', 'timezone']
    search_fields = ['teacher__user__username', 'course__title']
    list_editable = ['is_active']


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['booking_id', 'user', 'session', 'status', 'booked_at', 'confirmed_at', 'attended']
    list_filter = ['status', 'attended', 'cancellation_reason', 'booked_at']
    search_fields = ['booking_id', 'user__username', 'user__email', 'session__title']
    readonly_fields = ['booking_id', 'booked_at', 'confirmed_at', 'cancelled_at', 'rescheduled_at']
    date_hierarchy = 'booked_at'


@admin.register(OneOnOneBooking)
class OneOnOneBookingAdmin(admin.ModelAdmin):
    list_display = ['booking_id', 'user', 'availability_slot', 'course', 'status', 'booked_at', 'confirmed_at', 'attended']
    list_filter = ['status', 'attended', 'cancellation_reason', 'booked_at', 'is_recurring']
    search_fields = ['booking_id', 'user__username', 'user__email', 'availability_slot__teacher__user__username']
    readonly_fields = ['booking_id', 'booked_at', 'confirmed_at', 'declined_at', 'cancelled_at', 'rescheduled_at']
    date_hierarchy = 'booked_at'
    raw_id_fields = ['user', 'availability_slot', 'course']


@admin.register(BookingReminder)
class BookingReminderAdmin(admin.ModelAdmin):
    list_display = ['get_booking', 'reminder_type', 'sent_at', 'sent_via']
    list_filter = ['reminder_type', 'sent_via', 'sent_at']
    search_fields = ['group_booking__user__username', 'group_booking__session__title', 
                     'one_on_one_booking__user__username']
    readonly_fields = ['sent_at']
    date_hierarchy = 'sent_at'
    
    def get_booking(self, obj):
        """Display the booking (either group or 1:1)"""
        if obj.group_booking:
            return f"Group: {obj.group_booking.user.get_full_name()} - {obj.group_booking.session.title}"
        elif obj.one_on_one_booking:
            return f"1:1: {obj.one_on_one_booking.user.get_full_name()} - {obj.one_on_one_booking.availability_slot}"
        return "N/A"
    get_booking.short_description = 'Booking'


# ============================================
# GIFT ENROLLMENTS ADMIN
# ============================================

@admin.register(GiftEnrollment)
class GiftEnrollmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'course', 'buyer', 'recipient_email', 'status', 'created_at', 'claimed_at']
    list_filter = ['status', 'created_at', 'claimed_at']
    search_fields = ['buyer__username', 'buyer__email', 'recipient_email', 'course__title', 'gift_token']
    readonly_fields = ['gift_token', 'created_at', 'claimed_at']
    date_hierarchy = 'created_at'
    raw_id_fields = ['buyer', 'course', 'payment', 'enrollment']
    
    fieldsets = (
        ('Gift Information', {
            'fields': ('gift_token', 'buyer', 'course', 'status')
        }),
        ('Recipient Information', {
            'fields': ('recipient_email', 'recipient_name', 'sender_name', 'gift_message')
        }),
        ('Payment & Enrollment', {
            'fields': ('payment', 'enrollment')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'claimed_at', 'expires_at')
        }),
    )


# ============================================
# LIVE CLASS SESSIONS ADMIN
# ============================================

@admin.register(LiveClassSession)
class LiveClassSessionAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'teacher', 'scheduled_start', 'status', 'seats_taken', 'total_seats']
    list_filter = ['status', 'course', 'teacher', 'scheduled_start']
    search_fields = ['title', 'course__title', 'teacher__user__username']
    readonly_fields = ['created_at', 'updated_at', 'started_at', 'ended_at']
    date_hierarchy = 'scheduled_start'
    raw_id_fields = ['course', 'teacher']


# ============================================
# LIVE CLASS TEACHER ASSIGNMENT ADMIN
# ============================================

@admin.register(LiveClassTeacherAssignment)
class LiveClassTeacherAssignmentAdmin(admin.ModelAdmin):
    list_display = ['session', 'old_teacher', 'new_teacher', 'assigned_by', 'created_at']
    list_filter = ['created_at', 'session__course']
    search_fields = ['session__title', 'old_teacher__user__username', 'new_teacher__user__username', 'assigned_by__username']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    raw_id_fields = ['session', 'old_teacher', 'new_teacher', 'assigned_by']


# ============================================
# CRM - LEAD TRACKER ADMIN
# ============================================

@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'phone', 'source', 'status', 'owner', 'last_contact_date', 'created_at']
    list_filter = ['status', 'source', 'owner', 'created_at']
    search_fields = ['name', 'email', 'phone']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
    raw_id_fields = ['owner', 'linked_user']


@admin.register(LeadTimelineEvent)
class LeadTimelineEventAdmin(admin.ModelAdmin):
    list_display = ['lead', 'event_type', 'actor', 'created_at']
    list_filter = ['event_type', 'created_at']
    search_fields = ['lead__name', 'lead__email', 'summary']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    raw_id_fields = ['lead', 'actor']


@admin.register(GiftEnrollmentLeadLink)
class GiftEnrollmentLeadLinkAdmin(admin.ModelAdmin):
    list_display = ['gift_enrollment', 'lead', 'created_at', 'created_by']
    list_filter = ['created_at']
    search_fields = ['gift_enrollment__recipient_email', 'lead__name', 'lead__email']
    readonly_fields = ['created_at']
    raw_id_fields = ['gift_enrollment', 'lead', 'created_by']


@admin.register(EnrollmentLeadLink)
class EnrollmentLeadLinkAdmin(admin.ModelAdmin):
    list_display = ['enrollment', 'lead', 'created_at', 'created_by']
    list_filter = ['created_at']
    search_fields = ['enrollment__user__username', 'lead__name', 'lead__email']
    readonly_fields = ['created_at']
    raw_id_fields = ['enrollment', 'lead', 'created_by']
