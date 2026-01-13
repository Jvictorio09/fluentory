# Website Translation Guide - Simple & Effective Solution
## English → Arabic Translation (Primary Focus)

## Overview
This guide provides a simple, effective way to implement multi-language support for your Django website using Django's built-in internationalization (i18n) framework. This solution is lightweight, maintainable, and doesn't overcomplicate your codebase.

**Primary Focus: English to Arabic Translation**

---

## Quick Start for Arabic (3 Steps)

### Step 1: Configure Settings
Add these settings to `myProject/settings.py`:

```python
# Internationalization
LANGUAGE_CODE = 'en-us'
USE_I18N = True
USE_L10N = True  # Enable localization (number/date formatting)
USE_TZ = True

# Supported languages (Arabic prioritized)
LANGUAGES = [
    ('en', 'English'),
    ('ar', 'العربية'),  # Arabic
    # Add more languages later as needed
    # ('es', 'Spanish'),
    # ('fr', 'French'),
]

# Path to translation files
LOCALE_PATHS = [
    BASE_DIR / 'locale',  # Creates locale/ folder in project root
]

# Add LocaleMiddleware (IMPORTANT: Must be after SessionMiddleware)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',  # Add this line
    'django.middleware.common.CommonMiddleware',
    # ... rest of your middleware
]
```

### Step 2: Update URLs
Add language prefix to URLs in `myProject/urls.py`:

```python
from django.conf.urls.i18n import i18n_patterns
from django.utils.translation import gettext_lazy as _

urlpatterns = [
    # Include admin with i18n
    path('i18n/', include('django.conf.urls.i18n')),
    # Your other non-translated URLs here (API endpoints, etc.)
]

# URLs that need translation
urlpatterns += i18n_patterns(
    path('admin/', admin.site.urls),
    path('', include('myApp.urls')),
    # ... your other app URLs
    prefix_default_language=False,  # Don't prefix default language (en)
)
```

### Step 3: Wrap Text in Templates
Replace hardcoded text with translation tags:

**Before:**
```html
<h1>Welcome to Fluentory</h1>
<p>Start learning today</p>
```

**After:**
```html
{% load i18n %}
<h1>{% trans "Welcome to Fluentory" %}</h1>
<p>{% trans "Start learning today" %}</p>
```

---

## Implementation Workflow

### Phase 1: Mark Text for Translation

#### In Templates:
```html
{% load i18n %}

<!-- Simple text -->
{% trans "Dashboard" %}

<!-- With context -->
{% trans "Save" context "button" %}

<!-- Variables -->
{% blocktrans with name=user.name %}Welcome, {{ name }}{% endblocktrans %}

<!-- Pluralization -->
{% blocktrans count counter=items|length %}
    You have {{ counter }} item.
{% plural %}
    You have {{ counter }} items.
{% endblocktrans %}
```

#### In Python Code:
```python
from django.utils.translation import gettext_lazy as _, gettext, ngettext

# For model fields (use lazy version)
class Course(models.Model):
    title = models.CharField(_('Title'), max_length=200)
    description = models.TextField(_('Description'))

# For views (regular gettext is fine)
from django.utils.translation import gettext
messages.success(request, gettext('Course created successfully'))

# Pluralization
count = items.count()
message = ngettext(
    'There is %(count)d item.',
    'There are %(count)d items.',
    count
) % {'count': count}
```

### Phase 2: Generate Translation Files

```bash
# 1. Create translation files for all languages (IMPORTANT: exclude venv to avoid errors)
python manage.py makemessages -l es --ignore=venv --ignore=staticfiles --ignore=static --ignore=.git --ignore=node_modules --ignore=__pycache__ --ignore=*.pyc  # Spanish
python manage.py makemessages -l fr --ignore=venv --ignore=staticfiles --ignore=static --ignore=.git --ignore=node_modules --ignore=__pycache__ --ignore=*.pyc  # French
python manage.py makemessages -l de --ignore=venv --ignore=staticfiles --ignore=static --ignore=.git --ignore=node_modules --ignore=__pycache__ --ignore=*.pyc  # German
# ... repeat for each language

# OR create all at once (if you have all language folders)
python manage.py makemessages -a --ignore=venv --ignore=staticfiles --ignore=static --ignore=.git --ignore=node_modules --ignore=__pycache__ --ignore=*.pyc

# 2. This creates/updates .po files in locale/es/LC_MESSAGES/django.po
```

