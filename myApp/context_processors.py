"""
Context processors for Fluentory
"""
from .models import CoursePricing

def currency_context(request):
    """Add currency-related context to all templates"""
    # Get selected currency from session (default to USD)
    selected_currency = request.session.get('selected_currency', 'USD')
    
    # Available currencies
    available_currencies = [choice[0] for choice in CoursePricing.CURRENCY_CHOICES]
    
    return {
        'selected_currency': selected_currency,
        'available_currencies': available_currencies,
        'currency_choices': CoursePricing.CURRENCY_CHOICES,
    }

def hide_switch_view_context(request):
    """
    Determine whether to hide the "Switch View" button on specific public pages.
    Returns True to hide the button on:
    - Landing/Home page (/)
    - Footer pages (About, Careers, Blog, Help Center, Contact, Privacy, Terms, Cookies)
    Returns False to show on marketing pages (Courses, Outcomes, Proof, Pricing).
    """
    path = request.path
    
    # Hide on home page (exact match)
    if path == '/':
        return {'hide_switch_view': True}
    
    # Exact matches for footer pages
    exact_paths = ['/about/', '/careers/', '/contact/', '/privacy/', '/terms/', '/cookies/']
    if path in exact_paths:
        return {'hide_switch_view': True}
    
    # Prefix matches for blog routes
    if path.startswith('/blog/'):
        return {'hide_switch_view': True}
    
    # Prefix matches for help center routes
    if path.startswith('/help-center/') or path.startswith('/help/'):
        return {'hide_switch_view': True}
    
    # Default: show Switch View button (for marketing pages: Courses, Outcomes, Proof, Pricing)
    return {'hide_switch_view': False}

