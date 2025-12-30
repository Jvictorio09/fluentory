from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from myApp import views

urlpatterns = [
    # Django's default admin (hidden from regular users)
    path('django-admin/', admin.site.urls),
    
    # Landing page
    path('', views.home, name='home'),
    
    # Static pages
    path('about/', views.about_page, name='about'),
    path('careers/', views.careers_page, name='careers'),
    path('blog/', views.blog_page, name='blog'),
    path('help-center/', views.help_center_page, name='help_center'),
    path('contact/', views.contact_page, name='contact'),
    path('privacy/', views.privacy_page, name='privacy'),
    path('terms/', views.terms_page, name='terms'),
    path('cookies/', views.cookies_page, name='cookies'),
    
    # Authentication
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    # Django built-in auth views (password reset, confirm, done, etc.)
    # Namespace the included auth URLs to avoid name collisions with our own views
    path('accounts/', include(('django.contrib.auth.urls', 'auth'), namespace='accounts')),
    
    # Student routes
    path('student/', views.student_home, name='student_home'),
    path('student/courses/', views.student_courses, name='student_courses'),
    path('student/courses/<slug:slug>/', views.student_course_detail, name='student_course_detail'),
    path('student/placement/', views.student_placement, name='student_placement'),
    path('student/learning/', views.student_learning, name='student_learning'),
    path('student/certificates/', views.student_certificates, name='student_certificates'),
    path('student/settings/', views.student_settings, name='student_settings'),
    path('student/bookings/', views.student_bookings, name='student_bookings'),
    path('student/sessions/<int:session_id>/book/', views.student_book_session, name='student_book_session'),
    path('student/bookings/<int:booking_id>/cancel/', views.student_booking_cancel, name='student_booking_cancel'),
    path('student/bookings/<int:booking_id>/reschedule/', views.student_booking_reschedule, name='student_booking_reschedule'),
    path('student/player/', views.student_course_player, name='student_course_player'),
    path('student/player/<int:enrollment_id>/', views.student_course_player, name='student_course_player_enrollment'),
    path('student/player/<int:enrollment_id>/lesson/<int:lesson_id>/', views.student_course_player, name='student_course_player_lesson'),
    
    # Quiz
    path('student/quiz/<int:quiz_id>/', views.take_quiz, name='take_quiz'),
    path('student/quiz/result/<int:attempt_id>/', views.quiz_result, name='quiz_result'),
    
    # Student API endpoints
    path('api/set-currency/', views.set_currency, name='set_currency'),
    path('api/mark-complete/', views.mark_lesson_complete, name='mark_lesson_complete'),
    path('api/enroll/', views.enroll_course, name='enroll_course'),
    path('api/tutor/chat/', views.ai_tutor_chat, name='ai_tutor_chat'),
    
    # Certificate verification (public)
    path('verify/<uuid:certificate_id>/', views.verify_certificate, name='verify_certificate'),
    
    # Custom Admin Dashboard (User-facing admin tool)
    # Django Admin is at /django-admin/ for technical users
    path('dashboard/', include('myApp.dashboard_urls')),
    
    # Teacher routes
    path('teacher/', views.teacher_dashboard, name='teacher_dashboard'),
    path('teacher/courses/', views.teacher_courses, name='teacher_courses'),
    path('teacher/courses/create/', views.teacher_course_create, name='teacher_course_create'),
    path('teacher/courses/<int:course_id>/', views.teacher_course_edit, name='teacher_course_edit'),
    path('teacher/courses/<int:course_id>/lessons/', views.teacher_lessons, name='teacher_lessons'),
    path('teacher/courses/<int:course_id>/lessons/create/', views.teacher_lesson_create, name='teacher_lesson_create'),
    path('teacher/courses/<int:course_id>/lessons/<int:lesson_id>/edit/', views.teacher_lesson_edit, name='teacher_lesson_edit'),
    path('teacher/courses/<int:course_id>/lessons/<int:lesson_id>/delete/', views.teacher_lesson_delete, name='teacher_lesson_delete'),
    path('teacher/courses/<int:course_id>/quizzes/', views.teacher_quizzes, name='teacher_quizzes'),
    path('teacher/courses/<int:course_id>/quizzes/create/', views.teacher_quiz_create, name='teacher_quiz_create'),
    path('teacher/courses/<int:course_id>/quizzes/<int:quiz_id>/edit/', views.teacher_quiz_edit, name='teacher_quiz_edit'),
    path('teacher/courses/<int:course_id>/quizzes/<int:quiz_id>/delete/', views.teacher_quiz_delete, name='teacher_quiz_delete'),
    path('teacher/courses/<int:course_id>/quizzes/<int:quiz_id>/questions/', views.teacher_quiz_questions, name='teacher_quiz_questions'),
    path('teacher/students/', views.teacher_my_students, name='teacher_my_students'),
    path('teacher/courses/<int:course_id>/students/', views.teacher_students, name='teacher_students'),
    path('teacher/schedule/', views.teacher_schedule, name='teacher_schedule'),
    path('teacher/courses/<int:course_id>/live-classes/', views.teacher_live_classes, name='teacher_live_classes'),
    path('teacher/courses/<int:course_id>/announcements/', views.teacher_announcements, name='teacher_announcements'),
    path('teacher/courses/<int:course_id>/ai-settings/', views.teacher_ai_settings, name='teacher_ai_settings'),
    path('teacher/availability/', views.teacher_availability, name='teacher_availability'),
    path('teacher/availability/<int:availability_id>/delete/', views.teacher_availability_delete, name='teacher_availability_delete'),
    path('teacher/availability/<int:availability_id>/toggle-block/', views.teacher_availability_toggle_block, name='teacher_availability_toggle_block'),
    path('teacher/schedule/calendar/', views.teacher_schedule_calendar, name='teacher_schedule_calendar'),
    path('teacher/toggle-online-status/', views.teacher_toggle_online_status, name='teacher_toggle_online_status'),
    path('teacher/sessions/<int:session_id>/bookings/', views.teacher_session_bookings, name='teacher_session_bookings'),
    path('teacher/bookings/<int:booking_id>/cancel/', views.teacher_booking_cancel, name='teacher_booking_cancel'),
    path('teacher/bookings/<int:booking_id>/attendance/', views.teacher_mark_attendance, name='teacher_mark_attendance'),
    
    # Partner routes
    path('partner/', views.partner_overview, name='partner_overview'),
    path('partner/cohorts/', views.partner_cohorts, name='partner_cohorts'),
    path('partner/programs/', views.partner_programs, name='partner_programs'),
    path('partner/referrals/', views.partner_referrals, name='partner_referrals'),
    path('partner/marketing/', views.partner_marketing, name='partner_marketing'),
    path('partner/reports/', views.partner_reports, name='partner_reports'),
    path('partner/settings/', views.partner_settings, name='partner_settings'),
    
    # Public API
    path('api/courses/', views.api_courses, name='api_courses'),
    path('api/notifications/', views.api_notifications, name='api_notifications'),
    path('api/notifications/read/', views.api_mark_notification_read, name='api_mark_notification_read'),
    path('api/update-language/', views.api_update_language, name='api_update_language'),
    path('api/teacher/activity-feed/', views.api_teacher_activity_feed, name='api_teacher_activity_feed'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
