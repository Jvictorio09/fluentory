"""
Template tags for permission checks in templates.
"""
from django import template
from myApp.permissions import is_admin, is_teacher

register = template.Library()


@register.filter
def user_is_admin(user):
    """Check if user is an admin"""
    return is_admin(user)


@register.filter
def user_is_teacher(user):
    """Check if user is a teacher"""
    return is_teacher(user)

