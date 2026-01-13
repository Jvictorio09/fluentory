# Quick Setup: English to Arabic Translation

## Priority: English → Arabic

This is a quick-start guide specifically for implementing Arabic translation on your Fluentory website.

---

## Step-by-Step Implementation

### 1. Update Settings (`myProject/settings.py`)

Add these configurations:

```python
# Internationalization (around line 145)
LANGUAGE_CODE = 'en-us'
USE_I18N = True
USE_L10N = True  # Enable localization
USE_TZ = True

# Supported languages (Arabic prioritized)
LANGUAGES = [
    ('en', 'English'),
    ('ar', 'العربية'),  # Arabic
]

# Path to translation files
LOCALE_PATHS = [
    BASE_DIR / 'locale',
]
```

**Add LocaleMiddleware** (in MIDDLEWARE list, around line 53-61):
```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',  # ADD THIS LINE (after SessionMiddleware)
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    # ... rest of middleware
]
```

### 2. Update URLs (`myProject/urls.py`)

```python
from django.conf.urls.i18n import i18n_patterns
from django.urls import path, include
from django.contrib import admin

urlpatterns = [
    # Language switcher endpoint
    path('i18n/', include('django.conf.urls.i18n')),
    
    # API endpoints (don't need translation)
    path('api/', include('myApp.urls')),  # If you have API URLs
]

# URLs that need translation (wrap in i18n_patterns)
urlpatterns += i18n_patterns(
    path('django-admin/', admin.site.urls),
    path('', include('myApp.urls')),  # Your main app URLs
    prefix_default_language=False,  # Don't prefix /en/ for English
)
```

### 3. Create Arabic Translation File

```bash
# Create translation file for Arabic (exclude venv and other unnecessary directories)
python manage.py makemessages -l ar --ignore=venv --ignore=staticfiles --ignore=static --ignore=.git --ignore=node_modules --ignore=__pycache__ --ignore=*.pyc
```

**Important:** Always use the `--ignore` flags to exclude `venv` and other directories. This prevents errors from third-party packages.

This creates: `locale/ar/LC_MESSAGES/django.po`

### 4. Add Arabic Translations

Open `locale/ar/LC_MESSAGES/django.po` and translate:

```po
# Example translations
msgid "Welcome to Fluentory"
msgstr "مرحباً بك في Fluentory"

msgid "Dashboard"
msgstr "لوحة التحكم"

msgid "Courses"
msgstr "الدورات"

msgid "Login"
msgstr "تسجيل الدخول"

msgid "Sign Up"
msgstr "إنشاء حساب"

msgid "My Courses"
msgstr "دوراتي"

msgid "Settings"
msgstr "الإعدادات"

msgid "Logout"
msgstr "تسجيل الخروج"

msgid "Start learning today"
msgstr "ابدأ التعلم اليوم"

msgid "View Program"
msgstr "عرض البرنامج"

msgid "Enroll Now"
msgstr "سجل الآن"
```

### 5. Compile Translations

```bash
python manage.py compilemessages
```

This creates `locale/ar/LC_MESSAGES/django.mo` (binary file Django uses).

### 6. Update Templates

Add translation tags to your templates:

**Before:**
```html
<h1>Welcome to Fluentory</h1>
<p>Start learning today</p>
<a href="/courses">Courses</a>
```

**After:**
```html
{% load i18n %}
<h1>{% trans "Welcome to Fluentory" %}</h1>
<p>{% trans "Start learning today" %}</p>
<a href="{% url 'student_courses' %}">{% trans "Courses" %}</a>
```

**Key Template Tags:**
- `{% load i18n %}` - Load translation tags (add at top of template)
- `{% trans "Text" %}` - Translate text
- `{% blocktrans %}Text with {{ variable }}{% endblocktrans %}` - Translate with variables
- `{% blocktrans count counter=items|length %}...{% endblocktrans %}` - Pluralization

### 7. Create Language Switcher

Create `myApp/templates/partials/language_switcher.html`:

```html
{% load i18n %}
<form action="{% url 'set_language' %}" method="post" class="inline">
    {% csrf_token %}
    <input name="next" type="hidden" value="{{ request.get_full_path }}" />
    <select name="language" onchange="this.form.submit()" class="px-3 py-2 rounded-lg border border-white/10 bg-[#254346]/50 text-white text-sm">
        {% get_current_language as CURRENT_LANGUAGE %}
        <option value="en" {% if CURRENT_LANGUAGE == 'en' %}selected{% endif %}>English</option>
        <option value="ar" {% if CURRENT_LANGUAGE == 'ar' %}selected{% endif %}>العربية</option>
    </select>
</form>
```

Add to your base template (e.g., `myApp/templates/base.html` or navbar):

```html
{% include 'partials/language_switcher.html' %}
```

### 8. Add RTL Support for Arabic (Important!)

Arabic is right-to-left, so add CSS support:

**Option 1: Simple CSS (in your base template or CSS file)**
```html
<style>
    html[dir="rtl"] {
        direction: rtl;
        text-align: right;
    }
    html[dir="rtl"] .navbar,
    html[dir="rtl"] .menu {
        direction: rtl;
    }
</style>

<script>
    // Set RTL direction for Arabic
    document.addEventListener('DOMContentLoaded', function() {
        const lang = '{{ LANGUAGE_CODE|default:"en" }}';
        if (lang === 'ar') {
            document.documentElement.setAttribute('dir', 'rtl');
        } else {
            document.documentElement.setAttribute('dir', 'ltr');
        }
    });
</script>
```

