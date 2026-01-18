"""
Django template filter for rendering Editor.js JSON blocks to HTML
"""
from django import template
from django.utils.safestring import mark_safe
import json

register = template.Library()


@register.filter
def render_editorjs(content):
    """
    Convert Editor.js JSON blocks to HTML
    
    Usage:
        {{ lesson.content|render_editorjs }}
    """
    if not content:
        return mark_safe('')
    
    # Handle string JSON
    if isinstance(content, str):
        try:
            content = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            return mark_safe('<p class="text-white/60">Invalid content format</p>')
    
    # Handle dict with blocks
    if isinstance(content, dict):
        blocks = content.get('blocks', [])
        if not blocks:
            return mark_safe('')
    elif isinstance(content, list):
        blocks = content
    else:
        return mark_safe('')
    
    html_parts = []
    
    for block in blocks:
        block_type = block.get('type', '')
        block_data = block.get('data', {})
        
        if block_type == 'paragraph':
            text = block_data.get('text', '')
            html_parts.append(f'<p class="mb-4 text-white/90 leading-relaxed">{text}</p>')
        
        elif block_type == 'header':
            text = block_data.get('text', '')
            level = block_data.get('level', 2)
            if level == 1:
                html_parts.append(f'<h1 class="text-4xl font-bold mt-8 mb-4 text-white">{text}</h1>')
            elif level == 2:
                html_parts.append(f'<h2 class="text-3xl font-bold mt-8 mb-4 text-white">{text}</h2>')
            elif level == 3:
                html_parts.append(f'<h3 class="text-2xl font-semibold mt-6 mb-3 text-white">{text}</h3>')
            elif level == 4:
                html_parts.append(f'<h4 class="text-xl font-semibold mt-4 mb-2 text-white">{text}</h4>')
        
        elif block_type == 'list':
            items = block_data.get('items', [])
            style = block_data.get('style', 'unordered')
            if style == 'ordered':
                items_html = ''.join([f'<li class="mb-2 text-white/90">{item}</li>' for item in items])
                html_parts.append(f'<ol class="list-decimal pl-6 mb-4 space-y-2">{items_html}</ol>')
            else:
                items_html = ''.join([f'<li class="mb-2 text-white/90">{item}</li>' for item in items])
                html_parts.append(f'<ul class="list-disc pl-6 mb-4 space-y-2">{items_html}</ul>')
        
        elif block_type == 'quote':
            text = block_data.get('text', '')
            caption = block_data.get('caption', '')
            caption_html = f'<cite class="block mt-2 text-sm text-white/60">— {caption}</cite>' if caption else ''
            html_parts.append(f'<blockquote class="border-l-4 border-[#82C293] pl-4 italic my-6 text-white/80">{text}{caption_html}</blockquote>')
        
        elif block_type == 'code':
            code = block_data.get('code', '')
            html_parts.append(f'<pre class="bg-[#254346] text-white/90 rounded-lg p-4 overflow-auto my-4"><code>{code}</code></pre>')
        
        elif block_type == 'table':
            content_data = block_data.get('content', [])
            if content_data:
                rows_html = []
                for row in content_data:
                    cells_html = ''.join([f'<td class="px-4 py-2 border border-white/10 text-white/90">{cell}</td>' for cell in row])
                    rows_html.append(f'<tr>{cells_html}</tr>')
                table_html = ''.join(rows_html)
                html_parts.append(f'<div class="overflow-x-auto my-6"><table class="min-w-full border-collapse border border-white/10"><tbody>{table_html}</tbody></table></div>')
        
        elif block_type == 'delimiter':
            html_parts.append('<div class="my-8 text-center"><span class="text-4xl text-white/40">***</span></div>')
        
        elif block_type == 'raw':
            html = block_data.get('html', '')
            html_parts.append(f'<div class="my-4">{html}</div>')
        
        elif block_type == 'image':
            url = block_data.get('file', {}).get('url', '') or block_data.get('url', '')
            caption = block_data.get('caption', '')
            caption_html = f'<figcaption class="text-center mt-2 text-sm text-white/60">{caption}</figcaption>' if caption else ''
            if url:
                html_parts.append(f'<figure class="my-6"><img src="{url}" alt="{caption}" class="rounded-xl shadow-lg w-full max-w-4xl mx-auto" loading="lazy"/>{caption_html}</figure>')
    
    return mark_safe(''.join(html_parts))

