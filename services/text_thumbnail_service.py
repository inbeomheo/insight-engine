"""
텍스트 썸네일 생성 서비스
제목 텍스트를 기반으로 레이아웃/색상/폰트 설정을 산출하는 규칙 기반 서비스.
실제 이미지 렌더링 없이 썸네일 메타데이터만 생성.
"""
import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List

logger = logging.getLogger(__name__)

# 스타일별 색상 팔레트 정의
STYLE_PALETTES: Dict[str, Dict[str, str]] = {
    "bold": {"bg": "#1A1A2E", "text": "#FFFFFF", "accent": "#E94560"},
    "minimal": {"bg": "#FAFAFA", "text": "#333333", "accent": "#888888"},
    "gradient": {"bg": "#0F2027", "text": "#FFFFFF", "accent": "#2C5364"},
    "dark": {"bg": "#0D0D0D", "text": "#F0F0F0", "accent": "#BB86FC"},
    "neon": {"bg": "#0A0A0A", "text": "#39FF14", "accent": "#FF00FF"},
}

# 지원 스타일 목록
AVAILABLE_STYLES = list(STYLE_PALETTES.keys())

# 폰트 크기 범위 (제목 길이에 따라 조절)
_FONT_SIZE_MAX = 96
_FONT_SIZE_MIN = 28
# 한 줄 최대 글자수
_MAX_CHARS_PER_LINE = 12


@dataclass
class ThumbnailResult:
    """텍스트 썸네일 생성 결과"""
    title: str
    style: str
    layout: Dict[str, object]
    text_lines: List[str]
    font_size: int
    colors: Dict[str, str]
    readability_score: float


def _split_title_lines(title: str) -> List[str]:
    """제목을 줄바꿈 분리 (한 줄 최대 12자).

    단어 단위로 끊되, 단어가 12자를 초과하면 강제 분할.
    """
    words = title.split()
    if not words:
        return [title] if title else []

    lines: List[str] = []
    current_line = ""

    for word in words:
        # 현재 줄에 단어를 추가했을 때 12자 초과 여부 확인
        candidate = f"{current_line} {word}".strip() if current_line else word

        if len(candidate) <= _MAX_CHARS_PER_LINE:
            current_line = candidate
        else:
            # 현재 줄이 있으면 먼저 저장
            if current_line:
                lines.append(current_line)

            # 단어 자체가 12자 초과면 강제 분할
            if len(word) > _MAX_CHARS_PER_LINE:
                for i in range(0, len(word), _MAX_CHARS_PER_LINE):
                    chunk = word[i:i + _MAX_CHARS_PER_LINE]
                    if i + _MAX_CHARS_PER_LINE < len(word):
                        lines.append(chunk)
                    else:
                        current_line = chunk
            else:
                current_line = word

    # 마지막 줄 추가
    if current_line:
        lines.append(current_line)

    return lines


def _calculate_font_size(title: str) -> int:
    """제목 길이에 따라 폰트 크기 자동 조정.

    짧은 제목 → 큰 폰트, 긴 제목 → 작은 폰트.
    """
    length = len(title)
    if length <= 0:
        return _FONT_SIZE_MAX

    # 길이가 늘어날수록 로그 스케일로 축소
    # 1~5자: 96, 50자+: 28
    scale = max(0.0, 1.0 - math.log(max(length, 1)) / math.log(80))
    size = int(_FONT_SIZE_MIN + (_FONT_SIZE_MAX - _FONT_SIZE_MIN) * scale)
    return max(_FONT_SIZE_MIN, min(_FONT_SIZE_MAX, size))


def _calculate_readability_score(title: str, style: str, text_lines: List[str]) -> float:
    """가독성 점수 계산 (0~100).

    기준: 글자수 적절성, 배경-텍스트 대비, 줄 수.
    """
    score = 100.0

    # 1) 글자수 페널티: 너무 짧거나 너무 길면 감점
    char_count = len(title)
    if char_count < 3:
        score -= 20.0  # 너무 짧아서 의미 전달 부족
    elif char_count > 40:
        score -= min(30.0, (char_count - 40) * 0.75)  # 길수록 감점 (최대 30)

    # 2) 배경-텍스트 대비: 밝은 배경+밝은 글자 또는 어두운 배경+어두운 글자 감점
    colors = STYLE_PALETTES.get(style, STYLE_PALETTES["bold"])
    bg_brightness = _hex_brightness(colors["bg"])
    text_brightness = _hex_brightness(colors["text"])
    contrast = abs(bg_brightness - text_brightness)
    if contrast < 80:
        score -= 25.0  # 낮은 대비
    elif contrast < 120:
        score -= 10.0

    # 3) 줄 수 페널티: 4줄 초과 시 감점
    line_count = len(text_lines)
    if line_count > 6:
        score -= 20.0
    elif line_count > 4:
        score -= 10.0

    return round(max(0.0, min(100.0, score)), 1)


def _hex_brightness(hex_color: str) -> float:
    """HEX 색상의 밝기 계산 (0~255)."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return 128.0  # 파싱 불가 시 중간값
    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        # ITU-R BT.601 가중 밝기
        return 0.299 * r + 0.587 * g + 0.114 * b
    except ValueError:
        return 128.0


def generate_text_thumbnail(title: str, style: str = "bold") -> ThumbnailResult:
    """대형 텍스트 썸네일 메타데이터를 생성합니다.

    Args:
        title: 썸네일에 표시할 제목 텍스트
        style: 스타일 프리셋 ("bold", "minimal", "gradient", "dark", "neon")

    Returns:
        ThumbnailResult 데이터클래스
    """
    # 입력 정규화
    title = (title or "").strip()
    if not title:
        title = "제목 없음"

    if style not in STYLE_PALETTES:
        style = "bold"

    # 줄 분리
    text_lines = _split_title_lines(title)

    # 폰트 크기 결정
    font_size = _calculate_font_size(title)

    # 색상 팔레트
    colors = dict(STYLE_PALETTES[style])  # 복사본 반환

    # 레이아웃 계산
    layout = {
        "width": 1280,
        "height": 720,
        "text_align": "center",
        "vertical_align": "middle",
        "padding": 40,
        "line_spacing": int(font_size * 1.3),
    }

    # 가독성 점수
    readability_score = _calculate_readability_score(title, style, text_lines)

    return ThumbnailResult(
        title=title,
        style=style,
        layout=layout,
        text_lines=text_lines,
        font_size=font_size,
        colors=colors,
        readability_score=readability_score,
    )


def list_styles() -> List[str]:
    """사용 가능한 스타일 목록을 반환합니다."""
    return list(AVAILABLE_STYLES)
