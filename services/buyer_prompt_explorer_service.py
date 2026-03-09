"""
구매자 질문 탐색 서비스

카테고리별 구매 의도 질문을 규칙 기반으로 생성하여
콘텐츠 기획에 활용할 수 있는 프롬프트 목록을 제공합니다.
"""
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class BuyerPrompt:
    """구매자 의도 질문 데이터"""
    question: str
    intent: str          # "comparison" | "review" | "howto" | "price" | "alternative"
    funnel_stage: str    # "awareness" | "consideration" | "decision"
    priority: float      # 0~1

    def to_dict(self) -> dict:
        """딕셔너리 변환"""
        return {
            'question': self.question,
            'intent': self.intent,
            'funnel_stage': self.funnel_stage,
            'priority': round(self.priority, 2),
        }


# 유효한 intent 값
VALID_INTENTS = {'comparison', 'review', 'howto', 'price', 'alternative'}

# 유효한 funnel_stage 값
VALID_FUNNEL_STAGES = {'awareness', 'consideration', 'decision'}

# intent별 질문 템플릿 (카테고리 치환용)
# 각 템플릿: (질문 포맷, funnel_stage, 기본 priority)
_INTENT_TEMPLATES: dict[str, list[tuple[str, str, float]]] = {
    'comparison': [
        ('{category} 추천 순위 비교', 'consideration', 0.9),
        ('{category} vs 경쟁 제품 차이점', 'consideration', 0.85),
        ('{category} 브랜드별 장단점 비교', 'consideration', 0.8),
        ('{category} 가성비 좋은 제품은?', 'decision', 0.75),
    ],
    'review': [
        ('{category} 실사용 후기', 'consideration', 0.9),
        ('{category} 장단점 솔직 리뷰', 'consideration', 0.85),
        ('{category} 사용 후 만족도', 'decision', 0.7),
        ('{category} 내구성 리뷰', 'consideration', 0.65),
    ],
    'howto': [
        ('{category} 고르는 법', 'awareness', 0.95),
        ('{category} 초보자 가이드', 'awareness', 0.9),
        ('{category} 사용법 및 관리 방법', 'awareness', 0.8),
        ('{category} 설치 방법', 'awareness', 0.6),
    ],
    'price': [
        ('{category} 가격대별 추천', 'decision', 0.9),
        ('{category} 최저가 구매 방법', 'decision', 0.85),
        ('{category} 할인 시즌 정보', 'decision', 0.7),
        ('{category} 가격 동향', 'awareness', 0.55),
    ],
    'alternative': [
        ('{category} 대안 제품 추천', 'consideration', 0.85),
        ('{category} 대체할 수 있는 저렴한 옵션', 'consideration', 0.8),
        ('{category} 중고 vs 새제품', 'decision', 0.7),
        ('{category} 비슷한 성능의 다른 브랜드', 'consideration', 0.65),
    ],
}

# funnel_stage별 priority 보정 (높은 단계일수록 전환 가까움)
_FUNNEL_PRIORITY_BOOST: dict[str, float] = {
    'awareness': 0.0,
    'consideration': 0.05,
    'decision': 0.1,
}


def explore_buyer_prompts(
    category: str,
    intents: list[str] | None = None,
    min_priority: float = 0.0,
    max_results: int | None = None,
) -> list[BuyerPrompt]:
    """카테고리별 구매 의도 질문을 규칙 기반으로 생성합니다.

    Args:
        category: 제품/서비스 카테고리 (예: "노트북", "에어컨")
        intents: 포함할 intent 필터 (None이면 전체)
        min_priority: 최소 priority 필터 (0~1)
        max_results: 최대 반환 개수 (None이면 제한 없음)

    Returns:
        BuyerPrompt 목록 (priority 내림차순, 최소 5개 보장)

    Raises:
        ValueError: category가 비어있거나, 유효하지 않은 intent/priority 값
    """
    # 입력 검증
    if not category or not category.strip():
        raise ValueError('category는 비어있을 수 없습니다.')

    category = category.strip()

    if min_priority < 0.0 or min_priority > 1.0:
        raise ValueError(f'min_priority는 0~1 범위여야 합니다: {min_priority}')

    # intent 필터 검증
    target_intents = _resolve_intents(intents)

    # 질문 생성
    prompts = _generate_prompts(category, target_intents)

    # priority 필터 적용 (5개 미만이면 필터 완화)
    filtered = [p for p in prompts if p.priority >= min_priority]
    if len(filtered) < 5:
        # 최소 5개 보장: priority 내림차순으로 상위 5개 복원
        filtered = sorted(prompts, key=lambda p: p.priority, reverse=True)[:max(5, len(filtered))]

    # priority 내림차순 정렬
    filtered.sort(key=lambda p: (-p.priority, p.question))

    # max_results 적용
    if max_results is not None and max_results > 0:
        filtered = filtered[:max_results]

    logger.info(
        '구매자 질문 생성 완료: category=%s, intents=%s, 결과=%d건',
        category, target_intents, len(filtered),
    )

    return filtered


