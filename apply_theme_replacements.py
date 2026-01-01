#!/usr/bin/env python3
"""
Helper script to automate theme system replacements in HTML templates.
Converts hardcoded colors to CSS variables for theme support.

Usage: python apply_theme_replacements.py
"""

import re
import os
from pathlib import Path

# Files to process
FILES_TO_UPDATE = [
    'myApp/templates/partials/certificates.html',
    'myApp/templates/partials/pricing.html',
    'myApp/templates/partials/faq.html',
    'myApp/templates/partials/featured_courses.html',
]

def remove_class_from_string(classes_str, class_to_remove):
    """Remove a specific class from a class string"""
    classes = classes_str.split()
    classes = [c for c in classes if c != class_to_remove]
    return ' '.join(classes) if classes else ''

def add_or_merge_style(style_str, new_property, new_value):
    """Add or merge a style property into an existing style string"""
    if not style_str or style_str.strip() == '':
        return f"{new_property}: {new_value};"
    
    # Parse existing styles
    styles = {}
    for prop in style_str.split(';'):
        prop = prop.strip()
        if ':' in prop:
            key, value = prop.split(':', 1)
            styles[key.strip()] = value.strip()
    
    # Add/update the property
    styles[new_property] = new_value
    
    # Rebuild style string
    return '; '.join([f"{k}: {v}" for k, v in styles.items()]) + (';' if styles else '')

def process_section_tags(content):
    """Process <section> tags with bg-[#000000]"""
    def replace_section(match):
        tag_start = match.group(1)  # <section ... class="
        classes = match.group(2)     # class content
        rest = match.group(3)        # " ...>
        
        # Remove bg-[#000000] from classes
        new_classes = remove_class_from_string(classes, 'bg-[#000000]')
        
        # Check if style attribute already exists
        style_match = re.search(r'style="([^"]*)"', match.group(0))
        if style_match:
            existing_style = style_match.group(1)
            new_style = add_or_merge_style(existing_style, 'background-color', 'var(--bg-primary)')
            # Replace existing style
            return re.sub(r'style="[^"]*"', f'style="{new_style}"', match.group(0)).replace(f' {classes} ', f' {new_classes} ' if new_classes else ' ').replace(f'bg-[#000000]', '')
        else:
            # Add style attribute
            return f'{tag_start}{new_classes}{rest}" style="background-color: var(--bg-primary);">'
    
    # Pattern for <section class="... bg-[#000000] ...">
    content = re.sub(
        r'(<section[^>]*class=")([^"]*)\s+bg-\[#000000\]([^"]*")',
        replace_section,
        content
    )
    
    return content

def process_text_white(content):
    """Process text-white classes"""
    # Pattern: class="... text-white ..." or class="... text-white"
    def replace_text_white(match):
        tag_start = match.group(1)  # <tag ... class="
        classes = match.group(2)     # class content
        rest = match.group(3)        # " ...>
        
        # Remove text-white variants from classes
        classes_to_remove = ['text-white', 'text-white/70', 'text-white/60', 'text-white/85', 'text-white/80', 'text-white/50']
        new_classes = classes
        for cls in classes_to_remove:
            new_classes = remove_class_from_string(new_classes, cls)
        
        # Determine CSS variable based on which text-white was present
        css_var = 'var(--text-primary)'  # default
        if 'text-white/70' in classes or 'text-white/85' in classes or 'text-white/80' in classes:
            css_var = 'var(--text-secondary)'
        elif 'text-white/60' in classes:
            css_var = 'var(--text-tertiary)'
        elif 'text-white/50' in classes:
            css_var = 'var(--text-muted)'
        
        # Check if style attribute already exists
        full_tag = match.group(0)
        style_match = re.search(r'style="([^"]*)"', full_tag)
        if style_match:
            existing_style = style_match.group(1)
            new_style = add_or_merge_style(existing_style, 'color', css_var)
            # Replace in full tag
            result = re.sub(r'style="[^"]*"', f'style="{new_style}"', full_tag)
            result = result.replace(classes, new_classes)
            for cls in classes_to_remove:
                result = result.replace(cls, '')
            return result
        else:
            # Add style attribute
            return f'{tag_start}{new_classes}{rest}" style="color: {css_var};">'
    
    # Match text-white variants in class attributes
    patterns = [
        (r'(<[^>]*class="[^"]*)\s+text-white/70([^"]*")', 'var(--text-secondary)'),
        (r'(<[^>]*class="[^"]*)\s+text-white/60([^"]*")', 'var(--text-tertiary)'),
        (r'(<[^>]*class="[^"]*)\s+text-white/85([^"]*")', 'var(--text-secondary)'),
        (r'(<[^>]*class="[^"]*)\s+text-white/80([^"]*")', 'var(--text-secondary)'),
        (r'(<[^>]*class="[^"]*)\s+text-white/50([^"]*")', 'var(--text-muted)'),
        (r'(<[^>]*class="[^"]*)\s+text-white([^"]*")', 'var(--text-primary)'),
    ]
    
    for pattern, css_var in patterns:
        content = re.sub(pattern, lambda m: replace_text_white_class(m, css_var), content)
    
    return content

