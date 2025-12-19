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
    
    # Course Management (User-friendly interface)
    path('courses/', dashboard_views.dashboard_courses, name='courses'),
    
    # Payment Management (User-friendly interface)
    path('payments/', dashboard_views.dashboard_payments, name='payments'),
]

