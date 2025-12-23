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
    
    # Student routes
    path('student/', views.student_home, name='student_home'),
    path('student/courses/', views.student_courses, name='student_courses'),
    path('student/courses/<slug:slug>/', views.student_course_detail, name='student_course_detail'),
    path('student/placement/', views.student_placement, name='student_placement'),
    path('student/learning/', views.student_learning, name='student_learning'),
    path('student/certificates/', views.student_certificates, name='student_certificates'),
    path('student/settings/', views.student_settings, name='student_settings'),
    path('student/player/', views.student_course_player, name='student_course_player'),
    path('student/player/<int:enrollment_id>/', views.student_course_player, name='student_course_player_enrollment'),
    path('student/player/<int:enrollment_id>/lesson/<int:lesson_id>/', views.student_course_player, name='student_course_player_lesson'),
    
    # Quiz
    path('student/quiz/<int:quiz_id>/', views.take_quiz, name='take_quiz'),
    path('student/quiz/result/<int:attempt_id>/', views.quiz_result, name='quiz_result'),
    
    # Student API endpoints
    path('api/mark-complete/', views.mark_lesson_complete, name='mark_lesson_complete'),
    path('api/enroll/', views.enroll_course, name='enroll_course'),
    path('api/tutor/chat/', views.ai_tutor_chat, name='ai_tutor_chat'),
    
    # Certificate verification (public)
    path('verify/<uuid:certificate_id>/', views.verify_certificate, name='verify_certificate'),
    
    # Custom Admin Dashboard (User-facing admin tool)
    # Django Admin is at /django-admin/ for technical users
    path('dashboard/', include('myApp.dashboard_urls')),
    
    # Partner routes
    path('partner/', views.partner_overview, name='partner_overview'),
    path('partner/cohorts/', views.partner_cohorts, name='partner_cohorts'),
    
    # Public API
    path('api/courses/', views.api_courses, name='api_courses'),
    path('api/notifications/', views.api_notifications, name='api_notifications'),
    path('api/notifications/read/', views.api_mark_notification_read, name='api_mark_notification_read'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
