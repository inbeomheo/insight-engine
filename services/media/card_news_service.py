"""
카드뉴스 이미지 세트 생성 서비스
콘텐츠를 핵심 포인트로 분할하여 SVG 카드 리스트 생성
"""
import html
import logging
import re
from typing import List

logger = logging.getLogger(__name__)

# 카드 색상 팔레트 (그라데이션 쌍)
CARD_PALETTES = [
    ('#4F46E5', '#7C3AED'),  # 인디고→바이올렛
    ('#7C3AED', '#EC4899'),  # 바이올렛→핑크
    ('#EC4899', '#F59E0B'),  # 핑크→앰버
    ('#10B981', '#06B6D4'),  # 에메랄드→시안
    ('#F59E0B', '#EF4444'),  # 앰버→레드
    ('#06B6D4', '#4F46E5'),  # 시안→인디고
    ('#8B5CF6', '#6366F1'),  # 보라→인디고
    ('#F97316', '#F59E0B'),  # 오렌지→앰버
    ('#14B8A6', '#10B981'),  # 틸→에메랄드
    ('#E11D48', '#EC4899'),  # 로즈→핑크
]


def _split_content_to_points(content: str, max_points: int = 10) -> List[str]:
    """콘텐츠를 핵심 포인트로 분할합니다."""
    points = []

    # 마크다운 헤딩 추출
    headings = re.findall(r'^#{1,3}\s+(.+)$', content, re.MULTILINE)
    for h in headings:
        cleaned = re.sub(r'[*_`#]', '', h).strip()
        if cleaned and len(cleaned) > 2:
            points.append(cleaned)

    # 리스트 아이템 추출
    items = re.findall(r'^[\-\*\+]\s+(.+)$', content, re.MULTILINE)
    for item in items:
        cleaned = re.sub(r'[*_`]', '', item).strip()
        if cleaned and len(cleaned) > 5 and cleaned not in points:
            points.append(cleaned)

    # 번호 리스트 추출
    numbered = re.findall(r'^\d+\.\s+(.+)$', content, re.MULTILINE)
    for item in numbered:
        cleaned = re.sub(r'[*_`]', '', item).strip()
        if cleaned and len(cleaned) > 5 and cleaned not in points:
            points.append(cleaned)

    # 포인트 부족 시 문장 단위 분할
    if len(points) < 3:
        sentences = re.split(r'[.!?。]\s*', content)
        for s in sentences:
            cleaned = re.sub(r'[*_`#\-\[\]]', '', s).strip()
            if cleaned and len(cleaned) > 10 and cleaned not in points:
                points.append(cleaned)
                if len(points) >= max_points:
                    break

    return points[:max_points]


def _wrap_text_svg(text: str, max_chars_per_line: int = 18) -> str:
    """텍스트를 SVG tspan 줄바꿈으로 변환합니다."""
    safe = html.escape(text)
    if len(safe) <= max_chars_per_line:
        return f'<tspan x="400" dy="0">{safe}</tspan>'

    words = safe
    lines = []
    current = ''
    for char in words:
        current += char
        if len(current) >= max_chars_per_line:
            lines.append(current)
            current = ''
    if current:
        lines.append(current)

    tspans = []
    for i, line in enumerate(lines[:4]):  # 최대 4줄
        dy = '0' if i == 0 else '40'
        tspans.append(f'<tspan x="400" dy="{dy}">{line}</tspan>')

    return ''.join(tspans)


def _generate_card_svg(point: str, index: int, total: int, title: str = '') -> str:
    """단일 카드뉴스 SVG를 생성합니다.

    크기: 800x800 (인스타그램 정사각형)
    """
    color1, color2 = CARD_PALETTES[index % len(CARD_PALETTES)]
    safe_title = html.escape(title) if title else ''
    text_svg = _wrap_text_svg(point)

    # 첫 카드는 제목 카드
    if index == 0 and safe_title:
        title_text = _wrap_text_svg(safe_title, 16)
        return f'''<svg xmlns="http://www.w3.org/2000/svg" width="800" height="800" viewBox="0 0 800 800">
  <defs>
    <linearGradient id="bg{index}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{color1}"/>
      <stop offset="100%" style="stop-color:{color2}"/>
    </linearGradient>
  </defs>
  <rect width="800" height="800" rx="24" fill="url(#bg{index})"/>
  <circle cx="400" cy="280" r="60" fill="rgba(255,255,255,0.15)"/>
  <text x="400" y="295" text-anchor="middle" fill="#fff" font-size="36" font-weight="700">📋</text>
  <text x="400" y="420" text-anchor="middle" fill="#fff" font-size="32" font-weight="800"
        font-family="-apple-system,BlinkMacSystemFont,sans-serif">{title_text}</text>
  <text x="400" y="700" text-anchor="middle" fill="rgba(255,255,255,0.6)" font-size="16"
        font-family="-apple-system,sans-serif">{total}장 카드뉴스</text>
</svg>'''

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="800" height="800" viewBox="0 0 800 800">
  <defs>
    <linearGradient id="bg{index}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{color1}"/>
      <stop offset="100%" style="stop-color:{color2}"/>
    </linearGradient>
  </defs>
  <rect width="800" height="800" rx="24" fill="url(#bg{index})"/>
  <circle cx="400" cy="240" r="48" fill="rgba(255,255,255,0.15)"/>
  <text x="400" y="258" text-anchor="middle" fill="#fff" font-size="28" font-weight="800"
        font-family="-apple-system,sans-serif">{index}</text>
  <text x="400" y="420" text-anchor="middle" fill="#fff" font-size="26" font-weight="700"
        font-family="-apple-system,BlinkMacSystemFont,sans-serif">{text_svg}</text>
  <text x="400" y="740" text-anchor="middle" fill="rgba(255,255,255,0.5)" font-size="14"
        font-family="-apple-system,sans-serif">{index}/{total - 1}</text>
</svg>'''


def generate_card_news(content: str, title: str = '') -> List[str]:
    """콘텐츠를 카드뉴스 SVG 세트로 변환합니다.

    Args:
        content: 마크다운 콘텐츠
        title: 카드뉴스 제목 (첫 카드에 표시)

    Returns:
        SVG 문자열 리스트 (첫 번째 = 제목 카드)
    """
    if not content:
        return []

    points = _split_content_to_points(content)
    if not points:
        return []

    # 제목 카드 + 포인트 카드
    total = len(points) + 1
    cards = []

    # 제목 카드
    cards.append(_generate_card_svg(points[0], 0, total, title))

    # 포인트 카드
    for i, point in enumerate(points):
        cards.append(_generate_card_svg(point, i + 1, total))

    return cards
