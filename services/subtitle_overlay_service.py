"""
자막 오버레이 서비스

ffmpeg drawtext를 사용하여 비디오에 자막을 오버레이합니다.
"""
import logging
import os
import subprocess
import tempfile
import uuid
from typing import List, Dict

logger = logging.getLogger(__name__)

CLIP_OUTPUT_DIR = os.path.join(tempfile.gettempdir(), 'insight_clips')


def _build_drawtext_filter(subtitles: List[Dict]) -> str:
    """자막 목록으로 ffmpeg drawtext 필터 문자열을 생성합니다.

    Args:
        subtitles: [{"text": "...", "start": 0.0, "end": 3.0}, ...]

    Returns:
        ffmpeg drawtext 필터 체인 문자열
    """
    filters = []
    for sub in subtitles:
        text = sub['text'].replace("'", "\\'").replace(":", "\\:")
        start = float(sub['start'])
        end = float(sub['end'])
        f = (
            f"drawtext=text='{text}'"
            f":fontsize=28:fontcolor=white:borderw=2:bordercolor=black"
            f":x=(w-text_w)/2:y=h-60"
            f":enable='between(t,{start},{end})'"
        )
        filters.append(f)

    return ','.join(filters)


def add_subtitles(video_path: str, subtitles: List[Dict]) -> str:
    """비디오에 자막을 오버레이합니다.

    Args:
        video_path: 원본 비디오 파일 경로
        subtitles: 자막 목록. [{"text": "...", "start": 0.0, "end": 3.0}, ...]

    Returns:
        자막이 추가된 비디오 파일 경로

    Raises:
        ValueError: 입력 유효성 오류
        RuntimeError: ffmpeg 실행 실패
    """
    _validate_subtitle_inputs(video_path, subtitles)

    os.makedirs(CLIP_OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(CLIP_OUTPUT_DIR, f'subtitled_{uuid.uuid4().hex[:8]}.mp4')

    cmd = [
        'ffmpeg', '-i', video_path,
        '-vf', _build_drawtext_filter(subtitles),
        '-c:a', 'copy', '-y', output_path,
    ]

    _run_ffmpeg(cmd, output_path)
    logger.info('자막 오버레이 완료: %s', output_path)
    return output_path


def _validate_subtitle_inputs(video_path: str, subtitles: List[Dict]) -> None:
    """자막 오버레이 입력을 검증합니다."""
    if not os.path.exists(video_path):
        raise ValueError(f'비디오 파일이 존재하지 않습니다: {video_path}')
    if not subtitles:
        raise ValueError('자막 목록이 비어 있습니다.')
    for i, sub in enumerate(subtitles):
        if 'text' not in sub or 'start' not in sub or 'end' not in sub:
            raise ValueError(f'자막 {i+1}에 text/start/end 필드가 필요합니다.')


def _run_ffmpeg(cmd: list, output_path: str) -> None:
    """ffmpeg 명령을 실행하고 결과를 검증합니다."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if result.returncode != 0:
            raise RuntimeError(f'ffmpeg 자막 오버레이 실패: {result.stderr[:300]}')
    except FileNotFoundError:
        raise RuntimeError('ffmpeg가 설치되어 있지 않습니다.')
    if not os.path.exists(output_path):
        raise RuntimeError('자막 오버레이 결과 파일이 없습니다.')