def replace_text_white_class(match, css_var):
    """Helper to replace text-white classes"""
    full_match = match.group(0)
    # Simple replacement: remove text-white variant and add style
    if 'style=' in full_match:
        # Merge with existing style
        return re.sub(r'style="([^"]*)"', lambda m: f'style="{add_or_merge_style(m.group(1), "color", css_var)}"', 
                     re.sub(r'\s+text-white[^"]*', '', full_match))
    else:
        # Add style attribute
        return re.sub(r'(")\s*([>])', f'" style="color: {css_var};">', 
                     re.sub(r'\s+text-white[^"]*', '', full_match))

def process_bg_colors(content):
    """Process background color classes"""
    # This is complex - for bg-[#04363a]/70 we need special handling
    # For now, simpler approach: replace standalone bg-[#04363a] patterns
    
    replacements = [
        (r'bg-\[#04363a\]/90', 'rgba(4,54,58,0.9)'),
        (r'bg-\[#04363a\]/70', 'rgba(4,54,58,0.7)'),
        (r'bg-\[#04363a\]/50', 'rgba(4,54,58,0.5)'),
        (r'bg-\[#04363A\]/90', 'rgba(4,54,58,0.9)'),
        (r'bg-\[#04363A\]/70', 'rgba(4,54,58,0.7)'),
        (r'bg-\[#254346\]/70', 'rgba(37,67,70,0.7)'),
    ]
    
    # Note: These need to be converted to inline styles, which is complex
    # This is a placeholder - manual work may be needed
    
    return content

def process_file(file_path):
    """Process a single file with theme replacements"""
    print(f"\nProcessing: {file_path}")
    
    if not os.path.exists(file_path):
        print(f"  ❌ ERROR: File not found")
        return False
    
    # Read file
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    changes_made = []
    
    # Apply transformations (simplified for now)
    # 1. Section backgrounds (most reliable)
    new_content = process_section_tags(content)
    if new_content != content:
        changes_made.append("Section backgrounds")
        content = new_content
    
    # Note: More complex replacements (text-white, bg colors) require 
    # more sophisticated parsing. For production use, manual replacement
    # or a proper HTML parser (like BeautifulSoup) would be better.
    
    # For now, report what needs manual work
    text_white_count = len(re.findall(r'\btext-white[^"]*', content))
    bg_color_count = len(re.findall(r'bg-\[#[0-9A-Fa-f]{6}\]', content))
    
    if content != original_content:
        # Write back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  ✓ Updated ({', '.join(changes_made)})")
        if text_white_count > 0 or bg_color_count > 0:
            print(f"  ⚠ {text_white_count} text-white and {bg_color_count} bg-color instances may need manual review")
        return True
    else:
        if text_white_count > 0 or bg_color_count > 0:
            print(f"  ⚠ {text_white_count} text-white and {bg_color_count} bg-color instances need manual replacement")
        else:
            print(f"  ✓ No changes needed (already processed)")
        return False

def main():
    """Main function"""
    print("=" * 60)
    print("Theme Replacement Helper Script")
    print("=" * 60)
    print("\nThis script performs basic replacements.")
    print("Complex cases require manual review.\n")
    
    updated_count = 0
    for file_path in FILES_TO_UPDATE:
        if process_file(file_path):
            updated_count += 1
    
    print("\n" + "=" * 60)
    print(f"Summary: Processed {len(FILES_TO_UPDATE)} files")
    print(f"         Updated {updated_count} files")
    print("=" * 60)
    print("\n📝 Next steps:")
    print("   1. Review updated files for correctness")
    print("   2. Manually complete remaining text-white and bg-color replacements")
    print("   3. Test both light and dark modes")
    print("\nSee THEME_APPLICATION_STATUS.md for detailed status.")

if __name__ == '__main__':
    main()
