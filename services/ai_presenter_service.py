"""
AI 발표자 생성 서비스

사진 설명과 스크립트로부터 AI 발표자 설정을 생성하는 규칙 기반 서비스.
실제 영상 합성은 수행하지 않으며, 발표자 메타데이터와
스크립트 세그먼트를 구조화하여 반환한다.
외부 API 호출 없음.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import uuid
import re


@dataclass
class PresenterResult:
    """AI 발표자 생성 결과."""
    presenter_id: str
    appearance: Dict             # 외형 설정 (style, features 등)
    script_segments: List[Dict]  # 분절된 스크립트 목록
    estimated_duration: float    # 예상 발표 시간 (초)
    lip_sync_ready: bool         # 립싱크 준비 여부


# ── 발표자 스타일 프리셋 ──
_PRESENTER_STYLES = {
    "professional": {
        "posture": "정면 응시, 상반신",
        "expression": "자신감 있는 미소",
        "gesture": "최소한의 손동작",
        "background": "단색 배경 또는 오피스",
    },
    "casual": {
        "posture": "약간 기울인 자세",
        "expression": "친근한 표정",
        "gesture": "자연스러운 손동작",
        "background": "밝은 자연광 배경",
    },
    "educational": {
        "posture": "측면 또는 칠판 앞",
        "expression": "설명하는 표정",
        "gesture": "가리키기, 설명 동작",
        "background": "화이트보드 또는 슬라이드 옆",
    },
}

# ── 기본 설정 ──
_CHARS_PER_SECOND = 4.0    # 한국어 기준 초당 약 4자 발화
_MIN_SEGMENT_CHARS = 20     # 세그먼트 최소 글자 수
_MAX_SEGMENT_CHARS = 200    # 세그먼트 최대 글자 수
_PAUSE_BETWEEN_SEGMENTS = 0.5  # 세그먼트 간 쉼 (초)


def _detect_style(description: str) -> str:
    """사진 설명에서 발표자 스타일 추론."""
    desc_lower = description.lower()

    if any(kw in desc_lower for kw in ["정장", "수트", "넥타이", "비즈니스", "공식", "professional"]):
        return "professional"
    elif any(kw in desc_lower for kw in ["교수", "강사", "칠판", "교육", "수업", "educational"]):
        return "educational"
    elif any(kw in desc_lower for kw in ["캐주얼", "편한", "일상", "자연", "casual"]):
        return "casual"

    return "professional"  # 기본값


def _parse_appearance(description: str, style: str) -> Dict:
    """사진 설명에서 외형 정보 추출."""
    style_preset = _PRESENTER_STYLES.get(style, _PRESENTER_STYLES["professional"])

    appearance = {
        "style": style,
        "description": description.strip(),
        "posture": style_preset["posture"],
        "expression": style_preset["expression"],
        "gesture": style_preset["gesture"],
        "background": style_preset["background"],
    }

    return appearance


def _split_script(script: str) -> List[Dict]:
    """
    스크립트를 발화 세그먼트로 분절.
    문장 단위로 나누되, 너무 짧으면 합치고 너무 길면 쪼갠다.
    """
    if not script or not script.strip():
        return []

    # 문장 분리 (마침표, 물음표, 느낌표 기준)
    sentences = re.split(r'(?<=[.!?。])\s*', script.strip())
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return [{"text": script.strip(), "index": 0}]

    # 세그먼트 병합/분할
    segments = []
    buffer = ""

    for sentence in sentences:
        if len(buffer) + len(sentence) <= _MAX_SEGMENT_CHARS:
            buffer = (buffer + " " + sentence).strip() if buffer else sentence
        else:
            if buffer:
                segments.append(buffer)
            # 긴 문장은 쉼표/접속사 기준으로 분할
            if len(sentence) > _MAX_SEGMENT_CHARS:
                parts = re.split(r'[,，;；]\s*', sentence)
                sub_buffer = ""
                for part in parts:
                    if len(sub_buffer) + len(part) <= _MAX_SEGMENT_CHARS:
                        sub_buffer = (sub_buffer + ", " + part).strip(", ") if sub_buffer else part
                    else:
                        if sub_buffer:
                            segments.append(sub_buffer)
                        sub_buffer = part
                if sub_buffer:
                    segments.append(sub_buffer)
            else:
                buffer = sentence

    if buffer:
        segments.append(buffer)

    # 너무 짧은 세그먼트 병합
    merged = []
    for seg in segments:
        if merged and len(merged[-1]) < _MIN_SEGMENT_CHARS:
            merged[-1] = merged[-1] + " " + seg
        else:
            merged.append(seg)

    # 세그먼트 메타데이터 구성
    result = []
    cumulative_time = 0.0
    for i, text in enumerate(merged):
        duration = len(text) / _CHARS_PER_SECOND
        result.append({
            "index": i,
            "text": text,
            "start_time": round(cumulative_time, 2),
            "duration": round(duration, 2),
        })
        cumulative_time += duration + _PAUSE_BETWEEN_SEGMENTS

    return result


def generate_presenter(photo_description: str, script: str) -> PresenterResult:
    """
    AI 발표자 설정을 생성한다.

    Args:
        photo_description: 발표자 외형 설명 (예: "정장을 입은 30대 남성")
        script: 발표 스크립트 텍스트

    Returns:
        PresenterResult: 발표자 설정 + 스크립트 세그먼트

    Raises:
        ValueError: 설명이나 스크립트가 비어있을 때
    """
    if not photo_description or not photo_description.strip():
        raise ValueError("발표자 외형 설명이 필요합니다")
    if not script or not script.strip():
        raise ValueError("스크립트가 필요합니다")

    # 스타일 감지
    style = _detect_style(photo_description)

    # 외형 정보 구성
    appearance = _parse_appearance(photo_description, style)

    # 스크립트 분절
    segments = _split_script(script)

    # 예상 발표 시간 계산
    if segments:
        last = segments[-1]
        estimated_duration = last["start_time"] + last["duration"]
    else:
        estimated_duration = 0.0

    # 립싱크 준비 여부 (스크립트가 충분하고 세그먼트가 분절되었으면 준비됨)
    lip_sync_ready = len(segments) >= 1 and estimated_duration > 0

    return PresenterResult(
        presenter_id=str(uuid.uuid4())[:12],
        appearance=appearance,
        script_segments=segments,
        estimated_duration=round(estimated_duration, 2),
        lip_sync_ready=lip_sync_ready,
    )
