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

