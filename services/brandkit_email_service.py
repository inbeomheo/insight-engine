"""
브랜드 이메일 생성 서비스

브랜드 가이드라인(색상, 로고, 톤)을 적용하여
HTML/Plain 이메일 콘텐츠를 자동 생성합니다.
"""
import logging
import re
from dataclasses import dataclass, field
from typing import Dict

logger = logging.getLogger(__name__)


@dataclass
class BrandedEmail:
    """브랜드 적용된 이메일"""
    subject: str
    preview_text: str
    body_html: str
    body_plain: str
    brand_colors: Dict[str, str] = field(default_factory=dict)


# 기본 브랜드 색상
_DEFAULT_COLORS = {
    'primary': '#2563EB',
    'secondary': '#64748B',
    'background': '#F8FAFC',
    'text': '#1E293B',
    'accent': '#3B82F6',
}

# HTML 이메일 템플릿 (인라인 CSS 필수)
_EMAIL_TEMPLATE = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background-color:{bg_color};font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;margin:0 auto;">
  <tr><td style="background-color:{primary_color};padding:24px;text-align:center;">
    {header_content}
  </td></tr>
  <tr><td style="background-color:#FFFFFF;padding:32px;color:{text_color};font-size:16px;line-height:1.6;">
    {body_content}
  </td></tr>
  <tr><td style="background-color:{bg_color};padding:16px;text-align:center;color:{secondary_color};font-size:12px;">
    {footer_content}
  </td></tr>
</table>
</body>
</html>"""


def _extract_colors(brand: dict) -> dict:
    """브랜드 정보에서 색상을 추출합니다."""
    colors = dict(_DEFAULT_COLORS)
    brand_colors = brand.get('colors', {})
    if isinstance(brand_colors, dict):
        for key in _DEFAULT_COLORS:
            if key in brand_colors:
                colors[key] = brand_colors[key]
    # 직접 키로도 지원
    if brand.get('primary_color'):
        colors['primary'] = brand['primary_color']
    if brand.get('text_color'):
        colors['text'] = brand['text_color']
    return colors


def _generate_subject(content: str, brand: dict) -> str:
    """콘텐츠에서 이메일 제목을 생성합니다."""
    brand_name = brand.get('name', brand.get('brand_name', ''))
    # 첫 문장 또는 첫 줄을 제목으로 사용
    first_line = content.strip().split('\n')[0].strip()
    # 마크다운 헤더 제거
    first_line = re.sub(r'^#+\s*', '', first_line)
    # 너무 길면 잘라내기
    if len(first_line) > 60:
        first_line = first_line[:57] + '...'
    if brand_name:
        return f"[{brand_name}] {first_line}"
    return first_line


def _generate_preview(content: str) -> str:
    """미리보기 텍스트를 생성합니다 (90자 이내)."""
    # 마크다운 제거
    plain = re.sub(r'[#*_`\[\]()]', '', content)
    plain = re.sub(r'\n+', ' ', plain).strip()
    if len(plain) > 90:
        return plain[:87] + '...'
    return plain


def _content_to_html(content: str) -> str:
    """콘텐츠 텍스트를 간단한 HTML로 변환합니다."""
    lines = content.strip().split('\n')
    html_parts = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # 마크다운 헤더 → h2/h3
        if line.startswith('## '):
            html_parts.append(f'<h2 style="margin:20px 0 8px;font-size:20px;">{line[3:]}</h2>')
        elif line.startswith('# '):
            html_parts.append(f'<h2 style="margin:20px 0 8px;font-size:22px;">{line[2:]}</h2>')
        elif line.startswith('### '):
            html_parts.append(f'<h3 style="margin:16px 0 6px;font-size:18px;">{line[4:]}</h3>')
        elif line.startswith('- ') or line.startswith('* '):
            html_parts.append(f'<p style="margin:4px 0 4px 16px;">&bull; {line[2:]}</p>')
        else:
            # 볼드/이탤릭 처리
            line = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line)
            line = re.sub(r'\*(.+?)\*', r'<em>\1</em>', line)
            html_parts.append(f'<p style="margin:8px 0;">{line}</p>')
    return '\n'.join(html_parts)


def _content_to_plain(content: str) -> str:
    """콘텐츠를 플레인 텍스트로 변환합니다."""
    plain = re.sub(r'[#*_`]', '', content)
    plain = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', plain)  # 링크 → 텍스트만
    return plain.strip()


def generate_branded_email(content: str, brand: dict) -> BrandedEmail:
    """브랜드 가이드라인을 적용한 이메일을 생성합니다.

    Args:
        content: 이메일 본문 콘텐츠 (마크다운 또는 플레인 텍스트)
        brand: 브랜드 정보 딕셔너리
            - name (str): 브랜드명
            - colors (dict): primary, secondary, background, text, accent 색상
            - logo_url (str, 선택): 로고 URL
            - footer (str, 선택): 푸터 텍스트

    Returns:
        BrandedEmail
    """
    if not content:
        return BrandedEmail(
            subject='(제목 없음)',
            preview_text='',
            body_html='',
            body_plain='',
            brand_colors=_DEFAULT_COLORS,
        )

    brand = brand or {}
    colors = _extract_colors(brand)
    subject = _generate_subject(content, brand)
    preview = _generate_preview(content)

    # 헤더 구성
    brand_name = brand.get('name', brand.get('brand_name', ''))
    logo_url = brand.get('logo_url', '')
    header_parts = []
    if logo_url:
        header_parts.append(
            f'<img src="{logo_url}" alt="{brand_name}" '
            f'style="max-height:40px;margin-bottom:8px;" /><br/>'
        )
    if brand_name:
        header_parts.append(
            f'<span style="color:#FFFFFF;font-size:20px;font-weight:bold;">{brand_name}</span>'
        )
    header_content = ''.join(header_parts) or '&nbsp;'

    # 본문 HTML
    body_content = _content_to_html(content)

    # 푸터
    footer = brand.get('footer', f'&copy; {brand_name}' if brand_name else '')

    body_html = _EMAIL_TEMPLATE.format(
        bg_color=colors['background'],
        primary_color=colors['primary'],
        text_color=colors['text'],
        secondary_color=colors['secondary'],
        header_content=header_content,
        body_content=body_content,
        footer_content=footer,
    )

    body_plain = _content_to_plain(content)

    return BrandedEmail(
        subject=subject,
        preview_text=preview,
        body_html=body_html,
        body_plain=body_plain,
        brand_colors=colors,
    )