**Important:** Always include `--ignore=venv` and other ignore flags to prevent errors from third-party packages.

### Phase 3: Translate

1. Open `locale/es/LC_MESSAGES/django.po`
2. Find the `msgstr ""` entries
3. Add translations:

```po
msgid "Welcome to Fluentory"
msgstr "Bienvenido a Fluentory"

msgid "Dashboard"
msgstr "Panel de control"

msgid "Start learning today"
msgstr "Comienza a aprender hoy"
```

### Phase 4: Compile Translations

```bash
python manage.py compilemessages
```

This creates `.mo` files (binary format Django uses).

---

## Language Switcher Component

Create a simple language switcher for your templates:

**Template: `templates/partials/language_switcher.html`**
```html
{% load i18n %}
<form action="{% url 'set_language' %}" method="post" class="inline">
    {% csrf_token %}
    <input name="next" type="hidden" value="{{ request.get_full_path }}" />
    <select name="language" onchange="this.form.submit()" class="language-select">
        {% get_current_language as CURRENT_LANGUAGE %}
        {% get_available_languages as LANGUAGES %}
        {% for language_code, language_name in LANGUAGES %}
            <option value="{{ language_code }}" 
                    {% if language_code == CURRENT_LANGUAGE %}selected{% endif %}>
                {{ language_name }}
            </option>
        {% endfor %}
    </select>
</form>
```

**Add to your base template:**
```html
{% include 'partials/language_switcher.html' %}
```

---

## Best Practices

### 1. **Use Descriptive Keys**
```python
# Bad
_("msg1")

# Good
_("Welcome to the dashboard")
```

### 2. **Keep Context in Mind**
```python
# "Save" could mean different things
_("Save")  # Generic
_("Save changes")  # More specific - better
```

### 3. **Don't Translate Variables**
```python
# Bad
_("Welcome, " + username)

# Good
_("Welcome, %(username)s") % {"username": username}
# Or in templates:
{% blocktrans with name=username %}Welcome, {{ name }}{% endblocktrans %}
```

### 4. **Handle Plurals Properly**
```python
# Use ngettext for plural forms
message = ngettext(
    'You have %(count)d course.',
    'You have %(count)d courses.',
    count
) % {'count': count}
```

### 5. **Mark Strings in Models**
```python
from django.utils.translation import gettext_lazy as _

class Course(models.Model):
    title = models.CharField(_('Title'), max_length=200)
    
    class Meta:
        verbose_name = _('Course')
        verbose_name_plural = _('Courses')
```

---

## Handling Dynamic Content

### Database Content Translation

For user-generated content (courses, lessons, etc.), you have two options:

#### Option 1: Separate Translation Fields (Simple)
```python
class Course(models.Model):
    title_en = models.CharField(max_length=200)
    title_es = models.CharField(max_length=200, blank=True)
    title_fr = models.CharField(max_length=200, blank=True)
    description_en = models.TextField()
    description_es = models.TextField(blank=True)
    description_fr = models.TextField(blank=True)
    
    def title(self):
        lang = get_language()
        return getattr(self, f'title_{lang}', self.title_en)
    
    def description(self):
        lang = get_language()
        return getattr(self, f'description_{lang}', self.description_en)
```

#### Option 2: Use django-modeltranslation (Recommended for complex cases)
```bash
pip install django-modeltranslation
```

```python
# translation.py
from modeltranslation.translator import translator, TranslationOptions
from myApp.models import Course

class CourseTranslationOptions(TranslationOptions):
    fields = ('title', 'description', 'outcome')

translator.register(Course, CourseTranslationOptions)
```

---

## Common Commands (Arabic Focus)

