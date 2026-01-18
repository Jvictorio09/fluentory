# Lesson Editor System - Complete Documentation

## Overview
This document explains the current implementation of the lesson editor system for courses, modules, and lessons in the admin dashboard.

---

## Database Structure

### Models Hierarchy
```
Course
  └── Module (one-to-many)
        └── Lesson (one-to-many)
```

### Lesson Model Fields (Relevant to Editor)
```python
class Lesson(models.Model):
    # Basic Info
    module = ForeignKey(Module)
    title = CharField(max_length=200)
    description = TextField(blank=True)
    content_type = CharField(choices=[
        ('video', 'Video'),
        ('text', 'Text/Article'),
        ('quiz', 'Quiz'),
        ('assignment', 'Assignment'),
        ('interactive', 'Interactive'),
    ])
    
    # Content Fields
    video_url = URLField(blank=True)           # For video lessons
    video_duration = PositiveIntegerField()    # In seconds
    text_content = TextField(blank=True)       # Legacy HTML/rich text
    content = JSONField(default=dict)          # Editor.js JSON format
    
    # Settings
    order = PositiveIntegerField(default=0)
    estimated_minutes = PositiveIntegerField(default=10)
    is_preview = BooleanField(default=False)
    is_milestone = BooleanField(default=False)
```

### Content Field Structure

The `content` JSONField stores lesson content in two possible formats:

#### Format 1: Section-Based (Current Target)
```json
{
  "sections": [
    {
      "id": "section-1234567890",
      "title": "Introduction",
      "order": 0,
      "content": {
        "blocks": [
          {
            "type": "header",
            "data": {
              "text": "Welcome",
              "level": 1
            }
          },
          {
            "type": "paragraph",
            "data": {
              "text": "This is the introduction..."
            }
          }
        ]
      }
    },
    {
      "id": "section-1234567891",
      "title": "Main Content",
      "order": 1,
      "content": {
        "blocks": [...]
      }
    }
  ]
}
```

#### Format 2: Legacy Single Editor (Old Format)
```json
{
  "blocks": [
    {
      "type": "header",
      "data": { "text": "Title", "level": 1 }
    },
    {
      "type": "paragraph",
      "data": { "text": "Content..." }
    }
  ]
}
```

---

## Current Implementation Analysis

### ⚠️ CRITICAL ISSUE: Dual Editor Implementation

The codebase currently has **TWO conflicting editor implementations**:

#### 1. Single Editor (OLD - Lines 480-525)
- **HTML Container**: `#editorHost` (line 495)
- **JavaScript Instance**: `editorInstance` (line 626)
- **Initialization**: `initializeEditor()` function (line 989)
- **Location**: Inside `#lesson-text-fields` div
- **Status**: ❌ **NOT USED** - This is legacy code that should be removed

