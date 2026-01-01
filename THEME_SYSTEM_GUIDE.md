# Fluentory Theme System — Strict Implementation Guide (Inline-Only)

## 0) Non-Negotiables (Read Before Anything Else)

**NO new CSS files** (no theme.css, no "quick fix" stylesheet, no `<link>` additions).

**NO custom CSS classes** added just to theme something (ex: `.card-dark`, `.light-bg`, `.theme-text`).

**NO hardcoded hex colors** inside templates for backgrounds/text/borders (except shared accents, listed below).

**Tailwind is ONLY for layout/spacing/typography** (grid, flex, padding, margin, font-size, rounded, shadow, etc.)

**Theme colors must be applied only via inline styles using CSS variables:**
- `background-color`
- `color`
- `border-color`
- `fill/stroke` where applicable

**If any PR contains "new CSS" or "hardcoded bg/text colors", it is rejected.**

---

## 1) Architecture (How It Must Be Structured)

### A) One Theme Variables Source (Single Source of Truth)

Instead of duplicating the `<style>` theme variables in 6 base templates, do this:

1. **Create one partial** that contains the `<style>` block for theme variables.
2. **Include that partial** in all base templates.

✅ **Result**: You edit the palette once, and every role inherits it.

**Acceptance rule**: there should be exactly one copy of the theme variables in the project (in the partial).

**Implementation**:
- Create: `myApp/templates/partials/theme_variables.html`
- Include in: `base.html`, `student/base.html`, `teacher/base.html`, `dashboard/base.html`, `admin/base.html`, `partner/base.html`

### B) One Theme Toggle Script Source (Single Source of Truth)

Same idea:

1. The toggle logic must exist in **one place** (one inline `<script>` block in a partial)
2. Included in all base templates (or in a shared footer partial)

**Acceptance rule**: the toggle logic is not duplicated across templates.

**Implementation**:
- Move theme toggle logic to: `myApp/templates/partials/theme_script.html` OR keep in `static/js/theme.js` (already single source)
- Ensure it's included in all base templates

### C) Theme is Applied on the `<html>` Element

The system must set:
- `data-theme="dark"` OR `data-theme="light"`
- on the `<html>` element (not `<body>`, not random wrappers).

**Acceptance rule**: after toggle, you can inspect `<html>` and see the attribute change.

---

## 2) Theme Palette Rules (No Deviations)

### Variables to use (these are the only ones allowed)

- `--bg-primary`
- `--bg-secondary`
- `--bg-elevated`
- `--text-primary`
- `--text-secondary`
- `--text-tertiary`
- `--text-muted`
- `--border-primary`
- `--border-accent`
- `--accent-primary`
- `--accent-cta`

### Accent Colors

Accents are consistent in both modes. Dev can use either:
- variables (`--accent-primary`, `--accent-cta`) ✅ preferred
- or hardcoded ✅ allowed: `#82C293`, `#00655F`

**Everything else must be variable-based.**

---

## 3) How to Apply Theme Styles in Templates (Clear Rules)

### A) Replace ALL of these patterns:

- `bg-[#000000]`, `bg-[#04363A]`, `bg-[#254346]`
- `text-white`, `text-white/80`, `text-white/60`
- `border-white/10`, `border-white/20`
- any similar "dark-coded" colors

### B) With these mappings:

#### Page backgrounds
- main page wrapper → `style="background-color: var(--bg-primary);"`

#### Cards / surfaces
- panels, cards, sections → `style="background-color: var(--bg-secondary);"`

#### Elevated
- dropdowns, popovers, elevated containers → `style="background-color: var(--bg-elevated);"`

#### Text
- headings / main text → `style="color: var(--text-primary);"`
- descriptions → `style="color: var(--text-secondary);"`
- labels / subtle → `style="color: var(--text-tertiary);"`
- placeholder / muted → `style="color: var(--text-muted);"`

#### Borders
- standard borders → `style="border-color: var(--border-primary);"` or `style="border: 1px solid var(--border-primary);"`
- accent borders → `style="border-color: var(--border-accent);"` or `style="border: 1px solid var(--border-accent);"`

### C) Tailwind usage allowed:

✅ **Allowed**:
- layout: `flex`, `grid`, `gap`, `padding`, `margin`
- `rounded`, `shadow`, `width`, `height`
- text sizing: `text-lg`, `text-xl`, `font-bold`
- transitions/animations: `transition-all`, `duration-200`

❌ **NOT allowed**: 
- Tailwind `bg-*`, `text-*`, `border-*` when they define color (because that becomes static)

