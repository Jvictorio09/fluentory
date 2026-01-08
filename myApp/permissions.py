"""
Strict role-based permission system for Fluentory.
Enforces admin-only vs teacher permissions at view and UI level.
"""
from functools import wraps
from django.shortcuts import render
from django.http import HttpResponseForbidden
from django.contrib import messages
from django.shortcuts import redirect
from .views import get_or_create_profile


def admin_required(view_func):
    """
    Decorator that ensures only admins can access a view.
    Teachers and other roles get 403 Access Denied.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        # Allow superusers/staff
        if request.user.is_superuser or request.user.is_staff:
            return view_func(request, *args, **kwargs)
        
        # Check profile role
        profile = get_or_create_profile(request.user)
        
        if profile.role == 'admin':
            return view_func(request, *args, **kwargs)
        
        # Not an admin - show 403
        return render(request, '403.html', status=403)
    
    return wrapper


def teacher_only(view_func):
    """
    Decorator that ensures only teachers can access a view.
    Teachers can ONLY view their assigned live classes and related data.
    Admins are blocked from teacher-only views (unless explicitly allowed).
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        profile = get_or_create_profile(request.user)
        
        # Only allow teachers (instructor role)
        if profile.role == 'instructor':
            # Verify they have a teacher profile
            if hasattr(request.user, 'teacher_profile'):
                return view_func(request, *args, **kwargs)
        
        # Not a teacher - show 403
        return render(request, '403.html', status=403)
    
    return wrapper


def is_admin(user):
    """Check if user is an admin"""
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    profile = get_or_create_profile(user)
    return profile.role == 'admin'


def is_teacher(user):
    """Check if user is a teacher"""
    if not user.is_authenticated:
        return False
    profile = get_or_create_profile(user)
    return profile.role == 'instructor' and hasattr(user, 'teacher_profile')


def teacher_can_access_live_class(teacher, live_class):
    """
    Check if a teacher can access a specific live class.
    Teachers can ONLY access live classes assigned to them.
    """
    if not teacher or not live_class:
        return False
    
    # Check if teacher is assigned to this live class
    return live_class.assigned_teacher == teacher


def teacher_can_access_course(teacher, course):
    """
    Check if a teacher can access a specific course.
    Teachers can access courses they are assigned to.
    """
    if not teacher or not course:
        return False
    
    # Check if teacher is assigned to this course
    from myApp.models import CourseTeacher
    return CourseTeacher.objects.filter(
        teacher=teacher,
        course=course
    ).exists()

