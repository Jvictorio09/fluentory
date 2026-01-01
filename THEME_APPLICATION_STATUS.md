# Theme System Application Status

## Overview
This document tracks the progress of applying the theme system (light/dark mode with CSS variables) across all templates.

## ✅ Completed Files

### Base Templates (6/6 - COMPLETE)
- ✅ `myApp/templates/base.html`
- ✅ `myApp/templates/student/base.html`
- ✅ `myApp/templates/teacher/base.html`
- ✅ `myApp/templates/dashboard/base.html`
- ✅ `myApp/templates/admin/base.html`
- ✅ `myApp/templates/partner/base.html`

**Status**: All base templates include `theme_variables.html` and have theme system initialized.

### Shared Partials
- ✅ `myApp/templates/partials/theme_variables.html` - Single source of truth for CSS variables
- ✅ `myApp/templates/partials/theme_toggle.html` - Theme toggle button component
- ✅ `myApp/templates/partials/navbar.html` - Navigation bar (fully theme-aware)
- ✅ `myApp/templates/partials/announcement_bar.html` - Announcement bar
- ✅ `myApp/templates/partials/footer.html` - Footer (mostly complete, may need review)

### Landing Page Partials (6/9 - IN PROGRESS)
- ✅ `myApp/templates/partials/hero.html` - Hero section (fully theme-aware with hero-specific variables)
- ✅ `myApp/templates/partials/university_logos.html` - University logos/outcomes section
- ✅ `myApp/templates/partials/how_it_works.html` - How it works section
- ✅ `myApp/templates/partials/final_cta.html` - Final CTA section
- ✅ `myApp/templates/partials/ai_tutor.html` - AI Tutor section
- ✅ `myApp/templates/partials/certificates.html` - **COMPLETED** ✅
- ⏳ `myApp/templates/partials/pricing.html` - **~38 text-white + 16 bg-color instances remaining** (section background done)
- ⏳ `myApp/templates/partials/faq.html` - **~47 text-white + 36 bg-color instances remaining** (section background done)
- ⏳ `myApp/templates/partials/featured_courses.html` - **~33 text-white + 27 bg-color instances remaining** (section background done)

## 🔄 Remaining Work

### Landing Page (Priority 1)
**4 files remaining with ~193 color instances total**

#### certificates.html (29 instances)
- Section background: `bg-[#000000]`
- Headlines: `text-white`
- Cards: `bg-[#04363a]`, `bg-[#254346]`
- Borders: `border-white/10`
- Text variants: `text-white/70`, `text-white/60`

**Key sections to update:**
- Main section tag
- Eyebrow label
- Headlines and descriptions
- Verification card
- Certificate preview card
- Trust bullets

#### pricing.html (54 instances)
- Section background
- Pricing cards (3 cards)
- Currency selector buttons
- All text colors
- Borders and backgrounds
- Shadows (keep as-is, just update colors)

#### faq.html (59 instances)
- Section background
- FAQ accordion items (5 items)
- Preview card
- All interactive elements
- Text colors throughout

#### featured_courses.html (51 instances)
- Section background
- Filter buttons (6 buttons)
- Course cards (5 cards)
- All text, backgrounds, borders

### Student Pages (Priority 2)
- ⏳ Student dashboard
- ⏳ Student courses
- ⏳ Student profile
- ⏳ Course player
- ⏳ Quizzes
- ⏳ Certificates page

### Teacher Pages (Priority 3)
- ⏳ Teacher dashboard
- ⏳ Teacher courses
- ⏳ Teacher analytics
- ⏳ Student management

### Admin/Dashboard Pages (Priority 4)
- ⏳ Admin dashboard
- ⏳ User management
- ⏳ Course management
- ⏳ Analytics

### Partner Pages (Priority 5)
- ⏳ Partner overview
- ⏳ Partner programs
- ⏳ Partner referrals
- ⏳ Partner marketing
- ⏳ Partner reports
- ⏳ Partner settings

### Authentication Pages (Priority 6)
- ⏳ Login page
- ⏳ Register page
- ⏳ Password reset

### Static Pages (Priority 7)
- ⏳ About page
- ⏳ Contact page
- ⏳ Help center
- ⏳ Privacy policy
- ⏳ Terms of service
- ⏳ Cookies policy

## Replacement Patterns

### Common Replacements Needed

```html
<!-- Section backgrounds -->
bg-[#000000] → style="background-color: var(--bg-primary);"

<!-- Text colors -->
text-white → style="color: var(--text-primary);"
text-white/70 → style="color: var(--text-secondary);"
text-white/60 → style="color: var(--text-tertiary);"
text-white/85 → style="color: var(--text-secondary);"
text-white/80 → style="color: var(--text-secondary);"

<!-- Background colors -->
bg-[#04363a] → style="background-color: var(--bg-secondary);"
bg-[#04363A] → style="background-color: var(--bg-secondary);"
bg-[#254346] → style="background-color: var(--bg-elevated);"
bg-[#04363a]/70 → style="background-color: rgba(4,54,58,0.7);" (or use var(--bg-secondary) with opacity)

<!-- Borders -->
border-white/10 → style="border-color: var(--border-primary);"
border-white/20 → style="border-color: var(--border-primary);"
border-white/30 → style="border-color: var(--border-primary);"

<!-- Keep as-is (brand colors) -->
#82C293 → var(--accent-primary) or keep hardcoded
#00655F → var(--accent-cta) or keep hardcoded
#b8c943 → keep hardcoded (special accent)
```

### Complex Patterns

For elements with multiple classes:
```html
<!-- Before -->
<div class="rounded-xl bg-[#04363a] text-white border border-white/10">

<!-- After -->
<div class="rounded-xl border" style="background-color: var(--bg-secondary); color: var(--text-primary); border-color: var(--border-primary);">
```

For elements with existing inline styles:
```html
<!-- Before -->
<div class="bg-[#254346]" style="padding: 20px;">

<!-- After -->
<div style="background-color: var(--bg-elevated); padding: 20px;">
```

## Helper Script

A Python script `apply_theme_replacements.py` has been created to automate basic replacements. However, due to the complexity of HTML structure and the need to preserve existing attributes, **manual review is recommended** for:

1. Elements with existing inline styles (need to merge)
2. Complex Tailwind class combinations
3. Elements where class order matters
4. Conditional logic or Django template tags

## Next Steps

1. **Immediate**: Complete the 4 remaining landing page partials
2. **Short-term**: Apply theme to student and teacher pages
3. **Medium-term**: Apply theme to admin/dashboard and partner pages
4. **Long-term**: Apply theme to authentication and static pages

## Testing Checklist

For each updated file:
- [ ] Dark mode displays correctly
- [ ] Light mode displays correctly
- [ ] Theme toggle works
- [ ] No visual glitches
- [ ] Text is readable in both modes
- [ ] Accent colors remain consistent
- [ ] No hardcoded hex values for backgrounds/text/borders (except accents)

## Notes

- **Brand colors** (#82C293, #00655F) should remain consistent across themes
- **Gradients** can use hardcoded accent colors or CSS variables
- **Shadows** can remain as-is (they're not theme-specific)
- **Opacity modifiers** (like /70, /10) need to be converted to rgba() or kept with CSS variable + opacity

