"""
슬라이드 변환 서비스

마크다운 콘텐츠를 Reveal.js HTML 슬라이드로 변환합니다.
## 헤딩을 슬라이드 구분자로 사용합니다.
"""
import logging
import re
from html import escape

logger = logging.getLogger(__name__)


def convert_to_slides(markdown_content: str, theme: str = 'black') -> str:
    """마크다운을 Reveal.js HTML 슬라이드로 변환합니다.

    Args:
        markdown_content: 마크다운 형식의 콘텐츠
        theme: Reveal.js 테마 (black, white, league, beige, sky, night, serif, simple, solarized)

    Returns:
        독립 실행 가능한 Reveal.js HTML 문자열
    """
    if not markdown_content or not markdown_content.strip():
        raise ValueError('변환할 콘텐츠가 없습니다.')

    try:
        slides = _split_into_slides(markdown_content)
        slides_html = '\n'.join(_render_slide(s) for s in slides)
    except ValueError:
        raise
    except Exception as e:
        logger.error('슬라이드 변환 중 오류: %s', e)
        raise RuntimeError(f'슬라이드 변환 실패: {e}') from e

    return f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>슬라이드</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/reveal.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/theme/{escape(theme)}.css">
<style>
  .reveal h1, .reveal h2, .reveal h3 {{ font-family: 'Pretendard', sans-serif; }}
  .reveal pre {{ text-align: left; font-size: 0.65em; }}
  .reveal ul, .reveal ol {{ text-align: left; }}
  .reveal blockquote {{ font-style: italic; border-left: 4px solid #666; padding-left: 1em; }}
</style>
</head>
<body>
<div class="reveal">
  <div class="slides">
{slides_html}
  </div>
</div>
<script src="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/reveal.js"></script>
<script>Reveal.initialize({{ hash: true }});</script>
</body>
</html>'''


def _split_into_slides(markdown: str) -> list[str]:
    """마크다운을 ## 헤딩 기준으로 슬라이드 단위로 분할합니다."""
    # ## 또는 # 헤딩으로 분할
    parts = re.split(r'(?=^#{1,2}\s)', markdown.strip(), flags=re.MULTILINE)
    slides = [p.strip() for p in parts if p.strip()]
    # 슬라이드가 없으면 전체를 한 슬라이드로
    return slides if slides else [markdown.strip()]


def _convert_markdown_line(stripped: str) -> str:
    """단일 마크다운 줄을 HTML 태그로 변환합니다."""
    if not stripped:
        return ''
    if stripped.startswith('### '):
        return f'<h3>{_inline_format(stripped[4:])}</h3>'
    if stripped.startswith('## '):
        return f'<h2>{_inline_format(stripped[3:])}</h2>'
    if stripped.startswith('# '):
        return f'<h1>{_inline_format(stripped[2:])}</h1>'
    if stripped.startswith('> '):
        return f'<blockquote>{_inline_format(stripped[2:])}</blockquote>'
    if re.match(r'^[-*+]\s', stripped):
        return f'<li>{_inline_format(stripped[2:])}</li>'
    if re.match(r'^\d+\.\s', stripped):
        text = re.sub(r'^\d+\.\s', '', stripped)
        return f'<li>{_inline_format(text)}</li>'
    if re.match(r'^!\[.*?\]\(.*?\)', stripped):
        m = re.match(r'^!\[(.*?)\]\((.*?)\)', stripped)
        if m:
            return f'<img src="{escape(m.group(2))}" alt="{escape(m.group(1))}" style="max-height:400px;">'
        return ''
    if stripped in ('---', '***', '___'):
        return '<hr>'
    return f'<p>{_inline_format(stripped)}</p>'


def _render_slide(content: str) -> str:
    """단일 슬라이드 내용을 HTML로 변환합니다."""
    lines = content.split('\n')
    html_parts = []
    in_code_block = False
    code_lang = ''
    code_lines: list[str] = []

    for line in lines:
        if line.strip().startswith('```'):
            if in_code_block:
                code = escape('\n'.join(code_lines))
                html_parts.append(f'<pre><code class="{escape(code_lang)}">{code}</code></pre>')
                code_lines = []
                in_code_block = False
            else:
                in_code_block = True
                code_lang = line.strip()[3:].strip()
            continue

        if in_code_block:
            code_lines.append(line)
            continue

        tag = _convert_markdown_line(line.strip())
        if tag:
            html_parts.append(tag)

    if in_code_block and code_lines:
        code = escape('\n'.join(code_lines))
        html_parts.append(f'<pre><code>{code}</code></pre>')

    result = _wrap_list_items('\n'.join(html_parts))
    return f'    <section>\n      {result}\n    </section>'


def _inline_format(text: str) -> str:
    """인라인 마크다운 서식을 HTML로 변환합니다."""
    text = escape(text)
    # 볼드
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # 이탤릭
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    # 인라인 코드
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    # 링크
    text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', text)
    return text


def _wrap_list_items(html: str) -> str:
    """연속된 <li> 태그를 <ul>로 감쌉니다."""
    return re.sub(
        r'((?:<li>.*?</li>\n?)+)',
        r'<ul>\1</ul>',
        html
    )
