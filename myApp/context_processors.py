"""
Context processors for Fluentory
"""
from django.conf import settings
from .models import CoursePricing, SiteSettings

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

def social_links_context(request):
    """Add social media links context to all templates - uses DB values or defaults"""
    # Get default links from settings
    defaults = getattr(settings, 'SOCIAL_LINKS_DEFAULT', {})
    
    # Initialize with defaults
    linkedin_url = defaults.get('linkedin', None)
    instagram_url = defaults.get('instagram', None)
    facebook_url = defaults.get('facebook', None)
    twitter_url = defaults.get('twitter', None)
    whatsapp_url = defaults.get('whatsapp', None)
    
    # Track source for debug
    debug_source = {
        'linkedin': 'default',
        'instagram': 'default',
        'facebook': 'default',
        'twitter': 'default',
        'whatsapp': 'default',
    }
    
    try:
        from django.db import connection, ProgrammingError
        
        # Try to get values from database
        try:
            with connection.cursor() as cursor:
                # Get all social link fields that definitely exist
                cursor.execute("""
                    SELECT linkedin_url, instagram_url, facebook_url, twitter_url
                    FROM myApp_sitesettings 
                    WHERE id = 1;
                """)
                result = cursor.fetchone()
                if result:
                    # Use DB value if non-empty, else keep default
                    if result[0]:
                        linkedin_url = result[0]
                        debug_source['linkedin'] = 'db'
                    if result[1]:
                        instagram_url = result[1]
                        debug_source['instagram'] = 'db'
                    if result[2]:
                        facebook_url = result[2]
                        debug_source['facebook'] = 'db'
                    if result[3]:
                        twitter_url = result[3]
                        debug_source['twitter'] = 'db'
                
                # Check if whatsapp_number column exists and get it if it does
                if 'postgresql' in connection.vendor:
                    cursor.execute("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_schema = 'public' 
                        AND table_name = 'myApp_sitesettings'
                        AND column_name = 'whatsapp_number';
                    """)
                    whatsapp_column_exists = cursor.fetchone() is not None
                    
                    if whatsapp_column_exists:
                        cursor.execute("SELECT whatsapp_number FROM myApp_sitesettings WHERE id = 1;")
                        result = cursor.fetchone()
                        whatsapp_number = result[0] if result and result[0] else None
                        
                        if whatsapp_number:
                            # Remove any spaces, dashes, or parentheses from the number
                            clean_number = whatsapp_number.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
                            # Ensure it starts with + or add it
                            if not clean_number.startswith('+'):
                                clean_number = '+' + clean_number
                            whatsapp_url = f"https://wa.me/{clean_number}"
                            debug_source['whatsapp'] = 'db'
        except (ProgrammingError, Exception):
            # If query fails, try ORM as fallback
            try:
                site_settings = SiteSettings.get_solo()
                if site_settings.linkedin_url:
                    linkedin_url = site_settings.linkedin_url
                    debug_source['linkedin'] = 'db'
                if site_settings.instagram_url:
                    instagram_url = site_settings.instagram_url
                    debug_source['instagram'] = 'db'
                if site_settings.facebook_url:
                    facebook_url = site_settings.facebook_url
                    debug_source['facebook'] = 'db'
                if site_settings.twitter_url:
                    twitter_url = site_settings.twitter_url
                    debug_source['twitter'] = 'db'
                # Try WhatsApp if column exists
                try:
                    whatsapp_number = getattr(site_settings, 'whatsapp_number', None)
                    if whatsapp_number:
                        clean_number = whatsapp_number.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
                        if not clean_number.startswith('+'):
                            clean_number = '+' + clean_number
                        whatsapp_url = f"https://wa.me/{clean_number}"
                        debug_source['whatsapp'] = 'db'
                except (AttributeError, ProgrammingError):
                    pass
            except Exception:
                # If ORM also fails, keep defaults
                pass
    except Exception:
        # If everything fails, keep defaults
        pass
    
    # Always return complete dict with all keys
    return {
        'social_links': {
            'linkedin': linkedin_url,
            'instagram': instagram_url,
            'facebook': facebook_url,
            'twitter': twitter_url,
            'whatsapp': whatsapp_url,
        },
        'social_links_debug_source': debug_source,  # Temporary debug flag
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

