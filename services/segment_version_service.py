"""세그먼트별 버전 자동 생성 서비스

동일 원본 콘텐츠를 초보자/실무자/의사결정자 등 세그먼트별로
톤, 길이, CTA를 달리하여 자동 생성한다.
"""
from dataclasses import dataclass


@dataclass
class SegmentConfig:
    """세그먼트 설정"""
    name: str           # "beginner", "practitioner", "executive"
    tone: str           # "친근한", "전문적", "간결한"
    max_length: int     # 목표 글자수
    focus: str          # "기초 설명", "실무 적용", "의사결정 요약"
    cta_style: str      # "학습 유도", "도구 추천", "ROI 강조"


# 기본 세그먼트 프리셋
SEGMENT_PRESETS: dict[str, SegmentConfig] = {
    "beginner": SegmentConfig("beginner", "친근한", 1500, "기초 설명", "학습 유도"),
    "practitioner": SegmentConfig("practitioner", "전문적", 2000, "실무 적용", "도구 추천"),
    "executive": SegmentConfig("executive", "간결한", 800, "의사결정 요약", "ROI 강조"),
}

# 커스텀 세그먼트 저장소 (런타임)
_custom_segments: dict[str, SegmentConfig] = {}


def get_segment_config(segment_name: str) -> SegmentConfig:
    """세그먼트 프리셋 또는 커스텀 설정 조회.

    Args:
        segment_name: 세그먼트 이름

    Returns:
        SegmentConfig 인스턴스

    Raises:
        ValueError: 존재하지 않는 세그먼트
    """
    config = SEGMENT_PRESETS.get(segment_name) or _custom_segments.get(segment_name)
    if not config:
        available = list_segments()
        raise ValueError(
            f"알 수 없는 세그먼트: '{segment_name}'. "
            f"사용 가능: {available}"
        )
    return config


def register_custom_segment(
    name: str,
    tone: str,
    max_length: int,
    focus: str,
    cta_style: str,
) -> SegmentConfig:
    """커스텀 세그먼트 등록.

    Args:
        name: 세그먼트 이름 (영문 권장)
        tone: 어조
        max_length: 목표 글자수 (양수)
        focus: 초점
        cta_style: CTA 스타일

    Returns:
        등록된 SegmentConfig

    Raises:
        ValueError: 유효하지 않은 파라미터
    """
    if not name or not name.strip():
        raise ValueError("세그먼트 이름은 필수입니다")
    if max_length <= 0:
        raise ValueError("max_length는 양수여야 합니다")

    config = SegmentConfig(
        name=name.strip(),
        tone=tone,
        max_length=max_length,
        focus=focus,
        cta_style=cta_style,
    )
    _custom_segments[name.strip()] = config
    return config


def list_segments() -> list[str]:
    """사용 가능한 모든 세그먼트 이름 목록 반환."""
    names = list(SEGMENT_PRESETS.keys()) + list(_custom_segments.keys())
    return sorted(set(names))


def generate_versions(
    content: str,
    segments: list[str] | None = None,
) -> dict[str, str]:
    """세그먼트별 버전 생성.

    AI 호출 없이 프롬프트 기반 변환 시뮬레이션으로
    세그먼트 설정(톤, 길이, 포커스, CTA)에 맞게 내용을 조정한다.

    Args:
        content: 원본 콘텐츠
        segments: 생성할 세그먼트 이름 목록. None이면 기본 3개 프리셋.

    Returns:
        {세그먼트명: 변환된 콘텐츠} 딕셔너리

    Raises:
        ValueError: 빈 콘텐츠 또는 알 수 없는 세그먼트
    """
    if not content or not content.strip():
        raise ValueError("콘텐츠가 비어 있습니다")

    if segments is None:
        segments = list(SEGMENT_PRESETS.keys())

    results: dict[str, str] = {}
    for seg_name in segments:
        config = get_segment_config(seg_name)
        results[seg_name] = _transform_for_segment(content, config)

    return results


def _transform_for_segment(content: str, config: SegmentConfig) -> str:
    """세그먼트 설정에 맞게 콘텐츠를 변환 (시뮬레이션).

    실제 AI 호출 대신, 세그먼트 메타데이터를 헤더로 붙이고
    max_length에 맞게 콘텐츠를 잘라 반환한다.
    """
    header = (
        f"[{config.name}] 톤: {config.tone} | "
        f"초점: {config.focus} | CTA: {config.cta_style}\n\n"
    )

    # max_length에서 헤더 길이를 빼고 본문 길이 조정
    body_limit = max(config.max_length - len(header), 100)
    body = content.strip()
    if len(body) > body_limit:
        body = body[:body_limit - 3] + "..."

    return header + body
