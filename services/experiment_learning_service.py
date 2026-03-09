"""
실험 학습 루프 서비스

A/B 실험 결과를 분석하여 재사용 가능한 학습 규칙을 추출하고,
누적된 규칙 히스토리를 관리합니다.
"""
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ── 데이터 모델 ──────────────────────────────────────────────

@dataclass
class ExperimentInput:
    """A/B 실험 입력 데이터"""
    experiment_id: str
    variant_a: str
    variant_b: str
    winner: str           # "a" 또는 "b"
    metric: str           # 예: "ctr", "engagement", "conversion"
    improvement: float    # 0~1 범위 (0.15 = 15% 개선)


@dataclass
class LearningRule:
    """실험에서 추출한 학습 규칙"""
    rule_id: str
    pattern: str              # 발견된 패턴 설명
    recommendation: str       # 권장 행동
    confidence: float         # 0~1 범위
    source_experiments: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ── 인메모리 학습 저장소 ──────────────────────────────────────

_learning_store: list[LearningRule] = []


# ── 패턴 감지 규칙 ───────────────────────────────────────────

# 메트릭별 패턴 키워드 → 패턴 설명 + 권장 행동
_METRIC_PATTERNS: dict[str, dict[str, str]] = {
    "ctr": {
        "pattern": "클릭률(CTR) 기반 승자 패턴 감지",
        "recommendation": "제목과 썸네일에서 승리 변형의 요소를 우선 적용하세요.",
    },
    "engagement": {
        "pattern": "참여율 기반 승자 패턴 감지",
        "recommendation": "콘텐츠 구조와 톤에서 승리 변형의 스타일을 채택하세요.",
    },
    "conversion": {
        "pattern": "전환율 기반 승자 패턴 감지",
        "recommendation": "CTA 위치와 문구에서 승리 변형을 기준으로 삼으세요.",
    },
    "retention": {
        "pattern": "유지율 기반 승자 패턴 감지",
        "recommendation": "도입부와 흐름 구성에서 승리 변형의 방식을 따르세요.",
    },
}

# 개선 폭에 따른 신뢰도 매핑 (구간 하한, 신뢰도)
_CONFIDENCE_THRESHOLDS: list[tuple[float, float]] = [
    (0.3, 0.95),   # 30%+ 개선 → 매우 높은 신뢰도
    (0.15, 0.80),  # 15%+ 개선 → 높은 신뢰도
    (0.05, 0.60),  # 5%+ 개선 → 중간 신뢰도
    (0.0, 0.40),   # 5% 미만 → 낮은 신뢰도
]


def _compute_confidence(improvement: float) -> float:
    """개선 폭에 기반한 신뢰도 산출."""
    clamped = max(0.0, min(1.0, improvement))
    for threshold, confidence in _CONFIDENCE_THRESHOLDS:
        if clamped >= threshold:
            return confidence
    return 0.40


def _generate_summary(experiment: ExperimentInput) -> str:
    """실험 결과를 자연어 요약 문장으로 변환."""
    winner_label = "A" if experiment.winner == "a" else "B"
    winner_variant = experiment.variant_a if experiment.winner == "a" else experiment.variant_b
    loser_variant = experiment.variant_b if experiment.winner == "a" else experiment.variant_a
    pct = round(experiment.improvement * 100, 1)

    return (
        f"실험 '{experiment.experiment_id}'에서 "
        f"변형 {winner_label}('{winner_variant}')이(가) "
        f"'{loser_variant}' 대비 {experiment.metric} 지표에서 "
        f"{pct}% 개선되었습니다."
    )


def _find_matching_pattern(metric: str) -> dict[str, str]:
    """메트릭에 맞는 패턴 템플릿을 반환. 미등록 메트릭은 범용 패턴 사용."""
    return _METRIC_PATTERNS.get(metric, {
        "pattern": f"'{metric}' 지표 기반 승자 패턴 감지",
        "recommendation": f"'{metric}' 지표에서 승리한 변형의 요소를 우선 적용하세요.",
    })


def _merge_if_duplicate(new_rule: LearningRule) -> bool:
    """동일 패턴의 기존 규칙이 있으면 실험 ID를 병합하고 신뢰도를 갱신.

    Returns:
        True: 병합 완료 (새 규칙 추가 불필요)
        False: 병합 대상 없음 (새 규칙 추가 필요)
    """
    for existing in _learning_store:
        if existing.pattern == new_rule.pattern:
            # 실험 ID 병합 (중복 방지)
            for exp_id in new_rule.source_experiments:
                if exp_id not in existing.source_experiments:
                    existing.source_experiments.append(exp_id)
            # 반복 확인 시 신뢰도 상승 (최대 1.0)
            existing.confidence = min(1.0, max(existing.confidence, new_rule.confidence) + 0.05)
            logger.info("기존 규칙 '%s'에 실험 병합 (신뢰도: %.2f)", existing.rule_id, existing.confidence)
            return True
    return False


# ── 공개 API ─────────────────────────────────────────────────

def learn_from_experiment(result: dict) -> LearningRule:
    """실험 결과에서 학습 규칙을 추출합니다.

    Args:
        result: 실험 결과 딕셔너리. 필수 키:
            experiment_id, variant_a, variant_b, winner, metric, improvement

    Returns:
        추출된 (또는 병합된) LearningRule

    Raises:
        ValueError: 필수 필드 누락 또는 값 범위 초과 시
    """
    # 필수 필드 검증
    required = {"experiment_id", "variant_a", "variant_b", "winner", "metric", "improvement"}
    missing = required - set(result.keys())
    if missing:
        raise ValueError(f"필수 필드 누락: {missing}")

    # winner 값 검증
    if result["winner"] not in ("a", "b"):
        raise ValueError(f"winner는 'a' 또는 'b'여야 합니다. 받은 값: '{result['winner']}'")

    # improvement 범위 검증
    improvement = result["improvement"]
    if not isinstance(improvement, (int, float)):
        raise ValueError(f"improvement는 숫자여야 합니다. 받은 타입: {type(improvement).__name__}")
    if improvement < 0 or improvement > 1:
        raise ValueError(f"improvement는 0~1 범위여야 합니다. 받은 값: {improvement}")

    experiment = ExperimentInput(**{k: result[k] for k in required})
    pattern_info = _find_matching_pattern(experiment.metric)
    confidence = _compute_confidence(experiment.improvement)
    summary = _generate_summary(experiment)

    rule = LearningRule(
        rule_id=f"rule-{uuid.uuid4().hex[:8]}",
        pattern=pattern_info["pattern"],
        recommendation=f"{pattern_info['recommendation']} | {summary}",
        confidence=confidence,
        source_experiments=[experiment.experiment_id],
    )

    # 중복 패턴 병합 시도
    if _merge_if_duplicate(rule):
        # 병합된 기존 규칙 반환
        for existing in _learning_store:
            if existing.pattern == rule.pattern:
                return existing

    _learning_store.append(rule)
    logger.info("새 학습 규칙 생성: %s (신뢰도: %.2f)", rule.rule_id, rule.confidence)
    return rule


def get_learning_history() -> list[LearningRule]:
    """누적 학습 규칙 목록을 반환합니다.

    Returns:
        신뢰도 내림차순 정렬된 LearningRule 리스트 (복사본)
    """
    return sorted(_learning_store, key=lambda r: r.confidence, reverse=True)


def clear_learning_history() -> int:
    """학습 저장소를 초기화합니다. (테스트용)

    Returns:
        삭제된 규칙 수
    """
    count = len(_learning_store)
    _learning_store.clear()
    return count
