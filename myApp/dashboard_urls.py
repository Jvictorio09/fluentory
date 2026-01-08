"""
Custom Admin Dashboard URLs
Separate from Django Admin - this is for end users (content managers, admins)
who need user-friendly workflows, not technical database access.
"""
from django.urls import path
from . import dashboard_views

app_name = 'dashboard'

urlpatterns = [
    # Dashboard Overview
    path('', dashboard_views.dashboard_overview, name='overview'),
    
    # Role Switcher & Impersonation
    path('switch-role/', dashboard_views.dashboard_switch_role, name='switch_role'),
    path('stop-impersonation/', dashboard_views.dashboard_stop_impersonation, name='stop_impersonation'),
    
    # Content Management (User-friendly workflows)
    path('content/hero/', dashboard_views.dashboard_hero, name='hero'),
    path('content/site-images/', dashboard_views.dashboard_site_images, name='site_images'),
    
    # Media Management (User-friendly interface)
    path('media/', dashboard_views.dashboard_media, name='media'),
    path('media/add/', dashboard_views.dashboard_media_add, name='media_add'),
    path('media/<int:media_id>/edit/', dashboard_views.dashboard_media_edit, name='media_edit'),
    path('media/<int:media_id>/delete/', dashboard_views.dashboard_media_delete, name='media_delete'),
    
    # User Management (User-friendly interface)
    path('users/', dashboard_views.dashboard_users, name='users'),
    path('users/create/', dashboard_views.dashboard_user_create, name='user_create'),
    path('users/<int:user_id>/login-as/', dashboard_views.dashboard_login_as, name='login_as'),
    
    # Course Management (User-friendly interface)
    path('courses/', dashboard_views.dashboard_courses, name='courses'),
    path('courses/create/', dashboard_views.dashboard_course_create, name='course_create'),
    path('courses/<int:course_id>/edit/', dashboard_views.dashboard_course_edit, name='course_edit'),
    path('courses/<int:course_id>/toggle-publish/', dashboard_views.dashboard_course_toggle_publish, name='course_toggle_publish'),
    
    # Teacher Management
    path('teachers/', dashboard_views.dashboard_teachers, name='teachers'),
    path('teachers/<int:teacher_id>/details/', dashboard_views.dashboard_teacher_details, name='teacher_details'),
    path('teachers/<int:teacher_id>/reset-password/', dashboard_views.dashboard_teacher_reset_password, name='teacher_reset_password'),
    path('teachers/<int:teacher_id>/force-password-reset/', dashboard_views.dashboard_teacher_force_password_reset, name='teacher_force_password_reset'),
    path('teachers/<int:teacher_id>/approve/', dashboard_views.dashboard_teacher_approve, name='teacher_approve'),
    path('teachers/<int:teacher_id>/reject/', dashboard_views.dashboard_teacher_reject, name='teacher_reject'),
    path('teachers/<int:teacher_id>/assign-course/', dashboard_views.dashboard_teacher_assign_course, name='teacher_assign_course'),
    path('teachers/<int:teacher_id>/remove-course/<int:assignment_id>/', dashboard_views.dashboard_teacher_remove_course, name='teacher_remove_course'),
    
    # Manual Enrollment
    path('manual-enroll/', dashboard_views.dashboard_manual_enroll, name='manual_enroll'),
    
    # Payment Management (User-friendly interface)
    path('payments/', dashboard_views.dashboard_payments, name='payments'),
    
    # Gifted Courses Management
    path('gifted-courses/', dashboard_views.dashboard_gifted_courses, name='gifted_courses'),
    path('gifted-courses/<int:gift_id>/resend-email/', dashboard_views.dashboard_resend_gift_email, name='resend_gift_email'),
    path('gifted-courses/<int:gift_id>/manual-claim/', dashboard_views.dashboard_manual_claim_gift, name='manual_claim_gift'),
    
    # Live Classes Management
    path('live-classes/', dashboard_views.dashboard_live_classes, name='live_classes'),
    path('live-classes/create/', dashboard_views.dashboard_live_class_create, name='live_class_create'),
    path('live-classes/<int:session_id>/', dashboard_views.dashboard_live_class_detail, name='live_class_detail'),
    path('live-classes/<int:session_id>/edit/', dashboard_views.dashboard_live_class_edit, name='live_class_edit'),
    path('api/check-teacher-availability/', dashboard_views.dashboard_check_teacher_availability, name='check_teacher_availability'),
    
    # Analytics Dashboard
    path('analytics/', dashboard_views.dashboard_analytics, name='analytics'),
    
    # CRM - Lead Tracker
    path('leads/', dashboard_views.dashboard_leads, name='leads'),
    path('leads/create/', dashboard_views.dashboard_lead_create, name='lead_create'),
    path('leads/<int:lead_id>/', dashboard_views.dashboard_lead_detail, name='lead_detail'),
    path('leads/<int:lead_id>/edit/', dashboard_views.dashboard_lead_edit, name='lead_edit'),
    path('leads/<int:lead_id>/add-note/', dashboard_views.dashboard_lead_add_note, name='lead_add_note'),
    path('leads/<int:lead_id>/link-user/', dashboard_views.dashboard_lead_link_user, name='lead_link_user'),
    path('leads/<int:lead_id>/link-gift/', dashboard_views.dashboard_lead_link_gift, name='lead_link_gift'),
    path('leads/<int:lead_id>/link-enrollment/', dashboard_views.dashboard_lead_link_enrollment, name='lead_link_enrollment'),
    path('crm-analytics/', dashboard_views.dashboard_crm_analytics, name='crm_analytics'),
]

