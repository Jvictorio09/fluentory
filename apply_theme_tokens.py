#!/usr/bin/env python3
"""
Script to systematically apply dual theme tokens across all dashboard templates.
Replaces hard-coded dark mode styles with light-first, dark-overlay approach.
"""

import os
import re
from pathlib import Path

# Replacement mappings following the dual token system
REPLACEMENTS = [
    # Text colors - Light first, dark overlay
    (r'\btext-white\b', 'text-gray-900 dark:text-white'),
    (r'\btext-white/70\b', 'text-gray-600 dark:text-white/70'),
    (r'\btext-white/60\b', 'text-gray-500 dark:text-white/60'),
    (r'\btext-white/50\b', 'text-gray-500 dark:text-white/50'),
    (r'\btext-white/40\b', 'text-gray-400 dark:text-white/40'),
    
    # Backgrounds - Light first, dark overlay
    (r'\bbg-\[#04363a\]/70\b', 'bg-white dark:bg-[#04363a]/70'),
    (r'\bbg-\[#254346\]/70\b', 'bg-white dark:bg-[#254346]/70'),
    (r'\bbg-\[#254346\]/50\b', 'bg-gray-50 dark:bg-[#254346]/50'),
    (r'\bbg-\[#254346\]/90\b', 'bg-gray-100 dark:bg-[#254346]/90'),
    
    # Borders - Light first, dark overlay
    (r'\bborder-white/10\b', 'border-gray-200 dark:border-white/10'),
    (r'\bborder-white/20\b', 'border-gray-300 dark:border-white/20'),
    
    # Dividers
    (r'\bdivide-white/10\b', 'divide-gray-200 dark:divide-white/10'),
    
    # Hover states
    (r'\bhover:bg-\[#82C293\]/5\b', 'hover:bg-emerald-50 dark:hover:bg-[#82C293]/5'),
    (r'\bhover:bg-\[#254346\]/90\b', 'hover:bg-gray-50 dark:hover:bg-[#254346]/90'),
    (r'\bhover:border-\[#82C293\]/40\b', 'hover:border-emerald-300 dark:hover:border-[#82C293]/40'),
    
    # Status pills - Light variants
    (r'\bbg-\[#259d78\]/20\s+text-\[#259d78\]\s+border\s+border-\[#259d78\]/30\b', 
     'bg-emerald-100 dark:bg-[#259d78]/20 text-emerald-700 dark:text-[#259d78] border border-emerald-300 dark:border-[#259d78]/30'),
    
    (r'\bbg-\[#82C293\]/20\s+text-\[#82C293\]\s+border\s+border-\[#82C293\]/30\b',
     'bg-emerald-100 dark:bg-[#82C293]/20 text-emerald-700 dark:text-[#82C293] border border-emerald-300 dark:border-[#82C293]/30'),
    
    (r'\bbg-\[#f8da03\]/20\s+text-\[#f8da03\]\s+border\s+border-\[#f8da03\]/40\b',
     'bg-yellow-100 dark:bg-[#f8da03]/20 text-yellow-700 dark:text-[#f8da03] border border-yellow-300 dark:border-[#f8da03]/40'),
    
    # Focus states
    (r'\bfocus:ring-\[#82C293\]/40\b', 'focus:ring-emerald-300 dark:focus:ring-[#82C293]/40'),
    (r'\bfocus:border-\[#82C293\]/50\b', 'focus:border-emerald-400 dark:focus:border-[#82C293]/50'),
    
    # Shadows
    (r'\bshadow-\[0_15px_40px_rgba\(0,0,0,0\.3\)\]\b', 'shadow-lg dark:shadow-[0_15px_40px_rgba(0,0,0,0.3)]'),
    (r'\bhover:shadow-\[0_20px_50px_rgba\(130,194,147,0\.2\)\]\b', 'hover:shadow-xl dark:hover:shadow-[0_20px_50px_rgba(130,194,147,0.2)]'),
    
    # Links/Accents
    (r'\btext-\[#82C293\]\b', 'text-emerald-600 dark:text-[#82C293]'),
    (r'\bhover:text-\[#8abc59\]\b', 'hover:text-emerald-700 dark:hover:text-[#8abc59]'),
    (r'\bhover:bg-\[#82C293\]/10\b', 'hover:bg-emerald-50 dark:hover:bg-[#82C293]/10'),
    
    # Placeholder text
    (r'\bplaceholder:text-white/40\b', 'placeholder:text-gray-400 dark:placeholder:text-white/40'),
]

# Directories to process
DASHBOARD_DIRS = [
    'myApp/templates/dashboard',
    'myApp/templates/student',
    'myApp/templates/teacher',
    'myApp/templates/admin',
    'myApp/templates/partner',
]

def apply_replacements(content: str) -> str:
    """Apply all replacements to content."""
    for pattern, replacement in REPLACEMENTS:
        content = re.sub(pattern, replacement, content)
    return content

def process_file(file_path: Path):
    """Process a single template file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        content = apply_replacements(content)
        
        # Only write if content changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ Updated: {file_path}")
            return True
        else:
            print(f"⊘ No changes: {file_path}")
            return False
    except Exception as e:
        print(f"✗ Error processing {file_path}: {e}")
        return False

def main():
    """Main function to process all dashboard templates."""
    base_path = Path(__file__).parent
    
    total_files = 0
    updated_files = 0
    
    for dir_path in DASHBOARD_DIRS:
        full_dir = base_path / dir_path
        if not full_dir.exists():
            print(f"Warning: Directory not found: {full_dir}")
            continue
        
        # Find all HTML files
        html_files = list(full_dir.rglob('*.html'))
        
        # Filter out base templates that should be handled separately
        html_files = [f for f in html_files if 'base.html' not in str(f) or 'base_site.html' in str(f)]
        
        for file_path in html_files:
            total_files += 1
            if process_file(file_path):
                updated_files += 1
    
    print(f"\n{'='*60}")
    print(f"Processed: {total_files} files")
    print(f"Updated: {updated_files} files")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()





