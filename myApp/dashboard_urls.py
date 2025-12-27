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
    
    # Teacher Management
    path('teachers/', dashboard_views.dashboard_teachers, name='teachers'),
    path('teachers/<int:teacher_id>/approve/', dashboard_views.dashboard_teacher_approve, name='teacher_approve'),
    path('teachers/<int:teacher_id>/reject/', dashboard_views.dashboard_teacher_reject, name='teacher_reject'),
    path('teachers/<int:teacher_id>/assign-course/', dashboard_views.dashboard_teacher_assign_course, name='teacher_assign_course'),
    path('teachers/<int:teacher_id>/remove-course/<int:assignment_id>/', dashboard_views.dashboard_teacher_remove_course, name='teacher_remove_course'),
    
    # Manual Enrollment
    path('manual-enroll/', dashboard_views.dashboard_manual_enroll, name='manual_enroll'),
    
    # Payment Management (User-friendly interface)
    path('payments/', dashboard_views.dashboard_payments, name='payments'),
]

