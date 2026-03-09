"""
브랜드 규칙 기반 자동 교정 서비스

콘텐츠 내 브랜드 표현 오류를 규칙 목록에 따라 자동 교정.
규칙 기반 (AI API 호출 없음).
"""
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Correction:
    """단일 교정 내역."""
    original_text: str
    corrected_text: str
    rule_name: str
    position: int          # 원본 텍스트에서의 시작 위치


@dataclass
class CorrectionResult:
    """교정 결과."""
    original: str
    corrected: str
    corrections: List[Correction]
    correction_count: int


def _find_all_occurrences(text: str, substring: str, case_sensitive: bool = True) -> List[int]:
    """텍스트에서 substring의 모든 위치를 찾습니다."""
    positions = []
    search_text = text if case_sensitive else text.lower()
    search_sub = substring if case_sensitive else substring.lower()
    start = 0
    while True:
        idx = search_text.find(search_sub, start)
        if idx == -1:
            break
        positions.append(idx)
        start = idx + 1
    return positions


def auto_correct_brand(content: str, rules: List[dict]) -> CorrectionResult:
    """브랜드 규칙에 따라 콘텐츠를 자동 교정합니다.

    rules 형식: [{"find": "잘못된 표현", "replace": "올바른 표현", "name": "규칙명"}]
    선택 키: "case_sensitive" (기본 True)

    교정은 원본 텍스트 기준으로 위치를 기록한 뒤,
    뒤쪽부터 치환하여 위치 어긋남을 방지합니다.

    Args:
        content: 교정할 콘텐츠
        rules: 교정 규칙 리스트

    Returns:
        CorrectionResult
    """
    if not content or not content.strip():
        return CorrectionResult(
            original=content or "",
            corrected=content or "",
            corrections=[],
            correction_count=0,
        )

    if not rules:
        return CorrectionResult(
            original=content,
            corrected=content,
            corrections=[],
            correction_count=0,
        )

    # 모든 교정 대상을 수집 (원본 기준 위치)
    all_corrections: List[Correction] = []

    for rule in rules:
        find_text = rule.get('find', '')
        replace_text = rule.get('replace', '')
        rule_name = rule.get('name', '이름 없는 규칙')
        case_sensitive = rule.get('case_sensitive', True)

        if not find_text:
            continue

        positions = _find_all_occurrences(content, find_text, case_sensitive)
        for pos in positions:
            # 원본에서 실제 매칭된 텍스트 추출 (대소문자 무시 시 원본 유지)
            matched_text = content[pos:pos + len(find_text)]
            all_corrections.append(Correction(
                original_text=matched_text,
                corrected_text=replace_text,
                rule_name=rule_name,
                position=pos,
            ))

    if not all_corrections:
        return CorrectionResult(
            original=content,
            corrected=content,
            corrections=[],
            correction_count=0,
        )

    # 위치 역순 정렬 (뒤에서부터 치환하여 위치 어긋남 방지)
    all_corrections.sort(key=lambda c: c.position, reverse=True)

    # 겹치는 교정 제거 (같은 위치에 여러 규칙이 매칭된 경우 첫 번째만)
    seen_positions = set()
    unique_corrections = []
    for corr in all_corrections:
        overlap = False
        for seen_pos, seen_len in seen_positions:
            if not (corr.position + len(corr.original_text) <= seen_pos or
                    corr.position >= seen_pos + seen_len):
                overlap = True
                break
        if not overlap:
            unique_corrections.append(corr)
            seen_positions.add((corr.position, len(corr.original_text)))

    # 뒤에서부터 치환
    corrected = content
    for corr in unique_corrections:
        end = corr.position + len(corr.original_text)
        corrected = corrected[:corr.position] + corr.corrected_text + corrected[end:]

    # 결과 정렬 (위치 오름차순으로 반환)
    unique_corrections.sort(key=lambda c: c.position)

    return CorrectionResult(
        original=content,
        corrected=corrected,
        corrections=unique_corrections,
        correction_count=len(unique_corrections),
    )


def validate_rules(rules: List[dict]) -> List[str]:
    """교정 규칙 목록의 유효성을 검증합니다.

    Args:
        rules: 교정 규칙 리스트

    Returns:
        오류 메시지 리스트 (빈 리스트 = 유효)
    """
    errors = []
    for i, rule in enumerate(rules):
        if not isinstance(rule, dict):
            errors.append(f"규칙 {i}: dict 타입이 아닙니다")
            continue
        if not rule.get('find'):
            errors.append(f"규칙 {i}: 'find' 키가 없거나 비어있습니다")
        if 'replace' not in rule:
            errors.append(f"규칙 {i}: 'replace' 키가 없습니다")
        if not rule.get('name'):
            errors.append(f"규칙 {i}: 'name' 키가 없거나 비어있습니다")
    return errors
