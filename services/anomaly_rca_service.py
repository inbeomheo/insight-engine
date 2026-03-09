"""
이상 탐지 근본 원인 분석 (RCA) 서비스

이상(anomaly) 데이터를 받아 근본 원인을 추정하고,
각 원인의 확률과 증거를 포함한 분석 보고서를 생성합니다.
규칙 기반 (AI API 호출 없음).
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class RootCause:
    """개별 근본 원인"""
    cause: str
    probability: float
    evidence: List[str] = field(default_factory=list)
    category: str = ""


@dataclass
class RCAReport:
    """근본 원인 분석 보고서"""
    anomaly_type: str
    root_causes: List[RootCause] = field(default_factory=list)
    confidence: float = 0.0
    recommended_fix: str = ""


# ── 이상 유형별 원인 규칙 ──
_ANOMALY_RULES: Dict[str, List[dict]] = {
    "spike": [
        {
            "cause": "트래픽 급증 (바이럴/외부 유입)",
            "category": "traffic",
            "check": lambda d: d.get("traffic_change", 0) > 100,
            "evidence_fn": lambda d: f"트래픽 변화율: +{d.get('traffic_change', 0)}%",
        },
        {
            "cause": "봇/크롤러 비정상 접근",
            "category": "security",
            "check": lambda d: d.get("bot_ratio", 0) > 0.5,
            "evidence_fn": lambda d: f"봇 비율: {d.get('bot_ratio', 0) * 100:.0f}%",
        },
        {
            "cause": "캠페인/프로모션 효과",
            "category": "marketing",
            "check": lambda d: d.get("campaign_active", False),
            "evidence_fn": lambda _: "활성 캠페인 존재",
        },
    ],
    "drop": [
        {
            "cause": "서버 장애/다운타임",
            "category": "infrastructure",
            "check": lambda d: d.get("error_rate", 0) > 0.1,
            "evidence_fn": lambda d: f"에러율: {d.get('error_rate', 0) * 100:.1f}%",
        },
        {
            "cause": "콘텐츠 품질 저하",
            "category": "content",
            "check": lambda d: d.get("bounce_rate", 0) > 0.7,
            "evidence_fn": lambda d: f"이탈률: {d.get('bounce_rate', 0) * 100:.0f}%",
        },
        {
            "cause": "SEO 순위 하락",
            "category": "seo",
            "check": lambda d: d.get("ranking_change", 0) < -5,
            "evidence_fn": lambda d: f"순위 변동: {d.get('ranking_change', 0)}",
        },
        {
            "cause": "경쟁사 콘텐츠 상승",
            "category": "competition",
            "check": lambda d: d.get("competitor_growth", 0) > 20,
            "evidence_fn": lambda d: f"경쟁사 성장률: +{d.get('competitor_growth', 0)}%",
        },
    ],
    "anomaly": [
        {
            "cause": "데이터 수집 오류",
            "category": "data",
            "check": lambda d: d.get("missing_data_pct", 0) > 0.1,
            "evidence_fn": lambda d: f"데이터 누락률: {d.get('missing_data_pct', 0) * 100:.1f}%",
        },
        {
            "cause": "계절적/주기적 패턴",
            "category": "pattern",
            "check": lambda d: d.get("is_seasonal", False),
            "evidence_fn": lambda _: "계절적 패턴 감지",
        },
        {
            "cause": "외부 이벤트 영향",
            "category": "external",
            "check": lambda d: d.get("external_event", False),
            "evidence_fn": lambda _: "외부 이벤트(뉴스/이슈) 감지",
        },
    ],
}


def _infer_anomaly_type(anomaly_data: dict) -> str:
    """anomaly_data에서 이상 유형을 추론합니다."""
    # 명시적 타입이 있으면 사용
    explicit = anomaly_data.get("anomaly_type", "")
    if explicit in _ANOMALY_RULES:
        return explicit

    # metric_change 기반 추론
    change = anomaly_data.get("metric_change", 0)
    if change > 0:
        return "spike"
    if change < 0:
        return "drop"
    return "anomaly"


def _evaluate_rules(anomaly_data: dict, rules: List[dict]) -> List[RootCause]:
    """규칙 리스트를 평가하여 매칭되는 근본 원인을 반환합니다."""
    causes: List[RootCause] = []
    for rule in rules:
        try:
            matched = rule["check"](anomaly_data)
        except (KeyError, TypeError, ValueError):
            matched = False

        if matched:
            evidence = []
            try:
                ev = rule["evidence_fn"](anomaly_data)
                if ev:
                    evidence.append(ev)
            except (KeyError, TypeError, ValueError):
                pass

            # 확률은 매칭 강도에 비례 (간단한 규칙: 매칭 시 0.6 기본)
            causes.append(RootCause(
                cause=rule["cause"],
                probability=0.6,
                evidence=evidence,
                category=rule.get("category", "unknown"),
            ))

    return causes


def _adjust_probabilities(causes: List[RootCause]) -> None:
    """원인 간 확률을 정규화하고 조정합니다 (합계 1.0 이하)."""
    if not causes:
        return

    total = sum(c.probability for c in causes)
    if total > 1.0:
        for c in causes:
            c.probability = round(c.probability / total, 3)
    else:
        for c in causes:
            c.probability = round(c.probability, 3)


def _generate_fix(causes: List[RootCause], anomaly_type: str) -> str:
    """최상위 원인에 대한 권장 조치를 생성합니다."""
    if not causes:
        return "추가 데이터 수집 후 재분석 필요"

    top = causes[0]
    fix_map = {
        "traffic": "트래픽 소스를 분석하고 서버 스케일링 검토",
        "security": "봇 차단 규칙 추가 및 WAF 설정 강화",
        "marketing": "캠페인 효과 측정 후 최적화",
        "infrastructure": "서버 상태 점검 및 장애 복구",
        "content": "이탈률 높은 페이지 콘텐츠 개선",
        "seo": "SEO 감사 실행 및 핵심 키워드 재최적화",
        "competition": "경쟁사 콘텐츠 분석 후 차별화 전략 수립",
        "data": "데이터 파이프라인 점검 및 누락 원인 파악",
        "pattern": "계절적 패턴에 맞춘 콘텐츠 일정 조정",
        "external": "외부 이벤트 모니터링 강화 및 대응 콘텐츠 준비",
    }
    return fix_map.get(top.category, f"'{top.cause}' 관련 상세 조사 필요")


def root_cause_analysis(anomaly_data: dict) -> RCAReport:
    """이상 데이터를 분석하여 근본 원인 보고서를 생성합니다.

    Args:
        anomaly_data: 이상 데이터 dict. 최소 하나의 메트릭 포함.
            - anomaly_type (선택): "spike", "drop", "anomaly"
            - metric_change (선택): 메트릭 변화량
            - 기타: traffic_change, error_rate, bounce_rate 등 규칙별 필드

    Returns:
        RCAReport 근본 원인 분석 보고서
    """
    if not anomaly_data:
        return RCAReport(
            anomaly_type="unknown",
            root_causes=[],
            confidence=0.0,
            recommended_fix="분석할 데이터가 없습니다",
        )

    anomaly_type = _infer_anomaly_type(anomaly_data)

    # 해당 유형 규칙 + 범용(anomaly) 규칙 평가
    rules = list(_ANOMALY_RULES.get(anomaly_type, []))
    if anomaly_type != "anomaly":
        rules.extend(_ANOMALY_RULES.get("anomaly", []))

    causes = _evaluate_rules(anomaly_data, rules)

    # 확률 정규화
    _adjust_probabilities(causes)

    # 확률 내림차순 정렬
    causes.sort(key=lambda c: c.probability, reverse=True)

    # 전체 신뢰도 (매칭된 원인 수와 확률 기반)
    if causes:
        confidence = round(min(1.0, sum(c.probability for c in causes) * 1.2), 3)
    else:
        confidence = 0.1

    fix = _generate_fix(causes, anomaly_type)

    return RCAReport(
        anomaly_type=anomaly_type,
        root_causes=causes,
        confidence=confidence,
        recommended_fix=fix,
    )
