"""
이메일 뉴스레터 HTML 변환 서비스

마크다운 콘텐츠를 이메일 클라이언트 호환 HTML로 변환합니다.
인라인 CSS + 테이블 레이아웃 사용 (Gmail, Outlook 등 호환).
"""
import logging
import re

logger = logging.getLogger(__name__)

# 이메일 친화 기본 스타일
_BASE_STYLE = {
    'body_bg': '#f4f4f4',
    'content_bg': '#ffffff',
    'text_color': '#333333',
    'heading_color': '#1a1a1a',
    'link_color': '#2563eb',
    'border_color': '#e5e7eb',
    'font_family': "'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif",
}


def _md_to_email_html(content: str) -> str:
    """마크다운 텍스트를 이메일 친화 HTML 블록으로 변환합니다."""
    lines = content.split('\n')
    html_parts = []
    in_list = False
    list_type = None  # 'ul' or 'ol'

    def _close_list():
        nonlocal in_list, list_type
        if in_list:
            html_parts.append(f'</{list_type}>')
            in_list = False
            list_type = None

    for line in lines:
        stripped = line.strip()

        if not stripped:
            _close_list()
            html_parts.append('<br/>')
            continue

        # 헤딩
        if stripped.startswith('###'):
            _close_list()
            text = _inline_format(stripped.lstrip('#').strip())
            html_parts.append(
                f'<h3 style="color:{_BASE_STYLE["heading_color"]};font-size:16px;'
                f'margin:20px 0 8px 0;font-weight:600;">{text}</h3>'
            )
        elif stripped.startswith('##'):
            _close_list()
            text = _inline_format(stripped.lstrip('#').strip())
            html_parts.append(
                f'<h2 style="color:{_BASE_STYLE["heading_color"]};font-size:20px;'
                f'margin:24px 0 10px 0;font-weight:700;">{text}</h2>'
            )
        elif stripped.startswith('#'):
            _close_list()
            text = _inline_format(stripped.lstrip('#').strip())
            html_parts.append(
                f'<h1 style="color:{_BASE_STYLE["heading_color"]};font-size:24px;'
                f'margin:28px 0 12px 0;font-weight:700;">{text}</h1>'
            )

        # 수평선
        elif stripped in ('---', '***', '___'):
            _close_list()
            html_parts.append(
                f'<hr style="border:0;border-top:1px solid {_BASE_STYLE["border_color"]};margin:20px 0;"/>'
            )

        # 인용문
        elif stripped.startswith('>'):
            _close_list()
            text = _inline_format(stripped.lstrip('>').strip())
            html_parts.append(
                f'<blockquote style="border-left:3px solid {_BASE_STYLE["link_color"]};'
                f'padding:8px 16px;margin:12px 0;color:#555;font-style:italic;">'
                f'{text}</blockquote>'
            )

        # 비순서 목록
        elif stripped.startswith(('- ', '* ', '+ ')):
            if not in_list or list_type != 'ul':
                _close_list()
                html_parts.append('<ul style="padding-left:20px;margin:8px 0;">')
                in_list = True
                list_type = 'ul'
            text = _inline_format(stripped[2:].strip())
            html_parts.append(f'<li style="margin:4px 0;line-height:1.6;">{text}</li>')

        # 순서 목록
        elif re.match(r'^\d+\.\s', stripped):
            if not in_list or list_type != 'ol':
                _close_list()
                html_parts.append('<ol style="padding-left:20px;margin:8px 0;">')
                in_list = True
                list_type = 'ol'
            text = _inline_format(re.sub(r'^\d+\.\s', '', stripped).strip())
            html_parts.append(f'<li style="margin:4px 0;line-height:1.6;">{text}</li>')

        # 일반 텍스트
        else:
            _close_list()
            text = _inline_format(stripped)
            html_parts.append(
                f'<p style="margin:8px 0;line-height:1.7;color:{_BASE_STYLE["text_color"]};">{text}</p>'
            )

    _close_list()
    return '\n'.join(html_parts)


def _inline_format(text: str) -> str:
    """마크다운 인라인 서식을 HTML로 변환합니다."""
    # 볼드
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # 이탤릭
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    # 인라인 코드
    text = re.sub(r'`(.+?)`', r'<code style="background:#f3f4f6;padding:2px 4px;border-radius:3px;font-size:13px;">\1</code>', text)
    # 링크
    text = re.sub(r'\[(.+?)\]\((.+?)\)', rf'<a href="\2" style="color:{_BASE_STYLE["link_color"]};">\1</a>', text)
    return text


def convert_to_newsletter(content: str, title: str) -> str:
    """마크다운 콘텐츠를 이메일 뉴스레터 HTML로 변환합니다.

    Args:
        content: 마크다운 콘텐츠
        title: 뉴스레터 제목

    Returns:
        이메일 클라이언트 호환 HTML 문자열

    Raises:
        ValueError: 콘텐츠가 비어 있음
    """
    if not content or not content.strip():
        raise ValueError('변환할 콘텐츠가 필요합니다.')

    body_html = _md_to_email_html(content)
    s = _BASE_STYLE

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>{title}</title>
</head>
<body style="margin:0;padding:0;background-color:{s['body_bg']};font-family:{s['font_family']};">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:{s['body_bg']};">
<tr><td align="center" style="padding:24px 16px;">
<table role="presentation" width="600" cellpadding="0" cellspacing="0"
  style="max-width:600px;width:100%;background-color:{s['content_bg']};border-radius:8px;overflow:hidden;">

  <!-- 헤더 -->
  <tr><td style="background-color:{s['link_color']};padding:28px 32px;">
    <h1 style="margin:0;color:#ffffff;font-size:22px;font-weight:700;line-height:1.4;">
      {title}
    </h1>
  </td></tr>

  <!-- 본문 -->
  <tr><td style="padding:28px 32px;">
    {body_html}
  </td></tr>

  <!-- 푸터 -->
  <tr><td style="padding:20px 32px;border-top:1px solid {s['border_color']};text-align:center;">
    <p style="margin:0;font-size:12px;color:#9ca3af;line-height:1.5;">
      Insight Engine으로 자동 생성된 뉴스레터입니다.
    </p>
  </td></tr>

</table>
</td></tr>
</table>
</body>
</html>"""

    return html
