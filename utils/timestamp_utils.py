"""
타임스탬프 유틸리티
YouTube 타임코드 변환 및 딥링크 생성 기능
"""
import re
from typing import Optional


def seconds_to_hhmmss(seconds: float) -> str:
    """초를 HH:MM:SS 형식 문자열로 변환합니다.

    Args:
        seconds: 변환할 초 (음수는 0으로 처리)

    Returns:
        'HH:MM:SS' 형식 문자열 (예: '00:02:05')
    """
    total = max(0, int(seconds))
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def hhmmss_to_seconds(hhmmss: str) -> int:
    """HH:MM:SS 형식 문자열을 초로 변환합니다.

    Args:
        hhmmss: 'HH:MM:SS' 또는 'MM:SS' 형식 문자열 (예: '00:02:05' 또는 '2:05')

    Returns:
        초 단위 정수 (변환 실패 시 0)
    """
    parts = hhmmss.strip().split(':')
    try:
        if len(parts) == 3:
            h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
        elif len(parts) == 2:
            h, m, s = 0, int(parts[0]), int(parts[1])
        else:
            return 0
        return h * 3600 + m * 60 + s
    except (ValueError, IndexError):
        return 0


def make_youtube_deeplink(video_url: str, seconds: int) -> str:
    """YouTube URL에 타임코드 파라미터를 추가하여 딥링크를 생성합니다.

    Args:
        video_url: YouTube 영상 URL
        seconds: 이동할 시간 (초)

    Returns:
        타임코드 파라미터가 포함된 YouTube URL
        (예: 'https://www.youtube.com/watch?v=abc123&t=125')
    """
    if not video_url:
        return video_url

    # 기존 t= 파라미터가 있으면 제거
    url = re.sub(r'[&?]t=\d+', '', video_url)

    # 파라미터 구분자 결정
    separator = '&' if '?' in url else '?'
    return f"{url}{separator}t={seconds}"


def format_segments_for_prompt(segments: list, max_segments: int = 50) -> str:
    """자막 세그먼트 배열을 AI 프롬프트 주입용 텍스트로 포맷합니다.

    타임스탬프가 있는 세그먼트를 '[HH:MM:SS] 텍스트' 형식으로 조합합니다.
    세그먼트 수가 많으면 균등하게 샘플링합니다.

    Args:
        segments: 자막 세그먼트 목록 [{'start': float, 'text': str}, ...]
        max_segments: 최대 포함 세그먼트 수 (기본 50)

    Returns:
        '[HH:MM:SS] 텍스트\\n...' 형식의 문자열, 세그먼트가 없으면 빈 문자열
    """
    if not segments:
        return ""

    # 세그먼트 수가 많으면 균등 샘플링
    if len(segments) > max_segments:
        step = len(segments) / max_segments
        segments = [segments[int(i * step)] for i in range(max_segments)]

    lines = []
    for seg in segments:
        start = seg.get('start', 0)
        text = seg.get('text', '').strip()
        if text:
            timestamp = seconds_to_hhmmss(start)
            lines.append(f"[{timestamp}] {text}")

    return "\n".join(lines)


def extract_timestamps_from_content(content: str) -> list:
    """AI 생성 콘텐츠에서 [HH:MM:SS] 형식 타임스탬프를 추출합니다.

    Args:
        content: 마크다운 콘텐츠 문자열

    Returns:
        타임스탬프 딕셔너리 목록 [{'hhmmss': str, 'seconds': int, 'pos': int}, ...]
    """
    pattern = re.compile(r'\[(\d{1,2}:\d{2}:\d{2})\]')
    results = []
    for match in pattern.finditer(content):
        hhmmss = match.group(1)
        results.append({
            'hhmmss': hhmmss,
            'seconds': hhmmss_to_seconds(hhmmss),
            'pos': match.start(),
        })
    return results
