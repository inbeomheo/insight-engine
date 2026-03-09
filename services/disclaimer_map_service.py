"""
면책 맵 서비스

콘텐츠에서 가격/성능 약속/보증/비교 주장 등 면책 고지가 필요한
트리거를 탐지하고, 적절한 고지문을 매핑·삽입합니다.
순수 파이썬, AI API 호출 없음.
"""
import re
from dataclasses import dataclass
from typing import List


@dataclass
class DisclaimerTrigger:
    """면책 트리거 데이터."""
    trigger_text: str
    trigger_type: str  # "price", "performance", "guarantee", "comparison"
    disclaimer_text: str
    position: int
    severity: str  # "low", "medium", "high"


# ── 가격 관련 패턴 ──
_PRICE_PATTERNS = [
    (re.compile(r'(?:할인|세일|특가|프로모션)\s*\d*\s*%?', re.IGNORECASE), 'high'),
    (re.compile(r'(?:무료|0원|공짜|무상)', re.IGNORECASE), 'high'),
    (re.compile(r'\d[\d,]*\s*원', re.IGNORECASE), 'medium'),
    (re.compile(r'\$\d[\d,.]*', re.IGNORECASE), 'medium'),
    (re.compile(r'(?:가격|비용|요금|월\s*\d)', re.IGNORECASE), 'low'),
]

_PRICE_DISCLAIMER = '※ 표시된 가격은 변동될 수 있으며, 특정 조건에서만 적용될 수 있습니다. 자세한 내용은 판매처를 확인하세요.'


# ── 성능 관련 패턴 ──
_PERFORMANCE_PATTERNS = [
    (re.compile(r'(?:성능|속도|효율)\s*(?:\d+\s*(?:%|배|배\s*이상))', re.IGNORECASE), 'high'),
    (re.compile(r'(?:향상|개선|증가)\s*(?:\d+\s*(?:%|배))', re.IGNORECASE), 'high'),
    (re.compile(r'(?:빠른|빠르게|고성능|고효율)', re.IGNORECASE), 'low'),
    (re.compile(r'\b\d+x\s*(?:faster|better|improved)\b', re.IGNORECASE), 'high'),
    (re.compile(r'\b(?:performance|speed|efficiency)\s*(?:boost|gain|improvement)\b', re.IGNORECASE), 'medium'),
]

_PERFORMANCE_DISCLAIMER = '※ 성능 수치는 특정 테스트 환경 기준이며, 실제 사용 환경에 따라 차이가 있을 수 있습니다.'


# ── 보증 관련 패턴 ──
_GUARANTEE_PATTERNS = [
    (re.compile(r'(?:100%\s*(?:보장|만족|환불|성공))', re.IGNORECASE), 'high'),
    (re.compile(r'(?:보장합니다|보증합니다|약속합니다)', re.IGNORECASE), 'high'),
    (re.compile(r'(?:확실|반드시|절대|틀림없)', re.IGNORECASE), 'medium'),
    (re.compile(r'\b(?:guarantee|warrant|assured|certain)\b', re.IGNORECASE), 'medium'),
    (re.compile(r'(?:환불\s*(?:가능|보장|약속))', re.IGNORECASE), 'high'),
]

_GUARANTEE_DISCLAIMER = '※ 보증 및 약속은 특정 조건 하에 적용됩니다. 상세 약관을 확인하세요.'


# ── 비교 관련 패턴 ──
_COMPARISON_PATTERNS = [
    (re.compile(r'(?:(?:보다|대비)\s*(?:우수|뛰어|좋|나은|빠른))', re.IGNORECASE), 'medium'),
    (re.compile(r'(?:업계\s*(?:최고|최초|유일|선두))', re.IGNORECASE), 'high'),
    (re.compile(r'(?:1위|넘버\s*원|No\.\s*1)', re.IGNORECASE), 'high'),
    (re.compile(r'\b(?:(?:better|superior|leading|#1|number\s*one)\s+(?:than|in|among))\b', re.IGNORECASE), 'high'),
    (re.compile(r'(?:경쟁\s*(?:사|제품|업체).*?(?:보다|대비|비해))', re.IGNORECASE), 'medium'),
]

_COMPARISON_DISCLAIMER = '※ 비교 주장은 특정 기준 및 시점에 따른 것이며, 모든 상황에 일반화될 수 없습니다.'


# ── 트리거 타입 → (패턴 목록, 면책 문구) 매핑 ──
_TRIGGER_MAP = {
    'price': (_PRICE_PATTERNS, _PRICE_DISCLAIMER),
    'performance': (_PERFORMANCE_PATTERNS, _PERFORMANCE_DISCLAIMER),
    'guarantee': (_GUARANTEE_PATTERNS, _GUARANTEE_DISCLAIMER),
    'comparison': (_COMPARISON_PATTERNS, _COMPARISON_DISCLAIMER),
}


def map_disclaimers(content: str) -> List[DisclaimerTrigger]:
    """콘텐츠에서 면책 고지가 필요한 트리거를 탐지합니다.

    Args:
        content: 분석할 콘텐츠

    Returns:
        DisclaimerTrigger 목록 (position 순 정렬)
    """
    if not content or not content.strip():
        return []

    triggers = []
    seen_texts = set()

    for trigger_type, (patterns, disclaimer) in _TRIGGER_MAP.items():
        for pattern, severity in patterns:
            for m in pattern.finditer(content):
                text = m.group().strip()
                # 동일 텍스트 중복 방지
                key = (text.lower(), trigger_type)
                if key in seen_texts:
                    continue
                seen_texts.add(key)

                triggers.append(DisclaimerTrigger(
                    trigger_text=text,
                    trigger_type=trigger_type,
                    disclaimer_text=disclaimer,
                    position=m.start(),
                    severity=severity,
                ))

    # position 순 정렬
    triggers.sort(key=lambda t: t.position)
    return triggers


def insert_mapped_disclaimers(
    content: str,
    triggers: List[DisclaimerTrigger],
) -> str:
    """탐지된 트리거에 대한 고지문을 콘텐츠 하단에 삽입합니다.

    각 trigger_type별로 하나의 면책 문구만 삽입 (중복 방지).

    Args:
        content: 원본 콘텐츠
        triggers: map_disclaimers()로 탐지된 트리거 목록

    Returns:
        고지문이 삽입된 콘텐츠
    """
    if not content or not triggers:
        return content or ''

    # trigger_type별 중복 제거 (가장 높은 severity 우선)
    severity_order = {'high': 0, 'medium': 1, 'low': 2}
    best_per_type: dict[str, DisclaimerTrigger] = {}

    for t in triggers:
        existing = best_per_type.get(t.trigger_type)
        if existing is None or severity_order.get(t.severity, 9) < severity_order.get(existing.severity, 9):
            best_per_type[t.trigger_type] = t

    # 면책 문구 수집 (중복 텍스트 방지)
    disclaimers = []
    seen_disclaimers = set()
    for t in best_per_type.values():
        if t.disclaimer_text not in seen_disclaimers:
            seen_disclaimers.add(t.disclaimer_text)
            disclaimers.append(t.disclaimer_text)

    if not disclaimers:
        return content

    disclaimer_block = '\n\n---\n' + '\n'.join(disclaimers)
    return content.rstrip() + disclaimer_block
