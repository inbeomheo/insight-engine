"""내보내기 라우트 — HTML/Markdown 전용."""
import io
import re as re_module

from flask import request, current_app, send_file

from routes.blog_routes import blog_bp
from src.contexts.identity.interface.auth_decorators import require_auth
from utils.responses import api_error, handle_error


@blog_bp.route('/api/export/markdown', methods=['POST'])
@require_auth
def export_markdown():
    """마크다운 파일로 내보냅니다."""
    try:
        data = request.get_json(silent=True) or {}
        title = data.get('title', 'AI 생성 결과')
        content = data.get('content', '')
        if not content:
            return api_error('변환할 콘텐츠가 없습니다.', 400)

        frontmatter = data.get('frontmatter')

        metadata = None
        if data.get('include_metadata'):
            metadata = {}
            for key in ('model', 'style', 'generated_at'):
                val = data.get(key)
                if val:
                    metadata[key] = val

        include_separator = bool(data.get('include_separator', False))

        from services.export.export_service import export_markdown as _export_md
        buffer = _export_md(
            title,
            content,
            frontmatter=frontmatter,
            metadata=metadata if metadata else None,
            include_separator=include_separator,
        )
        safe_title = re_module.sub(r'[^\w\s가-힣-]', '', title)[:30].strip() or 'content'

        return send_file(
            buffer,
            mimetype='text/markdown',
            as_attachment=True,
            download_name=f'{safe_title}.md',
        )
    except Exception as e:
        current_app.logger.error(f"MD export failed: {e}")
        return api_error('마크다운 내보내기 실패', 500)


def _detect_lang(text: str) -> str:
    """텍스트의 주요 언어를 감지하여 BCP-47 코드를 반환합니다."""
    ko = ja = en = 0
    for ch in text:
        cp = ord(ch)
        if 0xAC00 <= cp <= 0xD7AF or 0x3130 <= cp <= 0x318F:
            ko += 1
        elif 0x3040 <= cp <= 0x309F or 0x30A0 <= cp <= 0x30FF:
            ja += 1
        elif (0x41 <= cp <= 0x5A) or (0x61 <= cp <= 0x7A):
            en += 1
    if ko >= ja and ko >= en:
        return 'ko'
    if ja >= en:
        return 'ja'
    return 'en'


def _build_html_toc(html_content: str) -> str:
    """HTML 콘텐츠에서 h2/h3 태그를 파싱하여 목차 HTML을 생성합니다."""
    headings = re_module.findall(
        r'<(h[23])[^>]*>(.*?)</\1>',
        html_content,
        re_module.IGNORECASE | re_module.DOTALL,
    )
    if not headings:
        return ''

    items = []
    for tag, text in headings:
        clean_text = re_module.sub(r'<[^>]+>', '', text).strip()
        if not clean_text:
            continue
        anchor = re_module.sub(r'[^\w가-힣-]', '-', clean_text).strip('-').lower()
        css_class = 'toc-h3' if tag.lower() == 'h3' else ''
        class_attr = f' class="{css_class}"' if css_class else ''
        items.append(f'<li{class_attr}><a href="#{anchor}">{clean_text}</a></li>')

    if not items:
        return ''

    return '<nav class="toc"><h2>목차</h2><ul>' + '\n'.join(items) + '</ul></nav>'


@blog_bp.route('/api/export/html', methods=['POST'])
@require_auth
def export_html():
    """마크다운/HTML 콘텐츠를 독립 HTML 파일로 변환합니다."""
    try:
        data = request.get_json(silent=True) or {}
        title = data.get('title', 'AI 생성 결과')
        html_content = data.get('html', '') or data.get('content', '')
        dark_mode = data.get('dark_mode', False)
        print_friendly = data.get('print_friendly', False)

        if not html_content:
            return api_error('변환할 콘텐츠가 없습니다.', 400)

        include_toc = data.get('include_toc', False)
        lang = _detect_lang(html_content)

        dark_css = ''
        if dark_mode:
            dark_css = """
@media (prefers-color-scheme: dark) {
body { background: #1a1a2e; color: #e0e0e0; }
h1 { border-bottom-color: #444; }
h2 { color: #d1d5db; }
h3 { color: #9ca3af; }
blockquote { background: #1e293b; color: #93c5fd; border-left-color: #60a5fa; }
code { background: #374151; color: #f9fafb; }
th, td { border-color: #4b5563; }
th { background: #1f2937; }
a { color: #60a5fa; }
.meta { color: #9ca3af; }
}"""

        print_css = "@media print { body { max-width: 100%; padding: 1rem; } a { color: #000; text-decoration: underline; } a[href]::after { content: ' (' attr(href) ')'; font-size: 0.8em; color: #555; } pre { white-space: pre-wrap; word-wrap: break-word; } }" if print_friendly else ''
        toc_html = _build_html_toc(html_content) if include_toc else ''

        standalone_html = f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 800px; margin: 0 auto; padding: 2rem; line-height: 1.8; color: #1a1a1a; }}
h1 {{ font-size: 1.75rem; border-bottom: 2px solid #e5e7eb; padding-bottom: 0.5rem; }}
h2 {{ font-size: 1.4rem; margin-top: 2rem; color: #374151; }}
h3 {{ font-size: 1.15rem; color: #4b5563; }}
p {{ margin: 0.75rem 0; }}
ul, ol {{ padding-left: 1.5rem; }}
li {{ margin: 0.25rem 0; }}
blockquote {{ border-left: 4px solid #3b82f6; margin: 1rem 0; padding: 0.5rem 1rem; background: #eff6ff; color: #1e40af; }}
code {{ background: #f3f4f6; padding: 0.15rem 0.4rem; border-radius: 4px; font-size: 0.9em; }}
pre {{ background: #1f2937; color: #e5e7eb; padding: 1rem; border-radius: 8px; overflow-x: auto; }}
pre code {{ background: transparent; padding: 0; }}
table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
th, td {{ border: 1px solid #d1d5db; padding: 0.5rem 0.75rem; text-align: left; }}
th {{ background: #f9fafb; font-weight: 600; }}
a {{ color: #2563eb; }}
.meta {{ color: #6b7280; font-size: 0.85rem; margin-bottom: 1.5rem; }}
.toc {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 1rem 1.5rem; margin-bottom: 2rem; }}
.toc h2 {{ font-size: 1.1rem; margin: 0 0 0.5rem 0; color: #1e293b; }}
.toc ul {{ list-style: none; padding-left: 0; margin: 0; }}
.toc li {{ margin: 0.25rem 0; }}
.toc a {{ color: #2563eb; text-decoration: none; }}
.toc a:hover {{ text-decoration: underline; }}
.toc .toc-h3 {{ padding-left: 1.2rem; font-size: 0.9em; }}
{dark_css}
{print_css}
</style>
</head>
<body>
<h1>{title}</h1>
<p class="meta">Insight Engine으로 생성됨</p>
{toc_html}
{html_content}
</body>
</html>"""

        buf = io.BytesIO(standalone_html.encode('utf-8'))
        safe_title = re_module.sub(r'[^\w\s가-힣-]', '', title)[:50].strip() or 'export'
        return send_file(
            buf,
            mimetype='text/html',
            as_attachment=True,
            download_name=f'{safe_title}.html',
        )

    except Exception as e:
        return handle_error(e, 'HTML 내보내기')
