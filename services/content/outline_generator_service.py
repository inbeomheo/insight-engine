"""
콘텐츠 아웃라인 자동 생성 서비스

주제와 키워드를 기반으로 구조화된 콘텐츠 아웃라인(H2/H3)을 생성합니다.
규칙 기반 템플릿으로 AI 호출 없이 즉시 생성.
"""
import logging

logger = logging.getLogger(__name__)

# 아웃라인 구조 템플릿
_OUTLINE_TEMPLATES = {
    'guide': {
        'label': '가이드',
        'sections': [
            {'h2': '{topic}이란?', 'h3s': ['정의와 개념', '역사와 배경']},
            {'h2': '{topic}의 주요 특징', 'h3s': ['핵심 기능', '장단점 비교']},
            {'h2': '{topic} 시작하기', 'h3s': ['준비 사항', '단계별 가이드', '주의 사항']},
            {'h2': '실전 활용 사례', 'h3s': ['성공 사례', '실패에서 배우는 교훈']},
            {'h2': '자주 묻는 질문 (FAQ)', 'h3s': []},
            {'h2': '마무리 및 다음 단계', 'h3s': []},
        ],
    },
    'listicle': {
        'label': '리스트형',
        'sections': [
            {'h2': '{topic} 소개', 'h3s': ['왜 중요한가']},
            {'h2': '1. 첫 번째 포인트', 'h3s': ['상세 설명', '적용 방법']},
            {'h2': '2. 두 번째 포인트', 'h3s': ['상세 설명', '적용 방법']},
            {'h2': '3. 세 번째 포인트', 'h3s': ['상세 설명', '적용 방법']},
            {'h2': '4. 네 번째 포인트', 'h3s': ['상세 설명']},
            {'h2': '5. 다섯 번째 포인트', 'h3s': ['상세 설명']},
            {'h2': '결론', 'h3s': []},
        ],
    },
    'comparison': {
        'label': '비교 분석',
        'sections': [
            {'h2': '{topic} 개요', 'h3s': ['비교 배경', '평가 기준']},
            {'h2': '옵션 A 분석', 'h3s': ['특징', '장점', '단점']},
            {'h2': '옵션 B 분석', 'h3s': ['특징', '장점', '단점']},
            {'h2': '직접 비교표', 'h3s': ['기능 비교', '가격 비교', '성능 비교']},
            {'h2': '어떤 것을 선택해야 할까?', 'h3s': ['상황별 추천']},
            {'h2': '결론', 'h3s': []},
        ],
    },
    'tutorial': {
        'label': '튜토리얼',
        'sections': [
            {'h2': '소개', 'h3s': ['목표', '사전 준비물']},
            {'h2': '1단계: 환경 설정', 'h3s': ['필수 도구', '설치 방법']},
            {'h2': '2단계: 기본 구현', 'h3s': ['코드/절차 설명', '예제']},
            {'h2': '3단계: 심화 적용', 'h3s': ['고급 기능', '최적화']},
            {'h2': '문제 해결 (트러블슈팅)', 'h3s': ['자주 발생하는 오류', '해결 방법']},
            {'h2': '마무리', 'h3s': ['요약', '추가 학습 자료']},
        ],
    },
    'opinion': {
        'label': '의견/에세이',
        'sections': [
            {'h2': '도입: {topic}에 대한 나의 관점', 'h3s': []},
            {'h2': '현재 상황 분석', 'h3s': ['데이터와 근거', '주요 이슈']},
            {'h2': '나의 주장', 'h3s': ['근거 1', '근거 2', '근거 3']},
            {'h2': '예상 반론과 답변', 'h3s': []},
            {'h2': '결론 및 제언', 'h3s': []},
        ],
    },
}


_EMPTY_OUTLINE = {
    'topic': '',
    'template': '',
    'template_label': '',
    'outline': [],
    'markdown': '',
    'estimated_word_count': 0,
    'seo_tips': [],
}


def _build_outline_from_template(topic: str, tmpl: dict) -> tuple:
    """템플릿으로부터 아웃라인 구조와 마크다운을 생성합니다.

    Returns:
        (outline, markdown, estimated_word_count)
    """
    outline = []
    md_lines = [f'# {topic}\n']

    for section in tmpl['sections']:
        h2_text = section['h2'].format(topic=topic)
        children = []
        md_lines.append(f'## {h2_text}\n')

        for h3 in section.get('h3s', []):
            children.append({'level': 3, 'text': h3})
            md_lines.append(f'### {h3}\n')

        outline.append({
            'level': 2,
            'text': h2_text,
            'children': children,
        })

    total_sections = sum(1 + len(s.get('h3s', [])) for s in tmpl['sections'])
    return outline, '\n'.join(md_lines), total_sections * 250


def generate_outline(
    topic: str,
    template: str = 'guide',
    keywords: list = None,
) -> dict:
    """주제에 맞는 콘텐츠 아웃라인을 생성합니다.

    Args:
        topic: 콘텐츠 주제
        template: 템플릿 유형 (guide, listicle, comparison, tutorial, opinion)
        keywords: SEO 키워드 리스트 (선택)

    Returns:
        topic, template, outline, markdown, estimated_word_count, seo_tips를 포함하는 dict
    """
    if not topic or not topic.strip():
        return {**_EMPTY_OUTLINE, 'template': template}

    topic = topic.strip()
    if template not in _OUTLINE_TEMPLATES:
        template = 'guide'

    tmpl = _OUTLINE_TEMPLATES[template]
    outline, markdown, estimated = _build_outline_from_template(topic, tmpl)

    return {
        'topic': topic,
        'template': template,
        'template_label': tmpl['label'],
        'outline': outline,
        'markdown': markdown,
        'estimated_word_count': estimated,
        'seo_tips': _generate_seo_tips(topic, keywords or []),
    }


def get_templates() -> list:
    """사용 가능한 아웃라인 템플릿 목록."""
    return [
        {'id': k, 'label': v['label'], 'sections': len(v['sections'])}
        for k, v in _OUTLINE_TEMPLATES.items()
    ]


def _generate_seo_tips(topic: str, keywords: list) -> list:
    tips = [
        f'제목(H1)에 "{topic}" 키워드를 포함하세요.',
        '첫 문단 100자 이내에 핵심 키워드를 배치하세요.',
        'H2 소제목에 관련 키워드를 자연스럽게 포함하세요.',
    ]

    if keywords:
        tips.append(f'타겟 키워드: {", ".join(keywords[:5])}')
        tips.append('키워드를 본문에 2~3% 밀도로 분포시키세요.')

    return tips
