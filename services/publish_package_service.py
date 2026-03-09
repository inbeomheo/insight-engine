"""스키마 고정형 발행 패키지 생성 서비스

본문/메타설명/FAQ/SNS 카피를 타입 고정 스키마로 안전 생성한다.
"""
import json
import re
from dataclasses import dataclass, field


@dataclass
class PublishPackage:
    """발행 패키지 스키마"""
    title: str
    meta_description: str        # 160자 이내
    body_html: str
    faq: list[dict] = field(default_factory=list)        # [{"q": "...", "a": "..."}]
    sns_copies: dict[str, str] = field(default_factory=dict)  # {"twitter": "...", "linkedin": "..."}
    tags: list[str] = field(default_factory=list)
    schema_version: str = "1.0"


@dataclass
class ValidationError:
    """패키지 검증 오류"""
    field: str
    message: str
    severity: str  # "error", "warning"


# SNS 플랫폼별 최대 길이
_SNS_MAX_LENGTHS = {
    "twitter": 280,
    "linkedin": 700,
    "instagram": 2200,
    "threads": 500,
}


def build_package(
    content: str,
    title: str = "",
    tags: list[str] | None = None,
) -> PublishPackage:
    """콘텐츠에서 발행 패키지를 조립한다.

    Args:
        content: 원본 콘텐츠 (마크다운 또는 플레인텍스트)
        title: 제목. 빈 문자열이면 콘텐츠 첫 줄에서 추출.
        tags: 태그 목록. None이면 빈 리스트.

    Returns:
        PublishPackage 인스턴스
    """
    content = content.strip() if content else ""

    # 제목 결정: 명시적 > 첫 줄 추출
    if not title:
        title = _extract_title(content)

    # 메타설명: 첫 160자 (문장 단위 자르기)
    meta_description = _build_meta_description(content)

    # 본문 HTML: 간단한 마크다운 → HTML 변환
    body_html = _content_to_html(content)

    # FAQ: 콘텐츠에서 질문형 문장 추출
    faq = _extract_faq(content)

    # SNS 카피: 플랫폼별 길이 조정
    sns_copies = _build_sns_copies(content, title)

    return PublishPackage(
        title=title,
        meta_description=meta_description,
        body_html=body_html,
        faq=faq,
        sns_copies=sns_copies,
        tags=tags or [],
        schema_version="1.0",
    )


def validate_package(package: PublishPackage) -> list[ValidationError]:
    """발행 패키지 필드별 검증.

    Args:
        package: 검증할 PublishPackage

    Returns:
        ValidationError 목록 (빈 리스트이면 유효)
    """
    errors: list[ValidationError] = []

    # 필수 필드
    if not package.title or not package.title.strip():
        errors.append(ValidationError("title", "제목이 비어 있습니다", "error"))

    if not package.body_html or not package.body_html.strip():
        errors.append(ValidationError("body_html", "본문이 비어 있습니다", "error"))

    # 메타설명 길이
    if len(package.meta_description) > 160:
        errors.append(ValidationError(
            "meta_description",
            f"메타설명이 160자를 초과합니다 ({len(package.meta_description)}자)",
            "error",
        ))
    elif not package.meta_description:
        errors.append(ValidationError(
            "meta_description", "메타설명이 비어 있습니다", "warning",
        ))

    # FAQ 형식
    for i, item in enumerate(package.faq):
        if not isinstance(item, dict):
            errors.append(ValidationError(
                "faq", f"FAQ[{i}]가 딕셔너리가 아닙니다", "error",
            ))
        elif "q" not in item or "a" not in item:
            errors.append(ValidationError(
                "faq", f"FAQ[{i}]에 'q' 또는 'a' 키가 없습니다", "error",
            ))

    # schema_version
    if not package.schema_version:
        errors.append(ValidationError(
            "schema_version", "스키마 버전이 비어 있습니다", "warning",
        ))

    return errors


def export_package(package: PublishPackage, format: str = "json") -> str:
    """패키지를 직렬화하여 내보낸다.

    Args:
        package: 내보낼 PublishPackage
        format: 출력 형식 ("json" 지원)

    Returns:
        직렬화된 문자열

    Raises:
        ValueError: 지원하지 않는 형식
    """
    if format != "json":
        raise ValueError(f"지원하지 않는 형식: '{format}'. 사용 가능: json")

    data = {
        "schema_version": package.schema_version,
        "title": package.title,
        "meta_description": package.meta_description,
        "body_html": package.body_html,
        "faq": package.faq,
        "sns_copies": package.sns_copies,
        "tags": package.tags,
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


# --- 내부 헬퍼 ---

def _extract_title(content: str) -> str:
    """콘텐츠 첫 줄에서 제목 추출."""
    if not content:
        return ""
    first_line = content.split("\n")[0].strip()
    # 마크다운 헤딩 기호 제거
    first_line = re.sub(r"^#+\s*", "", first_line)
    return first_line[:100]  # 제목 최대 100자


def _build_meta_description(content: str) -> str:
    """콘텐츠에서 메타설명 생성 (160자 이내, 문장 단위)."""
    if not content:
        return ""
    # 마크다운 기호 제거
    plain = re.sub(r"[#*_`>\[\]()]", "", content)
    plain = re.sub(r"\n+", " ", plain).strip()

    if len(plain) <= 160:
        return plain

    # 160자 이내에서 마지막 문장 끝 찾기
    truncated = plain[:160]
    last_period = max(
        truncated.rfind("."),
        truncated.rfind("!"),
        truncated.rfind("?"),
        truncated.rfind("다."),
    )
    if last_period > 80:  # 최소 80자 확보
        return truncated[:last_period + 1]
    return truncated[:157] + "..."


def _content_to_html(content: str) -> str:
    """간단한 마크다운 → HTML 변환 (기본 단락 래핑)."""
    if not content:
        return ""
    paragraphs = content.split("\n\n")
    html_parts = []
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        # 마크다운 헤딩
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", p)
        if heading_match:
            level = len(heading_match.group(1))
            html_parts.append(f"<h{level}>{heading_match.group(2)}</h{level}>")
        else:
            html_parts.append(f"<p>{p}</p>")
    return "\n".join(html_parts)


def _extract_faq(content: str) -> list[dict]:
    """콘텐츠에서 질문형 문장을 추출하여 FAQ 구성."""
    if not content:
        return []

    faq_items = []
    # 물음표를 유지하면서 문장 분리 (lookbehind로 ?/./! 뒤에서 분리)
    sentences = re.split(r"(?<=[?!.])\s+|\n+", content)
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        # 물음표로 끝나거나 한국어 질문형 어미
        if "?" in s or s.endswith("까"):
            question = s.rstrip("?").strip() + "?"
            faq_items.append({
                "q": question,
                "a": "본문을 참조해 주세요.",
            })
        if len(faq_items) >= 5:  # 최대 5개
            break

    return faq_items


def _build_sns_copies(content: str, title: str) -> dict[str, str]:
    """플랫폼별 SNS 카피 생성."""
    plain = re.sub(r"[#*_`>\[\]()]", "", content)
    plain = re.sub(r"\n+", " ", plain).strip()

    copies = {}
    for platform, max_len in _SNS_MAX_LENGTHS.items():
        prefix = f"{title}\n\n" if title else ""
        available = max_len - len(prefix)
        if available <= 0:
            copies[platform] = title[:max_len]
            continue

        body = plain[:available]
        if len(plain) > available:
            body = plain[:available - 3] + "..."
        copies[platform] = prefix + body

    return copies