#### 2. Section-Based Editor (NEW - Lines 1363-1867)
- **HTML Container**: `#lesson-sections` (should exist but doesn't in HTML!)
- **JavaScript Instances**: `sectionEditors` object (line 1365)
- **Initialization**: `initializeSectionEditor()` function (line 1561)
- **Location**: Should be inside `#lesson-text-fields` div
- **Status**: ⚠️ **PARTIALLY IMPLEMENTED** - JavaScript exists but HTML container is missing

### The Problem

1. **HTML Structure Issue**: 
   - The HTML shows `#editorHost` (single editor) at line 495
   - But JavaScript functions expect `#lesson-sections` container (line 1368)
   - **Result**: Section-based editor cannot render because container doesn't exist

2. **Content Type Toggle Issue**:
   - `toggleLessonFields()` function (line 935) shows/hides `#lesson-text-fields`
   - But it doesn't initialize sections or show the section container
   - When switching to 'text' content type, it tries to initialize single editor instead

3. **Data Loading Issue**:
   - `loadLessonSections()` function (line 1847) exists to load section data
   - But it's never called when editing an existing lesson
   - `openLessonModal()` (line 820) loads lesson data but doesn't call `loadLessonSections()`

---

## How It Should Work (Intended Flow)

### 1. Creating a New Lesson

```
User clicks "Add Lesson" button
  ↓
openLessonModal(moduleId) called
  ↓
Modal opens with default content_type = 'text'
  ↓
toggleLessonFields('text') called
  ↓
#lesson-text-fields shown
  ↓
#lesson-sections container should be visible (BUT IT'S MISSING!)
  ↓
User clicks "Add Section" button
  ↓
addLessonSection() creates section HTML
  ↓
initializeSectionEditor() creates Editor.js instance for section
  ↓
User adds blocks via "Add Block" dropdown
  ↓
Content saved to lessonSections array
  ↓
Form submit → updateLessonContent() → saves to #lesson-content hidden field
  ↓
Backend receives: { sections: [...] }
```

### 2. Editing an Existing Lesson

```
User clicks "Edit Lesson" button
  ↓
openLessonModal(moduleId, lessonId) called
  ↓
Fetch lesson data from API
  ↓
Populate form fields
  ↓
If content_type === 'text':
  ↓
  Parse content JSON
  ↓
  Call loadLessonSections(content) (BUT THIS IS NEVER CALLED!)
  ↓
  Render sections with existing content
  ↓
Else if content_type === 'video':
  ↓
  Show video fields
```

---

## Current JavaScript Functions

### Section Management Functions

| Function | Purpose | Status |
|----------|---------|--------|
| `addLessonSection()` | Creates a new section with Editor.js | ✅ Implemented |
| `removeSection()` | Removes a section | ✅ Implemented |
| `moveSection()` | Reorders sections | ✅ Implemented |
| `updateSectionTitle()` | Updates section title | ✅ Implemented |
| `initializeSectionEditor()` | Creates Editor.js for a section | ✅ Implemented |
| `addBlockToSection()` | Adds block via dropdown | ✅ Implemented |
| `toggleBlockMenu()` | Shows/hides block dropdown | ✅ Implemented |
| `loadLessonSections()` | Loads sections from JSON | ✅ Implemented but **NEVER CALLED** |
| `updateLessonContent()` | Saves sections to hidden field | ✅ Implemented |

### Single Editor Functions (Legacy - Should Be Removed)

| Function | Purpose | Status |
|----------|---------|--------|
| `initializeEditor()` | Creates single Editor.js instance | ❌ Legacy - conflicts with sections |
| `focusEditor()` | Focuses single editor | ❌ Legacy |
| `handleDrop()` | Drag-drop for single editor | ❌ Legacy |

---

## What Needs to Be Fixed

### 1. HTML Structure Fix (HIGH PRIORITY)

**Current HTML (Line 481-525):**
```html
<div id="lesson-text-fields" class="hidden">
    <div id="editorHost">...</div>  <!-- ❌ WRONG - Single editor -->
    <input type="hidden" id="lesson-content" name="content" value="{}">
</div>
```

**Should Be:**
```html
<div id="lesson-text-fields" class="hidden">
    <div class="space-y-4">
        <div class="flex items-center justify-between mb-4">
            <h4>Lesson Content</h4>
            <button onclick="addLessonSection()">Add Section</button>
        </div>
        <div id="lesson-sections" class="space-y-4">
            <!-- Sections will be added here dynamically -->
        </div>
        <input type="hidden" id="lesson-content" name="content" value='{"sections":[]}'>
    </div>
</div>
```

### 2. Data Loading Fix (HIGH PRIORITY)

**In `openLessonModal()` function (line 820):**

**Current:**
```javascript
if (lessonId) {
    // ... load lesson data ...
    const contentData = lesson.content || {};
    initializeEditor(contentData);  // ❌ WRONG - Uses single editor
}
```

**Should Be:**
```javascript
if (lessonId) {
    // ... load lesson data ...
    const contentData = lesson.content || {};
    if (lesson.content_type === 'text') {
        loadLessonSections(contentData);  // ✅ Load sections
    }
}
```

### 3. Content Type Toggle Fix (MEDIUM PRIORITY)

**In `toggleLessonFields()` function (line 935):**

**Current:**
```javascript
else if (contentType === 'text') {
    videoFields.classList.add('hidden');
    textFields.classList.remove('hidden');
    setTimeout(() => {
        initializeEditor(parsed);  // ❌ WRONG - Uses single editor
    }, 200);
}
```

**Should Be:**
```javascript
else if (contentType === 'text') {
    videoFields.classList.add('hidden');
    textFields.classList.remove('hidden');
    // If no sections exist, create one default section
    if (lessonSections.length === 0) {
        addLessonSection();
    }
}
```

### 4. Remove Legacy Code (LOW PRIORITY)

Remove these functions and HTML:
- `initializeEditor()` function
- `focusEditor()` function  
- `handleDrop()`, `handleDragOver()`, `handleDragLeave()` (for single editor)
- `#editorHost` div
- `editorInstance` variable (or keep only for backward compatibility)

---

## Block Types Available

The "Add Block" dropdown supports these Editor.js block types:

| Block Type | Editor.js Tool | Description |
|------------|----------------|-------------|
| Heading 1 | `header` (level 1) | Large heading |
| Heading 2 | `header` (level 2) | Medium heading |
| Heading 3 | `header` (level 3) | Small heading |
| Paragraph | `paragraph` | Text content |
| Link | `paragraph` (with HTML link) | Hyperlink |
| Bullet List | `list` | Unordered list |
| Quote | `quote` | Highlighted quote |
| Image | `image` | Upload/paste image |
| Code Block | `code` | Code snippet |

---

## API Endpoints Used

### Lesson Management
- `GET /en/dashboard/api/lessons/{id}/update/` - Get lesson data
- `POST /en/dashboard/api/lessons/{id}/update/` - Update lesson
- `POST /en/dashboard/api/modules/{id}/lessons/create/` - Create lesson
- `POST /en/dashboard/api/lessons/{id}/delete/` - Delete lesson

### Image Upload
- `POST /en/dashboard/api/editor-image/` - Upload image for Editor.js

**Request:**
```javascript
FormData {
    file: File
}
```

**Response:**
```json
{
    "success": true,
    "url": "https://cloudinary.com/image.jpg"
}
```

---

## Data Flow Diagram

```
┌─────────────────┐
│  User Action    │
│  "Add Lesson"   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ openLessonModal │
│ (moduleId)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ toggleLesson    │
│ Fields('text')  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────────┐
│ #lesson-text-   │      │ #lesson-sections │
│ fields shown    │─────▶│ (MISSING!)       │
└────────┬────────┘      └──────────────────┘
         │
         ▼
┌─────────────────┐
│ User clicks     │
│ "Add Section"    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ addLessonSection│
│ ()              │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ initializeSection│
│ Editor(sectionId)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ User adds blocks│
│ via dropdown    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ updateLesson    │
│ Content()       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Form Submit     │
│ → Backend       │
└─────────────────┘
```

---

## Testing Checklist

### ✅ What Works
- [x] Module creation/editing
- [x] Lesson modal opens/closes
- [x] Content type dropdown works
- [x] Video fields show/hide correctly
- [x] Section JavaScript functions exist
- [x] Block dropdown menu works
- [x] Image upload endpoint exists

### ❌ What Doesn't Work
- [ ] Section-based editor doesn't render (missing HTML container)
- [ ] Existing lesson content doesn't load into sections
- [ ] New lessons don't create sections automatically
- [ ] Single editor code conflicts with section editor

---

## Recommended Fix Priority

1. **IMMEDIATE**: Fix HTML structure - replace `#editorHost` with `#lesson-sections` container
2. **IMMEDIATE**: Fix data loading - call `loadLessonSections()` when editing lessons
3. **HIGH**: Fix content type toggle - initialize sections instead of single editor
4. **MEDIUM**: Remove legacy single editor code
5. **LOW**: Add default section creation when switching to 'text' type

---

## Summary

The section-based editor system is **90% implemented** in JavaScript but **cannot function** because:

1. The HTML container (`#lesson-sections`) doesn't exist in the template
2. The data loading function (`loadLessonSections()`) is never called
3. Legacy single editor code conflicts and is still being used

**The fix requires:**
- Updating the HTML template to include the section container
- Updating `openLessonModal()` to load sections
- Updating `toggleLessonFields()` to initialize sections
- Removing or deprecating the single editor code

Once these fixes are applied, the section-based editor will work as intended.

