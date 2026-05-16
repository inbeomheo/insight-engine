"""
소셜 카드 메타태그 생성 서비스

콘텐츠에서 Open Graph + Twitter Card 메타태그를 생성합니다.
"""
import html
import logging
import re

logger = logging.getLogger(__name__)

_HEADING_PATTERN = re.compile(r'^#{1,6}\s+(.+)$', re.MULTILINE)
_IMAGE_PATTERN = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')

# 플랫폼별 설정
CARD_PRESETS = {
    'default': {'og_type': 'article', 'twitter_card': 'summary_large_image'},
    'blog': {'og_type': 'article', 'twitter_card': 'summary_large_image'},
    'product': {'og_type': 'product', 'twitter_card': 'summary'},
    'video': {'og_type': 'video.other', 'twitter_card': 'player'},
}


def generate_social_card(content: str, title: str = '',
                         url: str = '', image_url: str = '',
                         site_name: str = 'Insight Engine',
                         author: str = '', preset: str = 'default') -> dict:
    """Open Graph + Twitter Card 메타태그를 생성합니다.

    Args:
        content: 콘텐츠 본문
        title: 제목 (빈 문자열이면 콘텐츠에서 추출)
        url: 페이지 URL
        image_url: 대표 이미지 URL (빈 문자열이면 콘텐츠에서 추출)
        site_name: 사이트 이름
        author: 작성자
        preset: 카드 프리셋 (default/blog/product/video)

    Returns:
        {
            'og_tags': {tag: value},
            'twitter_tags': {tag: value},
            'meta_html': str,
            'description': str,
        }
    """
    if not content and not title:
        return _empty_result()

    text = (content or '').strip()
    card_preset = CARD_PRESETS.get(preset, CARD_PRESETS['default'])

    # 제목 추출
    if not title:
        match = _HEADING_PATTERN.search(text)
        title = match.group(1).strip() if match else '콘텐츠'

    # 설명 생성 (160자)
    description = _make_description(text, 160)

    # 이미지 추출
    if not image_url and text:
        img_match = _IMAGE_PATTERN.search(text)
        if img_match:
            image_url = img_match.group(2).strip()

    # OG 태그
    og_tags = {
        'og:title': title,
        'og:description': description,
        'og:type': card_preset['og_type'],
        'og:site_name': site_name,
    }
    if url:
        og_tags['og:url'] = url
    if image_url:
        og_tags['og:image'] = image_url
    if author:
        og_tags['article:author'] = author

    # Twitter 태그
    twitter_tags = {
        'twitter:card': card_preset['twitter_card'],
        'twitter:title': title,
        'twitter:description': description,
    }
    if image_url:
        twitter_tags['twitter:image'] = image_url

    # HTML 메타태그 생성
    meta_lines = []
    for tag, value in og_tags.items():
        safe_value = html.escape(value)
        meta_lines.append(f'<meta property="{tag}" content="{safe_value}">')
    for tag, value in twitter_tags.items():
        safe_value = html.escape(value)
        meta_lines.append(f'<meta name="{tag}" content="{safe_value}">')

    meta_html = '\n'.join(meta_lines)

    return {
        'og_tags': og_tags,
        'twitter_tags': twitter_tags,
        'meta_html': meta_html,
        'description': description,
    }


def _make_description(content: str, max_len: int = 160) -> str:
    """설명 텍스트를 생성합니다."""
    if not content:
        return ''
    clean = re.sub(r'^#{1,6}\s+.*$', '', content, flags=re.MULTILINE)
    clean = re.sub(r'[*_`~\[\]!()]', '', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    if len(clean) > max_len:
        clean = clean[:max_len - 3] + '...'
    return clean


def get_card_presets() -> list:
    """사용 가능한 카드 프리셋 목록."""
    return [{'id': pid, **config} for pid, config in CARD_PRESETS.items()]


def _empty_result() -> dict:
    return {'og_tags': {}, 'twitter_tags': {}, 'meta_html': '', 'description': ''}
