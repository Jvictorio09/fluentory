# Translation Issues Found

## Problem: Some strings translated, some not

## Issues Found:

### 1. ✅ FIXED: Headline Mismatch
**Template (`hero.html` line 30-31):**
```html
{% trans "The Modern Way" %}
{% trans "To Learn Globally." %}
```

**`.po` file had:**
```po
msgid "The Modern Way To Learn Globally."  ❌ Wrong - one combined string
```

**Fixed to:**
```po
msgid "The Modern Way"
msgstr "الطريقة الحديثة"

msgid "To Learn Globally."
msgstr "للتعلم عالميًا."
```

### 2. ❌ MISSING: Templates without `{% trans %}` tags

These templates DON'T have translation tags yet, so strings aren't being translated:

- **`ai_tutor.html`** - Lines 174, 179, 184-185, 189-192, 198 (no `{% trans %}` tags)
- **`featured_courses.html`** - Lines 26, 30, 42, 47, 52, 57, 62, 67, 88, 95, 99, 105, 110, 118 (no `{% trans %}` tags)
- **`pricing.html`** - Needs translation tags
- **`certificates.html`** - Needs translation tags  
- **`faq.html`** - Needs translation tags

### 3. ✅ WORKING: Templates with tags AND translations

- `hero.html` - Has tags and translations (except headline - now fixed)
- `final_cta.html` - Has tags and translations
- `university_logos.html` - Has tags and translations
- `how_it_works.html` - Has tags (partial)

## Next Steps:

1. ✅ Fixed headline mismatch in `.po` file
2. **Recompile translations:** `python manage.py compilemessages`
3. **Add `{% trans %}` tags to remaining templates** (ai_tutor, featured_courses, pricing, certificates, faq)
4. Run `makemessages` again to extract new strings
5. Add translations for new strings

## Quick Fix for Headline:

The headline should now work after recompiling!


