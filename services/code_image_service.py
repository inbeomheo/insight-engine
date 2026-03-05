"""
코드 스니펫 → 이미지 서비스
코드 블록을 carbon.sh 스타일 HTML/SVG로 변환
외부 API 불필요 — 순수 HTML+CSS 생성
"""
import html
import logging
import re
from typing import Dict

logger = logging.getLogger(__name__)

# 언어별 구문 하이라이팅 키워드
LANGUAGE_KEYWORDS: Dict[str, list] = {
    'python': ['def', 'class', 'import', 'from', 'return', 'if', 'elif', 'else',
               'for', 'while', 'try', 'except', 'with', 'as', 'yield', 'lambda',
               'True', 'False', 'None', 'and', 'or', 'not', 'in', 'is', 'raise',
               'pass', 'break', 'continue', 'async', 'await'],
    'javascript': ['function', 'const', 'let', 'var', 'return', 'if', 'else',
                    'for', 'while', 'class', 'import', 'export', 'from', 'async',
                    'await', 'new', 'this', 'true', 'false', 'null', 'undefined',
                    'try', 'catch', 'throw', 'typeof', 'instanceof'],
    'typescript': ['function', 'const', 'let', 'var', 'return', 'if', 'else',
                    'for', 'while', 'class', 'import', 'export', 'from', 'async',
                    'await', 'new', 'this', 'true', 'false', 'null', 'undefined',
                    'interface', 'type', 'enum', 'implements', 'extends'],
}

# 테마
THEME = {
    'bg': '#1E1E2E',
    'header': '#313244',
    'text': '#CDD6F4',
    'keyword': '#CBA6F7',
    'string': '#A6E3A1',
    'comment': '#6C7086',
    'number': '#FAB387',
    'dot_red': '#F38BA8',
    'dot_yellow': '#F9E2AF',
    'dot_green': '#A6E3A1',
}


def _highlight_line(line: str, language: str) -> str:
    """한 줄의 코드에 구문 하이라이팅을 적용합니다."""
    safe = html.escape(line)

    # 주석 처리
    comment_patterns = {
        'python': r'(#.*)$',
        'javascript': r'(//.*?)$',
        'typescript': r'(//.*?)$',
    }
    pattern = comment_patterns.get(language, r'(#.*)$')
    safe = re.sub(pattern, f'<span style="color:{THEME["comment"]}">\\1</span>', safe)

    # 문자열 처리 (따옴표)
    safe = re.sub(
        r'(&quot;.*?&quot;|&#x27;.*?&#x27;|&apos;.*?&apos;)',
        f'<span style="color:{THEME["string"]}">\\1</span>',
        safe
    )
    # 백틱 문자열
    safe = re.sub(
        r'(`[^`]*`)',
        f'<span style="color:{THEME["string"]}">\\1</span>',
        safe
    )

    # 숫자 하이라이팅
    safe = re.sub(
        r'\b(\d+(?:\.\d+)?)\b',
        f'<span style="color:{THEME["number"]}">\\1</span>',
        safe
    )

    # 키워드 하이라이팅
    keywords = LANGUAGE_KEYWORDS.get(language, LANGUAGE_KEYWORDS.get('python', []))
    for kw in keywords:
        safe = re.sub(
            rf'\b({re.escape(kw)})\b',
            f'<span style="color:{THEME["keyword"]};font-weight:700">\\1</span>',
            safe
        )

    return safe


def generate_code_image(code: str, language: str = 'python', title: str = '') -> str:
    """코드 블록을 carbon.sh 스타일 HTML로 변환합니다.

    Args:
        code: 소스 코드 문자열
        language: 프로그래밍 언어 ('python', 'javascript', 'typescript' 등)
        title: 파일명 (헤더에 표시, 선택)

    Returns:
        인라인 CSS 포함 HTML 문자열
    """
    if not code or not code.strip():
        return '<p>코드가 없습니다.</p>'

    language = language.lower().strip()
    safe_title = html.escape(title or f'code.{language}')
    lines = code.rstrip('\n').split('\n')

    # 코드 행 HTML 생성
    code_lines_html = ''
    for i, line in enumerate(lines, 1):
        highlighted = _highlight_line(line, language)
        code_lines_html += (
            f'<div style="display:flex;min-height:22px;line-height:22px;">'
            f'<span style="display:inline-block;width:40px;text-align:right;padding-right:16px;'
            f'color:{THEME["comment"]};user-select:none;flex-shrink:0;">{i}</span>'
            f'<span style="flex:1;white-space:pre;overflow-x:auto;">{highlighted}</span>'
            f'</div>'
        )

    return f'''<!DOCTYPE html>
<html lang="ko">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:24px;background:#0D1117;font-family:monospace;">
<div style="max-width:720px;margin:0 auto;border-radius:12px;overflow:hidden;
            box-shadow:0 20px 60px rgba(0,0,0,0.5);background:{THEME["bg"]};">
  <div style="display:flex;align-items:center;padding:12px 16px;background:{THEME["header"]};">
    <div style="display:flex;gap:8px;">
      <div style="width:12px;height:12px;border-radius:50%;background:{THEME["dot_red"]};"></div>
      <div style="width:12px;height:12px;border-radius:50%;background:{THEME["dot_yellow"]};"></div>
      <div style="width:12px;height:12px;border-radius:50%;background:{THEME["dot_green"]};"></div>
    </div>
    <span style="flex:1;text-align:center;color:{THEME["comment"]};font-size:13px;">{safe_title}</span>
  </div>
  <div style="padding:20px 16px;font-size:14px;color:{THEME["text"]};font-family:'Fira Code','JetBrains Mono',Consolas,monospace;">
    {code_lines_html}
  </div>
</div>
</body>
</html>'''
