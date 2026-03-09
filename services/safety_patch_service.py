"""안전 패치 큐 서비스 -- 콘텐츠 안전성 검사 및 패치 생성"""
import re
from dataclasses import dataclass


@dataclass
class SafetyPatch:
    """안전 패치"""
    content_id: str = ""
    patch_type: str = ""         # outdated_link, deprecated_info, policy_change, factual_error
    original_text: str = ""
    patched_text: str = ""
    reason: str = ""


# 만료/위험 패턴 정의
_DEPRECATED_PATTERNS: list[tuple[str, str, str]] = [
    # (정규식 패턴, 패치 유형, 사유)
    (r'http://', "outdated_link", "HTTP 링크는 HTTPS로 전환해야 합니다"),
    (r'(?i)\b(python\s*2\b|python2)', "deprecated_info", "Python 2는 2020년 지원 종료됨"),
    (r'(?i)\b(ie\s*11|internet\s*explorer)', "deprecated_info", "Internet Explorer는 지원 종료됨"),
    (r'(?i)\b(flash\s*player|adobe\s*flash)', "deprecated_info", "Adobe Flash는 2020년 지원 종료됨"),
]

# 사실 오류 패턴 (흔한 잘못된 정보)
_FACTUAL_PATTERNS: list[tuple[str, str, str]] = [
    (r'(?i)지구는?\s*평평', "factual_error", "지구는 구형(타원체)입니다"),
    (r'(?i)만리장성.*우주.*보인', "factual_error", "만리장성은 우주에서 보이지 않습니다"),
]

# 정책 변경 패턴
_POLICY_PATTERNS: list[tuple[str, str, str]] = [
    (r'(?i)(?:무료|free)\s*(?:ssl|https)', "policy_change", "대부분의 호스팅에서 SSL은 기본 제공됩니다"),
]


def _scan_patterns(
    content: str,
    content_id: str,
    patterns: list[tuple[str, str, str]],
) -> list[SafetyPatch]:
    """패턴 목록으로 콘텐츠를 스캔하여 패치를 생성한다."""
    patches: list[SafetyPatch] = []

    for pattern, patch_type, reason in patterns:
        for match in re.finditer(pattern, content):
            original = match.group(0)
            patched = _generate_patch(original, patch_type)

            patches.append(SafetyPatch(
                content_id=content_id,
                patch_type=patch_type,
                original_text=original,
                patched_text=patched,
                reason=reason,
            ))

    return patches


def _generate_patch(original: str, patch_type: str) -> str:
    """원본 텍스트에 대한 패치 텍스트를 생성한다."""
    if patch_type == "outdated_link":
        return original.replace("http://", "https://")

    if patch_type == "deprecated_info":
        return f"[지원 종료] {original}"

    if patch_type == "policy_change":
        return f"[정책 변경] {original}"

    if patch_type == "factual_error":
        return f"[사실 확인 필요] {original}"

    return original


def queue_safety_patches(contents: list[dict]) -> list[SafetyPatch]:
    """콘텐츠 목록의 안전 패치를 생성한다.

    Args:
        contents: [{"id": "post-1", "text": "..."}, ...]

    Returns:
        list[SafetyPatch]
    """
    all_patches: list[SafetyPatch] = []

    for item in contents:
        content_id = str(item.get("id", ""))
        text = str(item.get("text", ""))

        if not text.strip():
            continue

        all_patterns = _DEPRECATED_PATTERNS + _FACTUAL_PATTERNS + _POLICY_PATTERNS
        patches = _scan_patterns(text, content_id, all_patterns)
        all_patches.extend(patches)

    return all_patches
