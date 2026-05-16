"""
마크다운 → HTML 변환 서비스

마크다운을 독립 실행 가능한 HTML로 변환합니다.
인라인 CSS 포함으로 외부 의존성 없이 렌더링 가능.
"""
import html
import logging
import re

logger = logging.getLogger(__name__)

_HEADING = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
_BOLD = re.compile(r'\*\*(.+?)\*\*')
_ITALIC = re.compile(r'(?<!\*)\*([^*]+?)\*(?!\*)')
_STRIKETHROUGH = re.compile(r'~~(.+?)~~')
_INLINE_CODE = re.compile(r'`([^`]+)`')
_CODE_BLOCK = re.compile(r'```(\w*)\n([\s\S]*?)```')
_LINK = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
_IMAGE = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
_BLOCKQUOTE = re.compile(r'^>\s*(.+)$', re.MULTILINE)
_HR = re.compile(r'^[-*_]{3,}\s*$', re.MULTILINE)
_UL_ITEM = re.compile(r'^\s*[-*•]\s+(.+)$', re.MULTILINE)
_OL_ITEM = re.compile(r'^\s*\d+[.)]\s+(.+)$', re.MULTILINE)

_DEFAULT_CSS = """
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
       max-width: 800px; margin: 0 auto; padding: 2rem; line-height: 1.7;
       color: #1a1a1a; background: #fff; }
h1,h2,h3,h4,h5,h6 { color: #111; margin-top: 1.5em; margin-bottom: 0.5em; }
h1 { font-size: 2em; border-bottom: 2px solid #eee; padding-bottom: 0.3em; }
h2 { font-size: 1.5em; border-bottom: 1px solid #eee; padding-bottom: 0.2em; }
code { background: #f4f4f4; padding: 2px 6px; border-radius: 3px; font-size: 0.9em; }
pre { background: #f8f8f8; padding: 1em; border-radius: 6px; overflow-x: auto; }
pre code { background: none; padding: 0; }
blockquote { border-left: 4px solid #ddd; margin: 1em 0; padding: 0.5em 1em; color: #666; }
a { color: #0066cc; text-decoration: none; }
a:hover { text-decoration: underline; }
img { max-width: 100%; height: auto; border-radius: 6px; }
hr { border: none; border-top: 1px solid #eee; margin: 2em 0; }
ul, ol { padding-left: 1.5em; }
li { margin-bottom: 0.3em; }
""".strip()


def convert_to_html(content: str, title: str = '',
                    include_css: bool = True,
                    standalone: bool = True) -> dict:
    """마크다운을 HTML로 변환합니다.

    Args:
        content: 마크다운 콘텐츠
        title: HTML 문서 제목
        include_css: 인라인 CSS 포함 여부
        standalone: 완전한 HTML 문서 생성 여부

    Returns:
        {
            'html': str,
            'char_count': int,
            'has_css': bool,
            'standalone': bool,
        }
    """
    if not content or not content.strip():
        return {'html': '', 'char_count': 0, 'has_css': False, 'standalone': False}

    body_html = _markdown_to_html_body(content.strip())

    if standalone:
        safe_title = html.escape(title or '문서')
        css_block = f'<style>{_DEFAULT_CSS}</style>' if include_css else ''
        full_html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{safe_title}</title>
{css_block}
</head>
<body>
{body_html}
</body>
</html>"""
    else:
        full_html = body_html

    return {
        'html': full_html.strip(),
        'char_count': len(full_html),
        'has_css': include_css and standalone,
        'standalone': standalone,
    }


def _markdown_to_html_body(md: str) -> str:
    """마크다운 본문을 HTML로 변환합니다."""
    text = md

    # 코드 블록 (먼저 처리 — 내부 마크다운 변환 방지)
    code_blocks = {}
    counter = [0]

    def replace_code_block(match):
        lang = match.group(1) or ''
        code = html.escape(match.group(2).strip())
        key = f'__CODE_BLOCK_{counter[0]}__'
        counter[0] += 1
        lang_attr = f' class="language-{lang}"' if lang else ''
        code_blocks[key] = f'<pre><code{lang_attr}>{code}</code></pre>'
        return key

    text = _CODE_BLOCK.sub(replace_code_block, text)

    # 이미지
    text = _IMAGE.sub(lambda m: f'<img src="{html.escape(m.group(2))}" alt="{html.escape(m.group(1))}">', text)

    # 링크
    text = _LINK.sub(lambda m: f'<a href="{html.escape(m.group(2))}">{html.escape(m.group(1))}</a>', text)

    # 인라인 코드
    text = _INLINE_CODE.sub(lambda m: f'<code>{html.escape(m.group(1))}</code>', text)

    # 볼드/이탤릭/취소선
    text = _BOLD.sub(r'<strong>\1</strong>', text)
    text = _ITALIC.sub(r'<em>\1</em>', text)
    text = _STRIKETHROUGH.sub(r'<del>\1</del>', text)

    # 헤딩
    text = _HEADING.sub(lambda m: f'<h{len(m.group(1))}>{m.group(2)}</h{len(m.group(1))}>', text)

    # 인용문
    text = _BLOCKQUOTE.sub(r'<blockquote>\1</blockquote>', text)

    # 수평선
    text = _HR.sub('<hr>', text)

    # 리스트 (간소화: 개별 항목만 변환)
    text = _UL_ITEM.sub(r'<li>\1</li>', text)
    text = _OL_ITEM.sub(r'<li>\1</li>', text)

    # 연속 <li> → <ul> 래핑
    text = re.sub(r'((?:<li>.*?</li>\n?)+)', r'<ul>\1</ul>', text)

    # 문단 (빈 줄로 구분된 텍스트)
    paragraphs = text.split('\n\n')
    processed = []
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        # 이미 블록 요소면 그대로
        if para.startswith(('<h', '<pre', '<ul', '<ol', '<blockquote', '<hr', '__CODE_BLOCK')):
            processed.append(para)
        else:
            processed.append(f'<p>{para}</p>')

    result = '\n'.join(processed)

    # 코드 블록 복원
    for key, block_html in code_blocks.items():
        result = result.replace(key, block_html)
        # <p> 안에 들어간 코드 블록 수정
        result = result.replace(f'<p>{block_html}</p>', block_html)

    return result