def _resolve_intents(intents: list[str] | None) -> list[str]:
    """intent 필터를 검증하고 확정합니다."""
    if intents is None:
        return list(_INTENT_TEMPLATES.keys())

    if not intents:
        raise ValueError('intents 리스트가 비어있습니다.')

    invalid = set(intents) - VALID_INTENTS
    if invalid:
        raise ValueError(f'유효하지 않은 intent: {invalid}. 허용 값: {VALID_INTENTS}')

    return list(intents)


def _generate_prompts(category: str, intents: list[str]) -> list[BuyerPrompt]:
    """intent 템플릿에서 BuyerPrompt 목록을 생성합니다."""
    prompts: list[BuyerPrompt] = []

    for intent in intents:
        templates = _INTENT_TEMPLATES.get(intent, [])
        for question_fmt, funnel_stage, base_priority in templates:
            # priority에 funnel 보정 적용
            boost = _FUNNEL_PRIORITY_BOOST.get(funnel_stage, 0.0)
            priority = min(1.0, base_priority + boost)

            prompts.append(BuyerPrompt(
                question=question_fmt.format(category=category),
                intent=intent,
                funnel_stage=funnel_stage,
                priority=round(priority, 2),
            ))

    return prompts


def get_prompts_by_funnel(prompts: list[BuyerPrompt]) -> dict[str, list[BuyerPrompt]]:
    """BuyerPrompt 목록을 funnel_stage별로 그룹화합니다.

    Args:
        prompts: BuyerPrompt 목록

    Returns:
        funnel_stage를 키로 하는 딕셔너리
    """
    grouped: dict[str, list[BuyerPrompt]] = {
        'awareness': [],
        'consideration': [],
        'decision': [],
    }

    for prompt in prompts:
        if prompt.funnel_stage in grouped:
            grouped[prompt.funnel_stage].append(prompt)

    # 각 그룹 내 priority 내림차순 정렬
    for stage in grouped:
        grouped[stage].sort(key=lambda p: -p.priority)

    return grouped


def get_prompts_by_intent(prompts: list[BuyerPrompt]) -> dict[str, list[BuyerPrompt]]:
    """BuyerPrompt 목록을 intent별로 그룹화합니다.

    Args:
        prompts: BuyerPrompt 목록

    Returns:
        intent를 키로 하는 딕셔너리
    """
    grouped: dict[str, list[BuyerPrompt]] = {}

    for prompt in prompts:
        if prompt.intent not in grouped:
            grouped[prompt.intent] = []
        grouped[prompt.intent].append(prompt)

    for intent in grouped:
        grouped[intent].sort(key=lambda p: -p.priority)

    return grouped


def format_prompts_markdown(prompts: list[BuyerPrompt]) -> str:
    """BuyerPrompt 목록을 마크다운 형식으로 변환합니다.

    Args:
        prompts: BuyerPrompt 목록

    Returns:
        마크다운 문자열
    """
    if not prompts:
        return ''

    lines = ['# 구매자 질문 탐색 결과', '']

    grouped = get_prompts_by_funnel(prompts)
    stage_labels = {
        'awareness': '인지 단계 (Awareness)',
        'consideration': '고려 단계 (Consideration)',
        'decision': '결정 단계 (Decision)',
    }

    for stage, label in stage_labels.items():
        stage_prompts = grouped.get(stage, [])
        if not stage_prompts:
            continue

        lines.append(f'## {label}')
        lines.append('')
        for p in stage_prompts:
            intent_label = _intent_label(p.intent)
            lines.append(f'- **{p.question}** [{intent_label}] (우선순위: {p.priority:.2f})')
        lines.append('')

    return '\n'.join(lines)


def _intent_label(intent: str) -> str:
    """intent를 한국어 라벨로 변환합니다."""
    labels = {
        'comparison': '비교',
        'review': '리뷰',
        'howto': '방법',
        'price': '가격',
        'alternative': '대안',
    }
    return labels.get(intent, intent)