**Example**:
```html
<!-- ❌ WRONG -->
<div class="bg-[#04363A] text-white border border-white/10">

<!-- ✅ CORRECT -->
<div class="p-6 rounded-xl" style="background-color: var(--bg-secondary); color: var(--text-primary); border: 1px solid var(--border-primary);">
```

---

## 4) Toggle Button Requirements

### A) Must Exist on All Navbars

The toggle button must be included via the same partial in:
- public navbar (`partials/navbar.html`)
- student navbar (`student/partials/navbar.html`)
- teacher navbar (`teacher/partials/navbar.html`)
- admin/dashboard navbar (`dashboard/partials/navbar.html`, `admin/partials/navbar.html`)
- partner navbar (`partner/partials/navbar.html`)

### B) Must Have One Unique ID

There must be exactly one element with the toggle ID per page.

**Acceptance rule**: if the dev duplicates navbar or loads two nav partials, the toggle will break — fix that.

**Current implementation**: `id="theme-toggle"` in `partials/theme_toggle.html`

---

## 5) Why the Toggle "Is Not Working" (Most Common Causes)

Here's the no-excuses debugging list. Check in this order:

### Step 1 — Verify the script is running at all

Open browser console and confirm:
- no JS errors
- the theme script runs after page loads

If there's any JS error above it, the toggle won't bind.

### Step 2 — Confirm the button exists when the script binds

Most common issue: script runs before the navbar renders.

**Fix**: ensure the theme script is placed after the navbar markup (end of body is safest).

**Current implementation**: Script loads in `<head>` but uses DOM ready check — verify this works.

### Step 3 — Confirm the button ID matches

If script binds to `theme-toggle` but template uses `toggle-theme` (or vice versa), it fails silently.

**Rule**: one ID, same everywhere.

**Current ID**: `theme-toggle`

### Step 4 — Confirm localStorage key is consistent

You specified: `fluentory-theme`

Check:
- Are they saving to `theme` or `fluentory_theme` instead?
- If the key differs between save/load, it will never persist.

**Current key**: `fluentory-theme` ✅

### Step 5 — Confirm the attribute changes on `<html>`

Inspect element → `<html …>`
Click toggle.
You must see:
- `data-theme="light"` switching to `"dark"` and back.

If the attribute never changes, the JS is not binding or not executing.

### Step 6 — Confirm CSS selector matches the same attribute target

Your CSS uses:
- `:root { … }`
- `[data-theme="light"] { … }`

This works only if `data-theme="light"` is placed on the same element that matches that selector.

Since the script sets it on `<html>`, that's fine — but if the dev mistakenly sets it on `<body>`, and your selector targets a different element, it may not override as expected.

✅ **Rule**: set attribute on `<html>` and keep selector general as written.

### Step 7 — Confirm there are no duplicate variable blocks overriding each other

If each base template defines its own `<style>` variables, you can accidentally override light mode rules on some roles.

✅ **That's why we must move the variables to one shared partial.**

**Current status**: Variables are duplicated in 6 base templates — **NEEDS FIXING** (move to single partial)

---

## 6) Enforcement Plan (Because You Said They Don't Follow)

### A) PR Review Rules

**Reject PR if**:
- any new CSS file exists
- any new `<style>` block appears outside the theme partial
- any hardcoded hex backgrounds/text/borders are used (except accents)
- any Tailwind `bg-*` / `text-*` / `border-*` colors appear in updated templates

### B) "Search & Destroy" Audit

Run a sweep and fix all occurrences of:
- `bg-[#`
- `text-white`
- `border-white`
- `#000000`
- `#04363A`
- `#254346`

If those remain, the theme system is incomplete.

**Command to find violations**:
```bash
# Search for hardcoded dark colors
grep -r "bg-\[#" myApp/templates/
grep -r "text-white" myApp/templates/
grep -r "#000000\|#04363A\|#254346" myApp/templates/
```

---

## 7) Definition of Done (No Wiggle Room)

This task is **DONE** only when:

- ✅ Toggle exists on every role layout + public pages
- ✅ Clicking toggle changes `<html data-theme="...">` instantly
- ✅ Preference persists after refresh and across navigation
- ✅ No template relies on hardcoded dark colors
- ✅ No static CSS introduced
- ✅ All key pages verified in both modes:
  - landing, pricing, login/signup
  - student dashboard/course player/quiz/certs
  - teacher dashboard/course/lesson/quiz screens
  - admin/dashboard/partner screens
- ✅ No unreadable text in light mode anywhere
- ✅ **Theme variables exist in ONE partial only** (not duplicated)
- ✅ **Theme script exists in ONE place only** (not duplicated)

---

