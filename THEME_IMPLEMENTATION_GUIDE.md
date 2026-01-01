# Theme System Implementation Guide

## Overview

This document outlines the light/dark mode theme system implementation for Fluentory. The system uses CSS variables and a global theme state that persists across page navigation.

## Core Files

### 1. `static/css/theme.css`
Defines CSS variables for all theme colors:
- `--bg-primary`: Primary background
- `--bg-secondary`: Cards/surfaces
- `--bg-elevated`: Elevated containers
- `--text-primary`: Primary text
- `--text-secondary`: Secondary text (70% opacity)
- `--text-tertiary`: Tertiary text (60% opacity)
- `--text-muted`: Muted text (50% opacity)
- `--border-primary`: Primary borders
- `--border-accent`: Accent borders
- `--accent-primary`: Primary accent (#82C293)
- `--accent-cta`: CTA accent (#00655F)

### 2. `static/js/theme.js`
Manages theme state:
- Defaults to dark mode
- Respects system preference if no user preference is set
- Persists user preference in localStorage
- Applies theme via `data-theme` attribute on `<html>`
- Exports `window.FluentoryTheme` API for programmatic control

### 3. `myApp/templates/partials/theme_toggle.html`
Reusable theme toggle button component.

## Color Mapping

### Dark Mode (Default)
- Primary background: `#000000`
- Cards/surfaces: `#04363A`
- Elevated containers: `#254346`
- Text: `#FFFFFF` (with opacity variants)
- Accents: `#82C293`, `#00655F` (shared)

### Light Mode
- Primary background: `#F7FAF9`
- Cards/surfaces: `#FFFFFF`
- Elevated containers: `#EEF5F3`
- Text: `#0F2E2E` (with opacity variants)
- Accents: `#82C293`, `#00655F` (shared - same as dark)

## Implementation Pattern

### Base Templates

All base templates should:

1. Load theme CSS and JS:
```django
{% load static %}
<link rel="stylesheet" href="{% static 'css/theme.css' %}">
<script src="{% static 'js/theme.js' %}" defer></script>
```

2. Use CSS variables for body:
```html
<body style="background-color: var(--bg-primary); color: var(--text-primary);">
```

### Replacing Hardcoded Colors

#### Background Colors

**Before:**
```html
<div class="bg-[#000000]">
<div class="bg-[#04363a]">
<div class="bg-[#254346]">
```

**After:**
```html
<div style="background-color: var(--bg-primary);">
<div style="background-color: var(--bg-secondary);">
<div style="background-color: var(--bg-elevated);">
```

#### Text Colors

**Before:**
```html
<p class="text-white">
<p class="text-white/90">
<p class="text-white/60">
```

**After:**
```html
<p style="color: var(--text-primary);">
<p style="color: var(--text-secondary);">
<p style="color: var(--text-tertiary);">
```

#### Borders

**Before:**
```html
<div class="border border-white/10">
```

**After:**
```html
<div style="border-color: var(--border-primary);" class="border">
```

#### Accent Colors (Same in Both Modes)

Accent colors (`#82C293`, `#00655F`) remain the same and can stay as-is:
```html
<div class="bg-[#82C293]">
<span class="text-[#00655F]">
```

Or use CSS variables for consistency:
```html
<div style="background-color: var(--accent-primary);">
<span style="color: var(--accent-cta);">
```

### Opacity Variants

For opacity variants, use CSS variables with rgba:
```css
/* Instead of: */
background-color: rgba(255, 255, 255, 0.1);

/* Use: */
background-color: color-mix(in srgb, var(--text-primary) 10%, transparent);
```

Or create utility classes in `theme.css`:
```css
.bg-overlay-10 {
    background-color: rgba(255, 255, 255, 0.1); /* Dark mode */
}
[data-theme="light"] .bg-overlay-10 {
    background-color: rgba(15, 46, 46, 0.1); /* Light mode */
}
```

## Components Checklist

All components should be checked in both modes:

### Pages
- [ ] Landing page
- [ ] Courses listing
- [ ] Course detail pages
- [ ] Pricing
- [ ] Login / Register
- [ ] Placement test
- [ ] Student dashboard
- [ ] Teacher dashboard
- [ ] Admin dashboard
- [ ] Partner dashboard
- [ ] Course player
- [ ] Quizzes
- [ ] Certificates

### Components
- [ ] Navbars
- [ ] Sidebars
- [ ] Cards
- [ ] Buttons
- [ ] Badges
- [ ] Inputs
- [ ] Dropdowns
- [ ] Tables
- [ ] Alerts
- [ ] Modals
- [ ] Notifications
- [ ] Empty states

## Current Status

### Completed ✅
- Theme CSS variables system
- Theme JS with localStorage persistence
- Theme toggle component
- Base templates updated (base.html, student/base.html, teacher/base.html, dashboard/base.html, admin/base.html, partner/base.html)
- Theme toggle added to all navbars

### In Progress 🚧
- Replacing hardcoded colors in templates (systematic update needed)

### Remaining 📋
- Update all template files to use CSS variables
- Test all pages in both modes
- Verify consistency across components

## Notes

- Default theme is dark mode
- System preference is respected if no user preference is set
- User preference persists across sessions
- Theme switch is instant (no page reload)
- Accent colors do not change between modes
- All transitions are smooth (200ms)

