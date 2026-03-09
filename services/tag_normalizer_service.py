"""
태그 정규화 서비스 — 비표준 태그를 정규 형태로 변환
"""

import re
from dataclasses import dataclass, field


@dataclass
class TagMapping:
    """태그 매핑 (원본 → 정규화)"""
    original: str
    normalized: str
    confidence: float = 1.0


@dataclass
class NormalizationResult:
    """정규화 결과"""
    tags: list[TagMapping] = field(default_factory=list)
    duplicates_removed: int = 0
    normalized_count: int = 0


# 동의어 매핑 (소문자 키 → 정규 형태)
_SYNONYM_MAP: dict[str, str] = {
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "react.js": "react",
    "reactjs": "react",
    "vue.js": "vue",
    "vuejs": "vue",
    "node.js": "nodejs",
    "next.js": "nextjs",
    "ml": "machine-learning",
    "ai": "artificial-intelligence",
    "dl": "deep-learning",
    "nlp": "natural-language-processing",
    "cv": "computer-vision",
    "db": "database",
    "api": "api",
    "ui": "user-interface",
    "ux": "user-experience",
    "devops": "devops",
    "ci/cd": "ci-cd",
    "k8s": "kubernetes",
}


def normalize_tag(tag: str) -> str:
    """단일 태그 정규화

    규칙: 소문자 변환 → 공백/언더스코어→하이픈 → 특수문자 제거 → 동의어 매핑

    Args:
        tag: 원본 태그

    Returns:
        정규화된 태그
    """
    if not tag.strip():
        return ""

    normalized = tag.strip().lower()

    # 동의어 매핑 (정규화 전 원본 매칭)
    if normalized in _SYNONYM_MAP:
        return _SYNONYM_MAP[normalized]

    # 공백/언더스코어 → 하이픈
    normalized = re.sub(r"[\s_]+", "-", normalized)

    # 허용: 알파벳, 숫자, 하이픈, 한국어/일본어/중국어
    normalized = re.sub(r"[^a-z0-9가-힣ぁ-んァ-ヶ一-龥\-]", "", normalized)

    # 연속 하이픈 제거
    normalized = re.sub(r"-+", "-", normalized)

    # 앞뒤 하이픈 제거
    normalized = normalized.strip("-")

    # 최종 동의어 매핑 체크
    if normalized in _SYNONYM_MAP:
        return _SYNONYM_MAP[normalized]

    return normalized


def normalize_tags(tags: list[str]) -> NormalizationResult:
    """태그 목록 정규화 + 중복 제거

    Args:
        tags: 원본 태그 목록

    Returns:
        정규화 결과 (매핑 목록, 중복 제거 수, 정규화 수)
    """
    mappings: list[TagMapping] = []
    seen: set[str] = set()
    duplicates = 0
    normalized_count = 0

    for tag in tags:
        normalized = normalize_tag(tag)
        if not normalized:
            continue

        if normalized in seen:
            duplicates += 1
            continue

        seen.add(normalized)
        confidence = 1.0 if tag.strip().lower() == normalized else 0.9
        mappings.append(TagMapping(
            original=tag,
            normalized=normalized,
            confidence=confidence,
        ))

        if tag.strip() != normalized:
            normalized_count += 1

    return NormalizationResult(
        tags=mappings,
        duplicates_removed=duplicates,
        normalized_count=normalized_count,
    )


def _edit_distance(a: str, b: str) -> int:
    """레벤슈타인 편집 거리 계산"""
    m, n = len(a), len(b)
    if m == 0:
        return n
    if n == 0:
        return m

    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev = dp[0]
        dp[0] = i
        for j in range(1, n + 1):
            temp = dp[j]
            if a[i - 1] == b[j - 1]:
                dp[j] = prev
            else:
                dp[j] = 1 + min(prev, dp[j], dp[j - 1])
            prev = temp
    return dp[n]


def suggest_canonical(tag: str, known_tags: list[str]) -> str | None:
    """유사 기존 태그 제안 (편집 거리 기반)

    Args:
        tag: 새 태그
        known_tags: 기존 태그 목록

    Returns:
        가장 유사한 기존 태그 또는 None (유사한 것이 없을 때)
    """
    if not tag.strip() or not known_tags:
        return None

    normalized = normalize_tag(tag)
    if not normalized:
        return None

    best_tag: str | None = None
    best_distance = float("inf")

    # 편집 거리 임계값: 태그 길이의 40% 이내
    threshold = max(2, int(len(normalized) * 0.4))

    for known in known_tags:
        known_norm = normalize_tag(known)
        if not known_norm or known_norm == normalized:
            continue
        dist = _edit_distance(normalized, known_norm)
        if dist < best_distance and dist <= threshold:
            best_distance = dist
            best_tag = known

    return best_tag


def merge_tag_sets(sets: list[list[str]]) -> list[str]:
    """여러 태그셋 병합 + 정규화

    Args:
        sets: 태그 목록의 목록

    Returns:
        정규화된 고유 태그 목록
    """
    all_tags: list[str] = []
    for tag_set in sets:
        all_tags.extend(tag_set)

    result = normalize_tags(all_tags)
    return [m.normalized for m in result.tags]
