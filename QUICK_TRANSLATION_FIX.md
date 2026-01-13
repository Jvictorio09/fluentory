# Quick Guide: Adding Translation Tags to Templates

## The Problem
Only 8 strings were found because most templates don't have translation tags yet.

## Solution: Add `{% trans %}` tags to your templates

### Step 1: Add `{% load i18n %}` at the top of templates
```html
{% load i18n %}
```

### Step 2: Wrap text with `{% trans %}` or `{% translate %}`

**Before:**
```html
<h1>Welcome Back</h1>
<p>Sign in to continue your learning journey</p>
<button>Login</button>
```

**After:**
```html
{% load i18n %}
<h1>{% trans "Welcome Back" %}</h1>
<p>{% trans "Sign in to continue your learning journey" %}</p>
<button>{% trans "Login" %}</button>
```

### Step 3: For text with variables, use `{% blocktrans %}`

**Before:**
```html
<p>Welcome, {{ username }}</p>
```

**After:**
```html
{% blocktrans with name=username %}Welcome, {{ name }}{% endblocktrans %}
```

## Common Templates to Update (Priority Order)

1. **Landing Page** (`myApp/templates/landing.html` and partials)
   - Hero section
   - "Take the Free Placement Test"
   - "Browse Programs"
   - Headlines and descriptions

2. **Login/Signup** (`myApp/templates/auth/login.html`, `signup.html`)
   - "Welcome Back"
   - "Sign in to continue your learning journey"
   - Form labels and buttons

3. **Student Pages** (`myApp/templates/student/`)
   - "Continue"
   - "Your courses"
   - Navigation items

4. **Dashboard** (`myApp/templates/dashboard/`)
   - Page titles
   - Button labels
   - Status messages

## After Adding Tags

1. Run `makemessages` again:
   ```bash
   python manage.py makemessages -l ar --ignore=venv --ignore=staticfiles --ignore=static --ignore=.git --ignore=node_modules --ignore=__pycache__ --ignore=*.pyc
   ```

2. This will find ALL strings with translation tags

3. Translate the strings in `locale/ar/LC_MESSAGES/django.po`

4. Compile: `python manage.py compilemessages`

## Example: Login Template

**Current (no translations):**
```html
<h1 class="text-2xl font-semibold text-white mb-2">Welcome Back</h1>
<p class="text-sm text-white/60">Sign in to continue your learning journey</p>
```

**With translations:**
```html
{% load i18n %}
<h1 class="text-2xl font-semibold text-white mb-2">{% trans "Welcome Back" %}</h1>
<p class="text-sm text-white/60">{% trans "Sign in to continue your learning journey" %}</p>
```

## Tips

- Start with high-traffic pages (homepage, login, dashboard)
- Don't translate variable names or code
- Only translate user-facing text
- Keep translations simple and natural
- You can do this incrementally - add tags page by page


