"""
콘텐츠 템플릿 엔진 서비스

콘텐츠 구조 템플릿을 생성, 적용, 관리합니다.
인메모리 템플릿 — 마크다운 구조(헤딩/섹션)를 추출하여 재사용.
"""
import logging
import re
from typing import List

logger = logging.getLogger(__name__)

_HEADING_PATTERN = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)

# 기본 제공 템플릿
BUILTIN_TEMPLATES = {
    'blog_post': {
        'name': '블로그 포스트',
        'sections': [
            {'level': 1, 'title': '{제목}'},
            {'level': 2, 'title': '서론'},
            {'level': 2, 'title': '본론'},
            {'level': 3, 'title': '핵심 포인트 1'},
            {'level': 3, 'title': '핵심 포인트 2'},
            {'level': 2, 'title': '결론'},
        ],
    },
    'tutorial': {
        'name': '튜토리얼',
        'sections': [
            {'level': 1, 'title': '{제목}'},
            {'level': 2, 'title': '개요'},
            {'level': 2, 'title': '사전 준비'},
            {'level': 2, 'title': '단계 1: {설명}'},
            {'level': 2, 'title': '단계 2: {설명}'},
            {'level': 2, 'title': '단계 3: {설명}'},
            {'level': 2, 'title': '마무리'},
            {'level': 2, 'title': 'FAQ'},
        ],
    },
    'review': {
        'name': '리뷰',
        'sections': [
            {'level': 1, 'title': '{제목} 리뷰'},
            {'level': 2, 'title': '개요'},
            {'level': 2, 'title': '장점'},
            {'level': 2, 'title': '단점'},
            {'level': 2, 'title': '비교'},
            {'level': 2, 'title': '총평'},
        ],
    },
    'newsletter': {
        'name': '뉴스레터',
        'sections': [
            {'level': 1, 'title': '{제목}'},
            {'level': 2, 'title': '이번 주 핵심'},
            {'level': 2, 'title': '트렌드'},
            {'level': 2, 'title': '추천 콘텐츠'},
            {'level': 2, 'title': '다음 주 예고'},
        ],
    },
}


def extract_template(content: str, template_name: str = '') -> dict:
    """콘텐츠에서 구조 템플릿을 추출합니다.

    Args:
        content: 원본 콘텐츠
        template_name: 템플릿 이름 (빈 문자열이면 자동 생성)

    Returns:
        {
            'name': str,
            'sections': [{'level': int, 'title': str}],
            'section_count': int,
        }
    """
    if not content or not content.strip():
        return {'name': '', 'sections': [], 'section_count': 0}

    sections = []
    for match in _HEADING_PATTERN.finditer(content):
        level = len(match.group(1))
        title = match.group(2).strip()
        sections.append({'level': level, 'title': title})

    name = template_name or ('커스텀 템플릿' if sections else '')

    return {
        'name': name,
        'sections': sections,
        'section_count': len(sections),
    }


def apply_template(template_id: str = '', custom_sections: List[dict] = None,
                   placeholders: dict = None) -> dict:
    """템플릿을 적용하여 마크다운 스켈레톤을 생성합니다.

    Args:
        template_id: 빌트인 템플릿 ID (빈 문자열이면 custom_sections 사용)
        custom_sections: 커스텀 섹션 목록 [{'level': int, 'title': str}]
        placeholders: 플레이스홀더 치환 딕셔너리 ({'제목': '실제 제목'})

    Returns:
        {
            'markdown': str,
            'template_name': str,
            'section_count': int,
        }
    """
    if template_id and template_id in BUILTIN_TEMPLATES:
        template = BUILTIN_TEMPLATES[template_id]
        sections = template['sections']
        name = template['name']
    elif custom_sections:
        sections = custom_sections
        name = '커스텀 템플릿'
    else:
        return {'markdown': '', 'template_name': '', 'section_count': 0}

    placeholders = placeholders or {}
    lines = []

    for section in sections:
        try:
            level = int(section.get('level', 2))
        except (TypeError, ValueError):
            level = 2
        title = str(section.get('title', '섹션'))

        # 플레이스홀더 치환
        for key, value in placeholders.items():
            title = title.replace(f'{{{key}}}', str(value))

        prefix = '#' * max(1, min(6, level))
        lines.append(f'{prefix} {title}')
        lines.append('')
        lines.append('')  # 본문 작성 공간

    markdown = '\n'.join(lines).strip()

    return {
        'markdown': markdown,
        'template_name': name,
        'section_count': len(sections),
    }


def list_templates() -> list:
    """사용 가능한 빌트인 템플릿 목록을 반환합니다."""
    return [
        {
            'id': tid,
            'name': template['name'],
            'section_count': len(template['sections']),
            'sections': [s['title'] for s in template['sections']],
        }
        for tid, template in BUILTIN_TEMPLATES.items()
    ]