## 8) Implementation Order (How to Assign Work Without Chaos)

Give them the implementation order:

1. **Shared theme partial (variables)** → include in all base templates
   - Create: `partials/theme_variables.html`
   - Remove duplicate `<style>` blocks from all 6 base templates
   - Include partial in all base templates

2. **Shared theme script partial (toggle logic)** → include in all base templates
   - Verify: `static/js/theme.js` is single source (or move to partial if needed)
   - Ensure script loads in all base templates

3. **Confirm toggle works on**:
   - landing page + student dashboard (2 tests)
   - Verify `<html data-theme>` changes
   - Verify localStorage persistence

4. **Then apply theme to**:
   - shared partials (navbar/footer/announcement/components)
   - Order: `navbar.html` → `footer.html` → `announcement_bar.html` → other partials

5. **Then apply role pages**:
   - student → teacher → admin/dashboard → partner
   - Within each role: start with dashboard/home, then other pages

That prevents them from "fixing pages" while the system is broken.

---

## 9) Current Status & Required Changes

### ✅ Completed
- Theme toggle JavaScript (`static/js/theme.js`) - single source ✅
- Theme toggle button component (`partials/theme_toggle.html`) ✅
- Theme toggle added to all navbars ✅
- Hero partial (`partials/hero.html`) - example implementation ✅

### ⚠️ Needs Fixing (Critical)
- **Theme variables are duplicated** in 6 base templates → **Must create single partial**
- Most templates still use hardcoded colors → **Need systematic replacement**

### ⏳ Remaining Work
- Create `partials/theme_variables.html` and remove duplicates
- Apply theme to all remaining templates (~75+ files)
- Audit for hardcoded color violations

---

## 10) Color Mapping Reference

### Background Colors

| Variable | Dark Mode | Light Mode | Usage |
|----------|-----------|------------|-------|
| `--bg-primary` | `#000000` | `#F7FAF9` | Main page background |
| `--bg-secondary` | `#04363A` | `#FFFFFF` | Cards, surfaces, modals |
| `--bg-elevated` | `#254346` | `#EEF5F3` | Elevated containers, dropdowns |

### Text Colors

| Variable | Dark Mode | Light Mode | Usage |
|----------|-----------|------------|-------|
| `--text-primary` | `#FFFFFF` | `#0F2E2E` | Headings, primary text |
| `--text-secondary` | `rgba(255,255,255,0.7)` | `rgba(15,46,46,0.7)` | Secondary text, descriptions |
| `--text-tertiary` | `rgba(255,255,255,0.6)` | `rgba(15,46,46,0.6)` | Tertiary text, labels |
| `--text-muted` | `rgba(255,255,255,0.5)` | `rgba(15,46,46,0.5)` | Muted text, placeholders |

### Border Colors

| Variable | Dark Mode | Light Mode | Usage |
|----------|-----------|------------|-------|
| `--border-primary` | `rgba(255,255,255,0.1)` | `rgba(15,46,46,0.1)` | Default borders |
| `--border-accent` | `rgba(130,194,147,0.3)` | `rgba(130,194,147,0.3)` | Accent borders (same) |

### Accent Colors (Same in Both Modes)

| Variable | Value | Usage |
|----------|-------|-------|
| `--accent-primary` | `#82C293` | Primary accent, buttons, links |
| `--accent-cta` | `#00655F` | CTA buttons, hover states |

---

## 11) Complete Page & Partial List

### Public Pages (extends `base.html`)

#### Main Landing Page
- **Template**: `myApp/templates/landing.html`
- **View**: `home()` in `myApp/views.py` (line 78)
- **Partials Used**:
  - ✅ `partials/hero.html` (Theme applied - example)
  - ⏳ `partials/university_logos.html`
  - ⏳ `partials/how_it_works.html`
  - ⏳ `partials/featured_courses.html`
  - ⏳ `partials/ai_tutor.html`
  - ⏳ `partials/certificates.html`
  - ⏳ `partials/pricing.html`
  - ⏳ `partials/faq.html`
  - ⏳ `partials/final_cta.html`
- **Shared Partials**:
  - ✅ `partials/navbar.html` (Theme toggle added)
  - ⏳ `partials/footer.html`
  - ⏳ `partials/announcement_bar.html`
  - ⏳ `partials/role_preview_banner.html`
  - ⏳ `partials/social_proof.html`