**Option 2: Use Django's built-in RTL (in base template)**
```html
{% load i18n %}
<html lang="{{ LANGUAGE_CODE|default:'en' }}" dir="{% if LANGUAGE_CODE == 'ar' %}rtl{% else %}ltr{% endif %}">
```

### 9. Update Python Code (Views)

For messages and user-facing strings:

```python
from django.utils.translation import gettext as _
from django.contrib import messages

# In views
messages.success(request, _('Course created successfully'))
messages.error(request, _('An error occurred'))
```

---

## Quick Checklist

- [ ] Add `LocaleMiddleware` to MIDDLEWARE
- [ ] Add `LANGUAGES` and `LOCALE_PATHS` to settings
- [ ] Update URLs with `i18n_patterns`
- [ ] Run `makemessages -l ar`
- [ ] Translate strings in `django.po`
- [ ] Run `compilemessages`
- [ ] Add `{% load i18n %}` and `{% trans %}` to templates
- [ ] Add language switcher component
- [ ] Add RTL CSS support
- [ ] Test language switching

---

## Testing

1. Start your development server:
```bash
python manage.py runserver
```

2. Visit your site and use the language switcher
3. URLs should change: `/courses/` → `/ar/courses/` (or stay as `/courses/` for English)
4. All translated text should appear in Arabic
5. Layout should switch to RTL for Arabic

---

## Common Issues

### Translations not showing?
- Make sure you ran `compilemessages`
- Check that `LocaleMiddleware` is in MIDDLEWARE
- Clear browser cache
- Verify `.po` file has `msgstr` filled (not empty)

### RTL not working?
- Check `dir="rtl"` is set on `<html>` tag
- Add CSS rules for RTL layouts
- Test with Arabic text to verify direction

### URLs not working?
- Ensure `i18n_patterns` wraps your URLs
- Check middleware order (LocaleMiddleware after SessionMiddleware)

### Windows: "Can't find msguniq" error?
This error occurs on Windows because GNU gettext tools are not installed by default.

**Solution 1: Download and install manually (Easiest - Recommended)**
1. Download gettext for Windows: https://mlocati.github.io/articles/gettext-iconv-windows.html
   - Click "Download gettext" button
   - Choose the "Complete package, except dependencies" version (smallest file)
2. Extract the ZIP file (e.g., to `C:\gettext`)
3. Add to PATH:
   - Open System Properties → Environment Variables
   - Edit "Path" variable
   - Add: `C:\gettext\bin` (or wherever you extracted it)
   - Click OK on all dialogs
4. **Restart your terminal/IDE** (important!)
5. Verify: Run `xgettext --version` in terminal (should show version number)

**Solution 2: Using Git for Windows (If already installed)**
- Git for Windows includes gettext tools
- Check if `C:\Program Files\Git\usr\bin` is in your PATH
- If not, add it to PATH (same steps as above)
- Restart terminal and try again

**Solution 3: Use Docker/WSL** (Alternative)
- Run Django commands in Docker or WSL (Windows Subsystem for Linux)
- Both have gettext tools pre-installed

**Solution 4: Skip for now (Optional)**
- The translation system works without gettext installed
- You can manually create translation files or install gettext later
- All the infrastructure (settings, URLs, templates) is already set up

**After installation:**
- Restart your terminal/IDE
- Run `python manage.py makemessages -l ar --ignore=venv --ignore=staticfiles --ignore=static --ignore=.git --ignore=node_modules --ignore=__pycache__ --ignore=*.pyc` again

### Error: "xgettext: found 1 fatal error" or warnings from venv packages?

This happens when `makemessages` scans your `venv` directory (third-party packages). The solution is simple:

**Always use `--ignore` flags:**
```bash
python manage.py makemessages -l ar --ignore=venv --ignore=staticfiles --ignore=static --ignore=.git --ignore=node_modules --ignore=__pycache__ --ignore=*.pyc
```

**Why this happens:**
- `makemessages` scans all Python files in your project by default
- Your `venv` folder contains third-party packages that may have translation issues
- These packages aren't your code, so you don't need to translate them

**The fix:**
- Always include `--ignore=venv` (and other ignore flags) when running `makemessages`
- This tells Django to skip scanning those directories
- Only your application code will be scanned for translatable strings

---

## Next Steps

1. **Start with high-traffic pages**: Home, Login, Dashboard, Courses
2. **Translate incrementally**: Don't try to translate everything at once
3. **Get native speaker review**: Have Arabic speakers review translations
4. **Add more languages later**: Once Arabic is working, add other languages

---

## Helpful Commands

```bash
# Create Arabic translation file (with ignore flags to exclude venv)
python manage.py makemessages -l ar --ignore=venv --ignore=staticfiles --ignore=static --ignore=.git --ignore=node_modules --ignore=__pycache__ --ignore=*.pyc

# Compile translations
python manage.py compilemessages

# Check for missing translations
python manage.py makemessages -l ar --check --ignore=venv --ignore=staticfiles --ignore=static --ignore=.git --ignore=node_modules --ignore=__pycache__ --ignore=*.pyc

# Update translations (keeps old ones)
python manage.py makemessages -l ar --no-obsolete --ignore=venv --ignore=staticfiles --ignore=static --ignore=.git --ignore=node_modules --ignore=__pycache__ --ignore=*.pyc
```

**Note:** Always include the `--ignore` flags to avoid scanning third-party packages in `venv` which can cause errors.

---

**Priority: Get Arabic working first, then expand to other languages!**

