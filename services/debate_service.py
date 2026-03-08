"""
AI 토론/다각적 관점 생성 서비스

주제에 대한 찬성/반대/중립 관점을 균형 있게 생성합니다.
규칙 기반 프레임워크 + 입력 텍스트 분석으로 관점을 구성합니다.
"""
import re
import logging

logger = logging.getLogger(__name__)

# 관점 프레임워크
_PERSPECTIVE_FRAMES = {
    'pro': {
        'label': '찬성',
        'starters': [
            '{topic}은(는) 여러 면에서 긍정적인 영향을 미칩니다.',
            '{topic}을(를) 지지하는 핵심 근거가 있습니다.',
            '{topic}의 장점은 다음과 같습니다.',
        ],
        'angle': '장점, 기회, 성공 사례, 효율성, 혁신',
    },
    'con': {
        'label': '반대',
        'starters': [
            '{topic}에 대해 신중하게 접근해야 하는 이유가 있습니다.',
            '{topic}의 잠재적 위험과 한계를 살펴봐야 합니다.',
            '{topic}에 대한 비판적 시각도 존재합니다.',
        ],
        'angle': '위험, 비용, 부작용, 한계, 윤리적 문제',
    },
    'neutral': {
        'label': '중립/균형',
        'starters': [
            '{topic}은(는) 맥락에 따라 다른 결과를 가져옵니다.',
            '{topic}에 대해 양측의 관점을 종합하면 다음과 같습니다.',
            '{topic}의 영향은 조건과 상황에 따라 달라집니다.',
        ],
        'angle': '조건부 효과, 트레이드오프, 맥락 의존성',
    },
}


_EMPTY_RESULT = {
    'topic': '',
    'perspectives': [],
    'discussion_questions': [],
    'conclusion': '',
}


def generate_debate(topic: str, content: str = '') -> dict:
    """주제에 대한 다각적 관점을 생성합니다.

    Args:
        topic: 토론 주제
        content: 관련 콘텐츠 (선택, 분석 정보 보강용)

    Returns:
        {
            "topic": str,
            "perspectives": [
                {
                    "stance": "pro" | "con" | "neutral",
                    "label": str,
                    "summary": str,
                    "key_points": list[str],
                    "considerations": str,
                }
            ],
            "discussion_questions": list[str],
            "conclusion": str,
        }
    """
    if not topic or not topic.strip():
        return dict(_EMPTY_RESULT)

    topic = topic.strip()
    content_points = _extract_points(content) if content else []

    return {
        'topic': topic,
        'perspectives': [
            _build_perspective(topic, stance, content_points)
            for stance in ('pro', 'con', 'neutral')
        ],
        'discussion_questions': _generate_questions(topic),
        'conclusion': _generate_conclusion(topic),
    }


def _build_perspective(topic: str, stance: str, content_points: list) -> dict:
    """특정 관점의 논거를 구성합니다."""
    frame = _PERSPECTIVE_FRAMES[stance]
    label = frame['label']

    # 도입문 선택 (topic 해시 기반 결정적)
    idx = hash(topic + stance) % len(frame['starters'])
    summary = frame['starters'][idx].format(topic=topic)

    # 핵심 논점 생성
    key_points = _generate_key_points(topic, stance, content_points)

    # 고려사항
    considerations = _generate_considerations(topic, stance)

    return {
        'stance': stance,
        'label': label,
        'summary': summary,
        'key_points': key_points,
        'considerations': considerations,
    }


def _generate_key_points(topic: str, stance: str, content_points: list) -> list:
    """관점별 핵심 논점을 생성합니다."""
    points_map = {
        'pro': [
            f'{topic}은(는) 효율성과 생산성을 크게 향상시킬 수 있습니다.',
            f'기존 방식 대비 비용 절감과 시간 단축 효과가 있습니다.',
            f'글로벌 트렌드에 부합하며 경쟁력 확보에 유리합니다.',
            f'사용자/고객 경험을 개선하는 데 기여합니다.',
        ],
        'con': [
            f'{topic}의 도입에는 초기 비용과 학습 곡선이 존재합니다.',
            f'보안, 프라이버시, 윤리적 우려가 있을 수 있습니다.',
            f'기존 시스템과의 호환성 문제가 발생할 수 있습니다.',
            f'과도한 의존은 장기적 리스크를 초래할 수 있습니다.',
        ],
        'neutral': [
            f'{topic}의 효과는 도입 규모와 맥락에 따라 크게 달라집니다.',
            f'장단점 모두 존재하며, 구체적 요구사항에 따른 평가가 필요합니다.',
            f'단기적 비용과 장기적 이익 간의 트레이드오프를 고려해야 합니다.',
            f'성공적 활용을 위해서는 적절한 가이드라인과 교육이 필수적입니다.',
        ],
    }

    points = points_map.get(stance, [])

    # 콘텐츠 포인트 반영 (있으면 첫 번째로 추가)
    if content_points and stance == 'pro':
        points = [f'본문에 따르면: {content_points[0]}'] + points
    elif content_points and stance == 'con' and len(content_points) > 1:
        points = [f'본문의 관점을 비판적으로 보면: {content_points[1]}'] + points

    return points[:4]


def _generate_considerations(topic: str, stance: str) -> str:
    """관점별 추가 고려사항."""
    considerations = {
        'pro': f'이 관점은 {topic}의 긍정적 측면에 초점을 맞추며, 실제 적용 시 맥락과 조건을 고려해야 합니다.',
        'con': f'이 관점은 잠재적 위험을 강조하며, 모든 상황에 일반화할 수는 없습니다.',
        'neutral': f'균형 잡힌 판단을 위해 추가 데이터와 사례 연구가 필요합니다.',
    }
    return considerations.get(stance, '')


def _generate_questions(topic: str) -> list:
    """토론용 질문을 생성합니다."""
    return [
        f'{topic}이(가) 우리 사회/산업에 미칠 가장 큰 영향은 무엇일까요?',
        f'{topic}의 부정적 측면을 최소화하려면 어떤 조치가 필요할까요?',
        f'5년 후 {topic}의 위치는 어떻게 변할까요?',
    ]


def _generate_conclusion(topic: str) -> str:
    """균형 잡힌 결론을 생성합니다."""
    return (
        f'{topic}에 대한 다양한 관점을 살펴보았습니다. '
        f'어떤 입장이든 근거에 기반한 판단이 중요하며, '
        f'열린 태도로 다른 관점을 수용하는 것이 건설적인 논의의 출발점입니다.'
    )


def _extract_points(content: str) -> list:
    """콘텐츠에서 핵심 문장을 추출합니다."""
    if not content:
        return []

    # 마크다운 제거
    plain = re.sub(r'#{1,6}\s+', '', content)
    plain = re.sub(r'\*\*(.+?)\*\*', r'\1', plain)
    plain = re.sub(r'```[\s\S]*?```', '', plain)

    sentences = re.split(r'[.!。]\s*|\n+', plain)
    points = [s.strip() for s in sentences if 15 <= len(s.strip()) <= 100]

    return points[:5]
