"""
콘텐츠 A/B 테스트 변형 생성 서비스

제목, 도입부, CTA를 규칙 기반 템플릿으로
다양한 변형을 생성합니다. AI 호출 없이 즉시 처리.
"""
import logging
import re
from typing import List

logger = logging.getLogger(__name__)

# 제목 변형 패턴
_TITLE_PATTERNS = {
    'question': '{}에 대해 알고 계셨나요?',
    'how_to': '{} 완벽 가이드',
    'listicle': '{}에 대한 핵심 포인트 정리',
    'urgent': '지금 바로 알아야 할 {}',
    'benefit': '{}로 달라지는 것들',
    'contrarian': '{}에 대한 오해와 진실',
    'curiosity': '아무도 말하지 않는 {}의 비밀',
}

# 도입부 변형 패턴
_INTRO_PATTERNS = {
    'question': '{}에 대해 깊이 생각해 본 적이 있으신가요?',
    'statistic': '최근 조사에 따르면, {}이(가) 주목받고 있습니다.',
    'story': '{}을(를) 처음 접했을 때, 많은 사람들이 놀라움을 감추지 못합니다.',
    'direct': '이 글에서는 {}에 대해 핵심만 정리했습니다.',
    'pain_point': '{}때문에 고민하고 계신다면, 이 글이 도움이 될 것입니다.',
}

# CTA 변형 패턴
_CTA_PATTERNS = {
    'share': '이 글이 유용했다면 공유해 주세요.',
    'comment': '여러분의 의견을 댓글로 남겨 주세요.',
    'subscribe': '더 많은 콘텐츠를 받아보려면 구독하세요.',
    'action': '지금 바로 시작해 보세요.',
    'bookmark': '나중에 다시 읽을 수 있도록 북마크하세요.',
}


def _extract_topic(title: str, content: str) -> str:
    """제목 또는 콘텐츠에서 핵심 주제를 추출합니다."""
    if title and title.strip():
        # 불필요한 접두사 제거
        topic = re.sub(r'^(#\s+|제목:\s*)', '', title.strip())
        return topic

    # 첫 헤딩에서 추출
    heading = re.search(r'^#{1,3}\s+(.+)$', content, re.MULTILINE)
    if heading:
        return heading.group(1).strip()

    # 첫 문장에서 추출
    first_sent = re.split(r'[.!?]', content)[0].strip()
    return first_sent[:50] if first_sent else '이 주제'


def generate_variants(content: str, title: str = '',
                      variant_types: List[str] = None) -> dict:
    """콘텐츠에서 A/B 테스트 변형을 생성합니다.

    Args:
        content: 원본 콘텐츠
        title: 원본 제목
        variant_types: 생성할 변형 유형 (title/intro/cta). None이면 전체.

    Returns:
        {
            'topic': str,
            'title_variants': [{'type': str, 'text': str}],
            'intro_variants': [{'type': str, 'text': str}],
            'cta_variants': [{'type': str, 'text': str}],
            'total': int,
        }
    """
    if not content or not content.strip():
        return {'topic': '', 'title_variants': [], 'intro_variants': [], 'cta_variants': [], 'total': 0}

    types = variant_types or ['title', 'intro', 'cta']
    topic = _extract_topic(title, content)

    result = {
        'topic': topic,
        'title_variants': [],
        'intro_variants': [],
        'cta_variants': [],
    }

    if 'title' in types:
        for vtype, pattern in _TITLE_PATTERNS.items():
            result['title_variants'].append({
                'type': vtype,
                'text': pattern.format(topic),
            })

    if 'intro' in types:
        for vtype, pattern in _INTRO_PATTERNS.items():
            result['intro_variants'].append({
                'type': vtype,
                'text': pattern.format(topic),
            })

    if 'cta' in types:
        for vtype, text in _CTA_PATTERNS.items():
            result['cta_variants'].append({
                'type': vtype,
                'text': text,
            })

    result['total'] = (len(result['title_variants']) +
                       len(result['intro_variants']) +
                       len(result['cta_variants']))
    return result


def get_variant_types() -> dict:
    """사용 가능한 변형 유형 목록."""
    return {
        'title': list(_TITLE_PATTERNS.keys()),
        'intro': list(_INTRO_PATTERNS.keys()),
        'cta': list(_CTA_PATTERNS.keys()),
    }
