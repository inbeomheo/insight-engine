"""
관할권 렌더러 서비스.

지역별 법규에 따라 콘텐츠에 면책조항을 추가하고 차단 콘텐츠를 제거한다.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class JurisdictionRule:
    """관할권 규칙."""
    jurisdiction: str  # EU / US / KR / JP / global
    content_type: str
    required_disclaimers: list  # list[str]
    blocked_content: list  # list[str] — 차단 키워드
    age_gate: bool = False


def get_applicable_rules(
    jurisdiction: str,
    content_type: str,
    rules: list,
) -> list:
    """해당 관할권과 콘텐츠 유형에 적용되는 규칙을 필터링한다.

    'global' 관할권 규칙은 항상 포함된다.
    """
    applicable = []
    for rule in rules:
        jurisdiction_match = (
            rule.jurisdiction == jurisdiction or rule.jurisdiction == "global"
        )
        type_match = (
            rule.content_type == content_type or rule.content_type == "*"
        )
        if jurisdiction_match and type_match:
            applicable.append(rule)
    return applicable


def render_for_jurisdiction(
    content: dict,
    jurisdiction: str,
    rules: list,
) -> dict:
    """관할권별로 콘텐츠를 렌더링한다.

    - 면책조항 추가
    - 차단 콘텐츠 제거
    - 연령 확인 필요 시 age_gate 플래그 추가
    """
    content_type = content.get("type", "general")
    text = content.get("text", "")

    applicable = get_applicable_rules(jurisdiction, content_type, rules)

    # 면책조항 수집
    disclaimers = []
    needs_age_gate = False
    blocked_keywords = []

    for rule in applicable:
        disclaimers.extend(rule.required_disclaimers)
        blocked_keywords.extend(rule.blocked_content)
        if rule.age_gate:
            needs_age_gate = True

    # 중복 면책조항 제거 (순서 유지)
    seen = set()
    unique_disclaimers = []
    for d in disclaimers:
        if d not in seen:
            seen.add(d)
            unique_disclaimers.append(d)

    # 차단 콘텐츠 제거
    filtered_text = text
    for keyword in blocked_keywords:
        filtered_text = filtered_text.replace(keyword, "[BLOCKED]")

    result = {
        **content,
        "text": filtered_text,
        "disclaimers": unique_disclaimers,
        "jurisdiction": jurisdiction,
    }

    if needs_age_gate:
        result["age_gate"] = True

    return result


def check_compliance(content: dict, rules: list) -> list:
    """콘텐츠의 준수 위반 사항 목록을 반환한다."""
    violations = []
    text = content.get("text", "")

    for rule in rules:
        for keyword in rule.blocked_content:
            if keyword in text:
                violations.append(
                    f"[{rule.jurisdiction}] 차단 콘텐츠 포함: '{keyword}'"
                )

    return violations


def add_age_gate(content: dict, jurisdiction: str) -> dict:
    """연령 확인 메타데이터를 추가한다."""
    age_requirements = {
        "EU": 16,
        "US": 13,
        "KR": 14,
        "JP": 13,
    }
    min_age = age_requirements.get(jurisdiction, 13)

    return {
        **content,
        "age_gate": True,
        "min_age": min_age,
        "age_gate_message": f"이 콘텐츠는 {min_age}세 이상만 이용 가능합니다",
        "jurisdiction": jurisdiction,
    }
