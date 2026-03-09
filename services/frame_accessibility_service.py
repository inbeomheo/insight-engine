"""
프레임 접근성 서비스.

비디오 프레임의 접근성 메타데이터를 생성하고 검증한다.
"""

from dataclasses import dataclass, field
import uuid


@dataclass
class FrameA11y:
    """프레임 접근성 정보"""
    frame_id: str = ""
    timestamp: str = ""
    alt_description: str = ""
    has_captions: bool = False
    audio_description: str = ""
    complexity: str = "simple"  # simple / moderate / complex


def generate_description(frame_content: str, context: str = "") -> str:
    """
    프레임 설명 생성.

    키워드 기반으로 시각 장애인을 위한 프레임 설명을 생성한다.
    """
    if not frame_content:
        return "설명할 수 있는 프레임 내용이 없습니다"

    # 키워드 기반 설명 구성
    parts = []

    # 콘텐츠 키워드 분석
    keywords = frame_content.split()
    if len(keywords) <= 3:
        parts.append(f"'{frame_content}'이(가) 표시된 프레임")
    else:
        parts.append(f"'{' '.join(keywords[:5])}' 등의 내용이 포함된 프레임")

    if context:
        parts.append(f"(맥락: {context})")

    return " ".join(parts)


def assess_frame_complexity(frame_content: str) -> str:
    """
    프레임 복잡도 평가.

    단어 수와 특수 요소 기반으로 복잡도를 판단한다.
    """
    if not frame_content:
        return "simple"

    words = frame_content.split()
    word_count = len(words)

    # 특수 요소 감지 (숫자, 특수문자 등)
    has_numbers = any(c.isdigit() for c in frame_content)
    has_special = any(c in "!@#$%^&*()[]{}|<>:;" for c in frame_content)

    if word_count > 20 or (has_numbers and has_special):
        return "complex"
    elif word_count > 8 or has_numbers:
        return "moderate"
    else:
        return "simple"


def create_audio_description(frames: list) -> str:
    """
    음성 해설 스크립트 생성.

    프레임 시퀀스를 기반으로 시각 장애인을 위한 음성 해설을 생성한다.
    """
    if not frames:
        return "음성 해설 대상 프레임이 없습니다."

    lines = []
    for frame in frames:
        timestamp = frame.timestamp or "00:00"
        desc = frame.alt_description or "설명 없음"

        line = f"[{timestamp}] {desc}"

        if frame.complexity == "complex":
            line += " (복잡한 장면)"

        lines.append(line)

    return "\n".join(lines)


def validate_accessibility(frames: list) -> dict:
    """
    접근성 검증.

    캡션과 설명 누락률을 계산한다.
    """
    if not frames:
        return {
            "total_frames": 0,
            "caption_coverage": 0.0,
            "description_coverage": 0.0,
            "audio_description_coverage": 0.0,
            "issues": [],
            "overall_score": 0.0,
        }

    total = len(frames)
    has_caption = sum(1 for f in frames if f.has_captions)
    has_description = sum(1 for f in frames if f.alt_description)
    has_audio_desc = sum(1 for f in frames if f.audio_description)

    caption_coverage = has_caption / total
    description_coverage = has_description / total
    audio_coverage = has_audio_desc / total

    issues = []

    if caption_coverage < 1.0:
        missing = total - has_caption
        issues.append(f"{missing}개 프레임에 캡션이 없습니다")

    if description_coverage < 1.0:
        missing = total - has_description
        issues.append(f"{missing}개 프레임에 대체 설명이 없습니다")

    # complex 프레임에 audio_description 없는 경우
    complex_no_audio = [
        f for f in frames
        if f.complexity == "complex" and not f.audio_description
    ]
    if complex_no_audio:
        issues.append(f"{len(complex_no_audio)}개 복잡한 프레임에 음성 해설이 없습니다")

    # 종합 점수: 각 커버리지의 가중 평균
    overall_score = (
        caption_coverage * 0.4
        + description_coverage * 0.4
        + audio_coverage * 0.2
    )

    return {
        "total_frames": total,
        "caption_coverage": round(caption_coverage, 4),
        "description_coverage": round(description_coverage, 4),
        "audio_description_coverage": round(audio_coverage, 4),
        "issues": issues,
        "overall_score": round(overall_score, 4),
    }
