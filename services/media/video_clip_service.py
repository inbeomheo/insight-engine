"""
비디오 클립 추출 서비스

YouTube 영상에서 타임스탬프 구간을 잘라 짧은 클립(Shorts)을 생성합니다.
yt-dlp로 영상 다운로드 -> ffmpeg로 구간 추출.
"""
import logging
import os
import subprocess
import tempfile
import uuid
from typing import List, Dict

logger = logging.getLogger(__name__)

# 클립 저장 디렉토리
CLIP_OUTPUT_DIR = os.path.join(tempfile.gettempdir(), 'insight_clips')


def _ensure_output_dir() -> str:
    """클립 출력 디렉토리를 생성하고 경로를 반환합니다."""
    os.makedirs(CLIP_OUTPUT_DIR, exist_ok=True)
    return CLIP_OUTPUT_DIR


def _download_video(video_url: str) -> str:
    """yt-dlp로 YouTube 영상을 다운로드합니다.

    Args:
        video_url: YouTube 영상 URL

    Returns:
        다운로드된 영상 파일 경로

    Raises:
        RuntimeError: yt-dlp 실행 실패
    """
    output_dir = _ensure_output_dir()
    output_path = os.path.join(output_dir, f'source_{uuid.uuid4().hex[:8]}.mp4')

    cmd = [
        'yt-dlp',
        '-f', 'bestvideo[height<=720]+bestaudio/best[height<=720]',
        '--merge-output-format', 'mp4',
        '-o', output_path,
        '--no-playlist',
        video_url,
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300
        )
        if result.returncode != 0:
            raise RuntimeError(f'yt-dlp 실패: {result.stderr[:300]}')
    except FileNotFoundError:
        raise RuntimeError('yt-dlp가 설치되어 있지 않습니다. "pip install yt-dlp" 실행 후 재시도하세요.')

    if not os.path.exists(output_path):
        raise RuntimeError('영상 다운로드 결과 파일이 없습니다.')

    logger.info('영상 다운로드 완료: %s', output_path)
    return output_path


def _extract_clip(source_path: str, start: str, end: str, index: int) -> str:
    """ffmpeg로 영상의 특정 구간을 추출합니다.

    Args:
        source_path: 원본 영상 경로
        start: 시작 타임스탬프 (HH:MM:SS 또는 MM:SS)
        end: 종료 타임스탬프
        index: 클립 인덱스 (파일명용)

    Returns:
        추출된 클립 파일 경로

    Raises:
        RuntimeError: ffmpeg 실행 실패
    """
    output_dir = _ensure_output_dir()
    clip_path = os.path.join(output_dir, f'clip_{uuid.uuid4().hex[:8]}_{index}.mp4')

    cmd = [
        'ffmpeg',
        '-i', source_path,
        '-ss', start,
        '-to', end,
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-y',  # 덮어쓰기
        clip_path,
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            raise RuntimeError(f'ffmpeg 클립 추출 실패: {result.stderr[:300]}')
    except FileNotFoundError:
        raise RuntimeError('ffmpeg가 설치되어 있지 않습니다.')

    if not os.path.exists(clip_path):
        raise RuntimeError(f'클립 파일 생성 실패 (index={index})')

    return clip_path


def extract_clips(video_url: str, clips: List[Dict[str, str]]) -> List[str]:
    """YouTube 영상에서 여러 클립을 추출합니다.

    Args:
        video_url: YouTube 영상 URL
        clips: 클립 목록. 각 항목: {"start": "MM:SS", "end": "MM:SS"}

    Returns:
        추출된 클립 파일 경로 목록

    Raises:
        ValueError: clips가 비어 있거나 형식 오류
        RuntimeError: 다운로드/추출 실패
    """
    if not clips:
        raise ValueError('추출할 클립 목록이 비어 있습니다.')
    if len(clips) > 10:
        raise ValueError('최대 10개 클립까지 추출할 수 있습니다.')

    for i, clip in enumerate(clips):
        if 'start' not in clip or 'end' not in clip:
            raise ValueError(f'클립 {i+1}에 start/end 타임스탬프가 필요합니다.')

    # 1. 원본 영상 다운로드
    source_path = _download_video(video_url)

    # 2. 각 클립 추출
    clip_paths = []
    try:
        for i, clip in enumerate(clips):
            path = _extract_clip(source_path, clip['start'], clip['end'], i)
            clip_paths.append(path)
            logger.info('클립 %d 추출 완료: %s → %s', i + 1, clip['start'], clip['end'])
    finally:
        # 원본 영상 정리
        if os.path.exists(source_path):
            os.remove(source_path)

    return clip_paths


def cleanup_clips(clip_paths: List[str]) -> None:
    """사용 완료된 클립 파일들을 삭제합니다."""
    for path in clip_paths:
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            logger.warning('클립 파일 삭제 실패: %s', path)