#### Static Pages
- ⏳ **About**: `pages/about.html` → `about_page()` (line 115)
- ⏳ **Careers**: `pages/careers.html` → `careers_page()` (line 125)
- ⏳ **Blog**: `pages/blog.html` → `blog_page()` (line 135)
- ⏳ **Help Center**: `pages/help_center.html` → `help_center_page()` (line 145)
- ⏳ **Contact**: `pages/contact.html` → `contact_page()` (line 155)
- ⏳ **Privacy**: `pages/privacy.html` → `privacy_page()` (line 165)
- ⏳ **Terms**: `pages/terms.html` → `terms_page()` (line 175)
- ⏳ **Cookies**: `pages/cookies.html` → `cookies_page()` (line 185)

#### Authentication Pages
- ⏳ **Login**: `registration/login.html` → `login_view()` (line 195)
- ⏳ **Signup**: `auth/signup.html` → `signup_view()` (line 220)

---

### Student Pages (extends `student/base.html`)

- ⏳ **Dashboard**: `student/home.html` → `student_home()` (line 264)
- ⏳ **Courses List**: `student/courses.html` → `student_courses()` (line 375)
- ⏳ **Course Detail**: `student/course_detail.html` → `student_course_detail()` (line 444)
- ⏳ **Course Player**: `student/course_player.html` → `student_course_player()` (line 651)
- ⏳ **Learning**: `student/learning.html` → `student_learning()` (line 558)
- ⏳ **Placement Test**: `student/placement.html` → `student_placement()` (line 495)
- ⏳ **Certificates**: `student/certificates.html` → `student_certificates()` (line 608)
- ⏳ **Settings**: `student/settings.html` → `student_settings()` (line 621)

**Student Partials**:
- ✅ `student/partials/navbar.html` (Theme toggle added)
- ⏳ `student/partials/sidebar.html`
- ⏳ `student/partials/mobile_menu.html`

---

### Teacher Pages (extends `teacher/base.html`)

- ⏳ **Dashboard**: `teacher/dashboard.html` → `teacher_dashboard()` (line 1404)
- ⏳ **Courses**: `teacher/courses.html` → `teacher_courses()` (line 1522)
- ⏳ **Course Create**: `teacher/course_create.html` → `teacher_course_create()`
- ⏳ **Course Edit**: `teacher/course_edit.html` → `teacher_course_edit()`
- ⏳ **Course Students**: `teacher/course_students.html` → `teacher_course_students()`
- ⏳ **Course Live Classes**: `teacher/course_live_classes.html` → `teacher_course_live_classes()`
- ⏳ **Lessons**: `teacher/lessons.html` → `teacher_lessons()`
- ⏳ **Lesson Create**: `teacher/lesson_create.html` → `teacher_lesson_create()`
- ⏳ **Lesson Edit**: `teacher/lesson_edit.html` → `teacher_lesson_edit()`
- ⏳ **Quizzes**: `teacher/quizzes.html` → `teacher_quizzes()`
- ⏳ **Quiz Create**: `teacher/quiz_create.html` → `teacher_quiz_create()`
- ⏳ **Quiz Edit**: `teacher/quiz_edit.html` → `teacher_quiz_edit()`
- ⏳ **Quiz Questions**: `teacher/quiz_questions.html` → `teacher_quiz_questions()`
- ⏳ **My Students**: `teacher/my_students.html` → `teacher_my_students()`
- ⏳ **Schedule**: `teacher/schedule.html` → `teacher_schedule()`
- ⏳ **Schedule Calendar**: `teacher/schedule_calendar.html` → `teacher_schedule_calendar()`
- ⏳ **Availability**: `teacher/availability.html` → `teacher_availability()`
- ⏳ **Announcements**: `teacher/announcements.html` → `teacher_announcements()`
- ⏳ **AI Settings**: `teacher/ai_settings.html` → `teacher_ai_settings()`

**Teacher Partials**:
- ✅ `teacher/partials/navbar.html` (Theme toggle added)
- ⏳ `teacher/partials/sidebar.html`

---

### Admin/Dashboard Pages (extends `dashboard/base.html`)

- ⏳ **Overview**: `dashboard/overview.html` → `dashboard:overview` (in `dashboard_views.py`)
- ⏳ **Users**: `dashboard/users.html` → `dashboard:users`
- ⏳ **Courses**: `dashboard/courses.html` → `dashboard:courses`
- ⏳ **Analytics**: `dashboard/analytics.html` → `dashboard:analytics`
- ⏳ **Payments**: `dashboard/payments.html` → `dashboard:payments`
- ⏳ **Media**: `dashboard/media.html` → `dashboard:media`
- ⏳ **Media Add**: `dashboard/media_add.html` → `dashboard:media_add`
- ⏳ **Media Edit**: `dashboard/media_edit.html` → `dashboard:media_edit`
- ⏳ **Hero Section**: `dashboard/hero.html` → `dashboard:hero`
- ⏳ **Site Images**: `dashboard/site_images.html` → `dashboard:site_images`

