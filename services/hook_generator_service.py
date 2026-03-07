"""
훅(Hook) 문장 생성 서비스

콘텐츠의 주제와 핵심 정보를 분석하여
독자의 관심을 끄는 서두 문장(훅)을 다양한 패턴으로 생성합니다.
AI 호출 없이 규칙 기반 템플릿으로 즉시 생성.
"""
import re
import logging

logger = logging.getLogger(__name__)

# 훅 패턴 템플릿
_HOOK_TEMPLATES = {
    'question': [
        '{topic}에 대해 얼마나 알고 계신가요?',
        '왜 {topic}이(가) 지금 이렇게 중요할까요?',
        '{topic}, 정말 효과가 있을까요?',
    ],
    'statistic': [
        '{stat}이라는 사실을 알고 계셨나요?',
        '최근 조사에 따르면 {stat}.',
        '{stat} — 이 숫자가 의미하는 것은 무엇일까요?',
    ],
    'contrarian': [
        '대부분의 사람들이 {topic}에 대해 잘못 알고 있습니다.',
        '{topic}에 관한 통념은 사실이 아닐 수 있습니다.',
        '많은 전문가들이 {topic}에 대해 틀린 조언을 하고 있습니다.',
    ],
    'story': [
        '{topic}을(를) 시작했을 때, 아무도 결과를 예상하지 못했습니다.',
        '3년 전, {topic}은(는) 완전히 다른 모습이었습니다.',
        '{topic}의 시작은 작은 질문에서 비롯되었습니다.',
    ],
    'promise': [
        '이 글을 읽으면 {topic}에 대한 관점이 달라질 것입니다.',
        '{topic}을(를) 제대로 이해하기 위한 핵심을 정리했습니다.',
        '5분만 투자하면 {topic}의 핵심을 파악할 수 있습니다.',
    ],
    'pain_point': [
        '{topic} 때문에 고민하고 계신가요?',
        '{topic}에서 반복되는 실수를 하고 있진 않나요?',
        '{topic}이(가) 어렵게 느껴지는 이유가 있습니다.',
    ],
}


def generate_hooks(topic: str, content: str = '', count: int = 5) -> dict:
    """주제에 대한 훅 문장을 생성합니다.

    Args:
        topic: 주제 또는 제목
        content: 참고 콘텐츠 (선택, 통계/수치 추출용)
        count: 생성할 훅 수 (기본 5, 최대 12)

    Returns:
        {
            "topic": str,
            "hooks": [
                {
                    "type": str (패턴 유형),
                    "text": str (훅 문장),
                    "effectiveness": str ("high" | "medium"),
                }
            ],
            "total": int,
            "recommendation": str,
        }
    """
    if not topic or not topic.strip():
        return {
            'topic': '',
            'hooks': [],
            'total': 0,
            'recommendation': '',
        }

    topic = topic.strip()
    count = max(1, min(count, 12))

    # 콘텐츠에서 통계/수치 추출
    stats = _extract_stats(content) if content else []

    hooks = []
    for pattern_type, templates in _HOOK_TEMPLATES.items():
        if len(hooks) >= count:
            break

        for template in templates:
            if len(hooks) >= count:
                break

            if '{stat}' in template:
                if stats:
                    text = template.format(stat=stats[0])
                    stats = stats[1:]  # 다음 통계 사용
                else:
                    continue
            else:
                text = template.format(topic=topic)

            effectiveness = _rate_effectiveness(pattern_type)
            hooks.append({
                'type': pattern_type,
                'text': text,
                'effectiveness': effectiveness,
            })

    recommendation = _recommend_best(hooks)

    return {
        'topic': topic,
        'hooks': hooks,
        'total': len(hooks),
        'recommendation': recommendation,
    }


def _extract_stats(content: str) -> list:
    """콘텐츠에서 통계/수치 문구를 추출합니다."""
    if not content:
        return []

    patterns = [
        re.compile(r'[\w\s]{3,15}\s*\d+[%％][\w\s]{0,20}'),
        re.compile(r'\d+[만억]\s*[명원건개][\w\s]{0,15}'),
        re.compile(r'\d+배[\w\s]{0,15}'),
    ]

    stats = []
    for pat in patterns:
        matches = pat.findall(content)
        for m in matches:
            cleaned = m.strip()
            if 5 <= len(cleaned) <= 50:
                stats.append(cleaned)

    return stats[:5]


def _rate_effectiveness(pattern_type: str) -> str:
    """패턴별 효과 등급."""
    high_patterns = {'question', 'statistic', 'pain_point'}
    return 'high' if pattern_type in high_patterns else 'medium'


def _recommend_best(hooks: list) -> str:
    """최적 훅 추천."""
    high_hooks = [h for h in hooks if h['effectiveness'] == 'high']
    if high_hooks:
        return f'"{high_hooks[0]["text"]}" — {high_hooks[0]["type"]} 패턴이 가장 효과적입니다.'
    elif hooks:
        return f'"{hooks[0]["text"]}" — 이 훅으로 시작하는 것을 추천합니다.'
    return ''
