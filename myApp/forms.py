"""
Django forms for the application
"""
from django import forms
from .models import Course, Category


class CourseCreateForm(forms.ModelForm):
    """Form for creating a new course"""
    
    # Define currency as explicit ChoiceField with real choices
    CURRENCY_CHOICES = [
        ('USD', 'USD - US Dollar'),
        ('EUR', 'EUR - Euro'),
        ('SAR', 'SAR - Saudi Riyal'),
        ('AED', 'AED - UAE Dirham'),
        ('JOD', 'JOD - Jordanian Dinar'),
        ('GBP', 'GBP - British Pound'),
    ]
    
    currency = forms.ChoiceField(
        choices=CURRENCY_CHOICES,
        required=True,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2.5 pr-10 rounded-lg border border-gray-200 dark:border-white/10 bg-white dark:bg-white/5 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-[#82C293]/40 focus:border-[#82C293]/50 transition-all',
            'style': 'cursor: pointer; position: relative; z-index: 10; -webkit-appearance: menulist; -moz-appearance: menulist; appearance: menulist;',
        })
    )
    
    class Meta:
        model = Course
        fields = ['title', 'slug', 'description', 'short_description', 'outcome', 
                  'category', 'level', 'course_type', 'price', 'is_free']
        # Note: currency is defined as explicit ChoiceField above, not from model
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-lg border border-gray-200 dark:border-white/10 bg-white dark:bg-white/5 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-[#82C293]/40 focus:border-[#82C293]/50 transition-all',
                'placeholder': 'Enter course title'
            }),
            'slug': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-lg border border-gray-200 dark:border-white/10 bg-white dark:bg-white/5 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-[#82C293]/40 focus:border-[#82C293]/50 transition-all',
                'placeholder': 'url-friendly-slug'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2.5 rounded-lg border border-gray-200 dark:border-white/10 bg-white dark:bg-white/5 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-[#82C293]/40 focus:border-[#82C293]/50 transition-all resize-y',
                'rows': 4,
                'placeholder': 'Enter a detailed description of your course'
            }),
            'short_description': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-lg border border-gray-200 dark:border-white/10 bg-white dark:bg-white/5 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-[#82C293]/40 focus:border-[#82C293]/50 transition-all',
            }),
            'outcome': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-lg border border-gray-200 dark:border-white/10 bg-white dark:bg-white/5 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-[#82C293]/40 focus:border-[#82C293]/50 transition-all',
            }),
            'category': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-lg border border-gray-200 dark:border-white/10 bg-white dark:bg-white/5 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-[#82C293]/40 focus:border-[#82C293]/50 transition-all',
            }),
            'level': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-lg border border-gray-200 dark:border-white/10 bg-white dark:bg-white/5 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-[#82C293]/40 focus:border-[#82C293]/50 transition-all',
            }),
            'course_type': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-lg border border-gray-200 dark:border-white/10 bg-white dark:bg-white/5 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-[#82C293]/40 focus:border-[#82C293]/50 transition-all',
            }),
            'price': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-lg border border-gray-200 dark:border-white/10 bg-white dark:bg-white/5 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-[#82C293]/40 focus:border-[#82C293]/50 transition-all',
                'step': '0.01',
                'min': '0'
            }),
            'is_free': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-[#82C293] bg-gray-100 border-gray-300 rounded focus:ring-[#82C293] focus:ring-2',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make slug optional (will be auto-generated)
        self.fields['slug'].required = False
        # Remove slug uniqueness validation - handled by model save()
        # This prevents form from blocking submission due to duplicate slugs
        if 'slug' in self.fields:
            # Remove unique constraint validation - model save() will handle uniqueness
            from django.core.validators import validate_slug
            self.fields['slug'].validators = [validate_slug]  # Keep only slug format validation
        
        self.fields['short_description'].required = False
        self.fields['outcome'].required = False
        self.fields['category'].required = False
        self.fields['price'].required = False
        
        # Currency is already defined as ChoiceField above with required=True
        # Set initial value
        self.fields['currency'].initial = 'USD'
        # Ensure choices are set (should already be set from field definition)
        if not self.fields['currency'].choices:
            self.fields['currency'].choices = self.CURRENCY_CHOICES
        
        self.fields['level'].required = False
        self.fields['level'].initial = 'beginner'
        
        # Ensure title and description are required (they should be by default, but make explicit)
        self.fields['title'].required = True
        self.fields['description'].required = True
        self.fields['course_type'].required = True
    
    def clean_slug(self):
        """Don't validate slug uniqueness here - let model save() handle it"""
        slug = self.cleaned_data.get('slug', '').strip()
        # Just return the slug, uniqueness will be handled by model's save() method
        # We don't check for duplicates here - model.save() will auto-append -2, -3, etc.
        return slug
    
    def full_clean(self):
        """Override to skip slug uniqueness validation"""
        super().full_clean()
        # Remove any slug uniqueness errors that might have been added
        if 'slug' in self._errors:
            # Remove only uniqueness-related errors, keep format errors
            self._errors['slug'] = [
                error for error in self._errors['slug'] 
                if 'already exists' not in str(error).lower() and 'unique' not in str(error).lower()
            ]
            # If no errors left, remove the field from errors
            if not self._errors['slug']:
                del self._errors['slug']
    
    def clean_currency(self):
        """Ensure currency defaults to USD if not provided"""
        currency = self.cleaned_data.get('currency', '').strip()
        return currency or 'USD'
    
    def clean_level(self):
        """Ensure level defaults to beginner if not provided"""
        level = self.cleaned_data.get('level', '').strip()
        return level or 'beginner'
    
    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price is not None and price < 0:
            raise forms.ValidationError('Price cannot be negative.')
        return price or 0