**Dashboard Partials**:
- ✅ `dashboard/partials/navbar.html` (Theme toggle added)
- ⏳ `dashboard/partials/sidebar.html`

---

### Partner Pages (extends `partner/base.html`)

- ⏳ **Overview**: `partner/overview.html` → `partner_overview()` (line 2294)
- ⏳ **Cohorts**: `partner/cohorts.html` → `partner_cohorts()` (line 2385)
- ⏳ **Programs**: `partner/programs.html` → `partner_programs()` (line 2428)
- ⏳ **Referrals**: `partner/referrals.html` → `partner_referrals()` (line 2480)
- ⏳ **Marketing**: `partner/marketing.html` → `partner_marketing()` (line 2530)
- ⏳ **Reports**: `partner/reports.html` → `partner_reports()` (line 2580)
- ⏳ **Settings**: `partner/settings.html` → `partner_settings()` (line 2630)

**Partner Partials**:
- ✅ `partner/partials/navbar.html` (Theme toggle added)
- ⏳ `partner/partials/sidebar.html`

---

### Admin Pages (extends `admin/base.html`)

- ⏳ **Overview**: `admin/overview.html` → `admin_overview()` (line 1095)
- ⏳ **Users**: `admin/users.html` → `admin_users()` (line 1120)
- ⏳ **Courses**: `admin/courses.html` → `admin_courses()` (line 1147)
- ⏳ **Payments**: `admin/payments.html` → `admin_payments()` (line 1163)
- ⏳ **Media**: `admin/media.html` → `admin_media()` (line 1183)
- ⏳ **Media Add**: `admin/media_add.html` → `admin_media_add()` (line 1225)
- ⏳ **Media Edit**: `admin/media_edit.html` → `admin_media_edit()` (line 1303)
- ⏳ **Site Images**: `admin/site_images.html` → `admin_site_images()` (line 1360)

**Admin Partials**:
- ✅ `admin/partials/navbar.html` (Theme toggle added)
- ⏳ `admin/partials/sidebar.html`

---

### Other Templates

- ⏳ **Verify Certificate**: `verify_certificate.html` → `verify_certificate()` (line 1034)
- ⏳ **Student Quiz**: `student/quiz.html` → `student_quiz()` (line 998)
- ⏳ **Student Quiz Result**: `student/quiz_result.html` → `student_quiz_result()` (line 1010)
- ⏳ **Student Bookings**: `student/bookings.html` → `student_bookings()` (line 750)

---

## 12) Quick Reference: Example Code Patterns

### Correct Pattern (✅)

```html
<!-- Card with theme-aware colors -->
<div class="p-6 rounded-xl shadow-lg" 
     style="background-color: var(--bg-secondary); color: var(--text-primary); border: 1px solid var(--border-primary);">
    <h2 style="color: var(--text-primary);">Title</h2>
    <p style="color: var(--text-secondary);">Description text</p>
    <button style="background-color: var(--accent-primary); color: white;">
        Click Me
    </button>
</div>
```

### Wrong Pattern (❌)

```html
<!-- Using hardcoded colors -->
<div class="bg-[#04363A] text-white border border-white/10 p-6 rounded-xl">
    <h2 class="text-white">Title</h2>
    <p class="text-white/80">Description</p>
</div>
```

### Combining Tailwind Layout + Inline Theme Colors (✅)

```html
<div class="flex items-center gap-4 p-6 rounded-xl transition-all duration-200 hover:shadow-xl"
     style="background-color: var(--bg-elevated); color: var(--text-primary);">
    <span style="color: var(--text-secondary);">Label</span>
    <span style="color: var(--text-primary);">Value</span>
</div>
```

---

## 13) Summary

**Theme System Architecture**:
1. **One CSS Variables Partial** (single source of truth)
2. **One Theme Script** (single source of truth)
3. **Inline Styles Only** (using CSS variables)
4. **Tailwind for Layout** (not for colors)

**Key Principles**: 
- ✅ **No custom CSS files**
- ✅ **No custom CSS classes for theming**
- ✅ **No hardcoded colors** (except accents)
- ✅ **Inline styles with CSS variables only**
- ✅ **Tailwind for layout/spacing/typography only**

**Enforcement**:
- Reject PRs with CSS files or hardcoded colors
- Run audit sweep for violations
- Verify single source of truth for variables and script

**Definition of Done**:
- Toggle works on all pages
- Preference persists
- No hardcoded colors
- No static CSS
- All pages verified in both modes
- No unreadable text