```bash
# Create/update Arabic translation file (IMPORTANT: exclude venv to avoid errors)
python manage.py makemessages -l ar --ignore=venv --ignore=staticfiles --ignore=static --ignore=.git --ignore=node_modules --ignore=__pycache__ --ignore=*.pyc

# Compile Arabic translations
python manage.py compilemessages

# Check for missing Arabic translations
python manage.py makemessages -l ar --check --ignore=venv --ignore=staticfiles --ignore=static --ignore=.git --ignore=node_modules --ignore=__pycache__ --ignore=*.pyc

# Update existing Arabic translations (keep old translations)
python manage.py makemessages -l ar --no-obsolete --ignore=venv --ignore=staticfiles --ignore=static --ignore=.git --ignore=node_modules --ignore=__pycache__ --ignore=*.pyc

# For all languages (when you add more later)
python manage.py makemessages -a --ignore=venv --ignore=staticfiles --ignore=static --ignore=.git --ignore=node_modules --ignore=__pycache__ --ignore=*.pyc
```

**Note:** Always include the `--ignore` flags to avoid scanning third-party packages in `venv` which can cause fatal errors.

---

## File Structure

After setup, your project will look like:

```
myProject/
├── locale/
│   ├── es/
│   │   └── LC_MESSAGES/
│   │       ├── django.po
│   │       └── django.mo
│   ├── fr/
│   │   └── LC_MESSAGES/
│   │       ├── django.po
│   │       └── django.mo
│   └── ...
├── myApp/
├── templates/
└── manage.py
```

---

## Testing Translations

### Test in Development:
1. Add a language to your browser preferences
2. Django will automatically detect it
3. Or use the language switcher

### Test Programmatically:
```python
from django.utils import translation

# Activate a language
translation.activate('es')

# Your code here
# ...

# Deactivate (restore default)
translation.deactivate()
```

---

## Deployment Checklist

- [ ] Run `makemessages` for all languages
- [ ] Complete all translations in `.po` files
- [ ] Run `compilemessages`
- [ ] Add `locale/` folder to version control (or ignore and rebuild on server)
- [ ] Ensure `LocaleMiddleware` is in `MIDDLEWARE`
- [ ] Test language switching
- [ ] Test URLs with language prefixes

---

## Troubleshooting

### Translations not showing?
1. Check `USE_I18N = True` in settings
2. Verify `LocaleMiddleware` is in `MIDDLEWARE`
3. Run `compilemessages`
4. Clear browser cache
5. Check `.po` files have `msgstr` filled in (not empty)

### URLs not working with language prefix?
- Ensure `i18n_patterns` is used in `urls.py`
- Check middleware order (LocaleMiddleware after SessionMiddleware)

### Missing translations?
- Run `makemessages -a --ignore=venv --ignore=staticfiles --ignore=static --ignore=.git --ignore=node_modules --ignore=__pycache__ --ignore=*.pyc` to regenerate `.po` files
- Check that text is wrapped in `{% trans %}` or `gettext()`

---

## Migration Strategy (Recommended Approach)

1. **Week 1**: Set up infrastructure (settings, middleware, URLs)
2. **Week 2**: Add translation tags to high-traffic pages (home, login, dashboard)
3. **Week 3**: Translate one language (start with most common)
4. **Week 4**: Add remaining languages gradually
5. **Ongoing**: Translate new content as you add features

**Start small**: Begin with the most visible pages, then expand.

---

## Quick Reference

| Task | Command |
|------|---------|
| Create Arabic translation file | `python manage.py makemessages -l ar --ignore=venv --ignore=staticfiles --ignore=static --ignore=.git --ignore=node_modules --ignore=__pycache__ --ignore=*.pyc` |
| Create for all languages | `python manage.py makemessages -a --ignore=venv --ignore=staticfiles --ignore=static --ignore=.git --ignore=node_modules --ignore=__pycache__ --ignore=*.pyc` |
| Compile translations | `python manage.py compilemessages` |
| Template tag | `{% load i18n %}` then `{% trans "Text" %}` |
| Python code | `from django.utils.translation import gettext_lazy as _` |

---

## Additional Resources

- [Django i18n Documentation](https://docs.djangoproject.com/en/stable/topics/i18n/)
- [Translation Best Practices](https://docs.djangoproject.com/en/stable/topics/i18n/translation/)
- [LocaleMiddleware](https://docs.djangoproject.com/en/stable/ref/middleware/#django.middleware.locale.LocaleMiddleware)

---

**Remember**: Start simple, translate incrementally, and don't try to translate everything at once. Focus on user-facing content first, then expand to admin interfaces and error messages.

