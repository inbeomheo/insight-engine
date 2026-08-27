"""
비디오 클립 추출 서비스

YouTube 영상에서 타임스탬프 구간을 잘라 짧은 클립(Shorts)을 생성합니다.
yt-dlp로 영상 다운로드 -> ffmpeg로 구간 추출.
"""
import json
import logging
import math
import os
import re
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from typing import Dict, List

from services.media.video_deepdive_service import (
    MonitoredDownloadError,
    _cleanup_download_paths,
    normalize_youtube_id,
    run_monitored_download,
)

logger = logging.getLogger(__name__)

# 클립 저장 디렉토리
CLIP_OUTPUT_DIR = os.environ.get(
    'VIDEO_CLIP_OUTPUT_DIR', os.path.join(tempfile.gettempdir(), 'insight_clips')
)
MAX_SOURCE_BYTES = 512 * 1024 * 1024
MAX_VIDEO_DURATION_SECONDS = 2 * 60 * 60
MAX_CLIP_DURATION_SECONDS = 3 * 60
MAX_TOTAL_CLIP_DURATION_SECONDS = 10 * 60
MAX_CLIP_BYTES = 128 * 1024 * 1024
MAX_OUTPUT_BYTES = 512 * 1024 * 1024
MAX_PROCESSING_SECONDS = 10 * 60

_CLIP_NAME_RE = re.compile(r'^clip_[0-9a-f]{8}_[0-9]+\.mp4$')
_SOURCE_NAME_RE = re.compile(r'^source_[0-9a-f]{8}\.mp4$')
_TIMESTAMP_RE = re.compile(r'^(?:(\d+):)?(\d+):(\d{1,2})(?:\.(\d{1,3}))?$')


def _ensure_output_dir() -> str:
    """클립 출력 디렉토리를 생성하고 경로를 반환합니다."""
    root = Path(CLIP_OUTPUT_DIR).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    if root.is_symlink():
        raise RuntimeError('클립 출력 디렉터리는 심볼릭 링크일 수 없습니다.')
    return str(root.resolve())


def _remaining_timeout(deadline: float, cap: int) -> int:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise RuntimeError('영상 클립 전체 처리 제한 시간을 초과했습니다.')
    return max(1, min(cap, int(math.ceil(remaining))))


def _run_process(cmd: List[str], *, deadline: float, timeout: int) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=_remaining_timeout(deadline, timeout),
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError('영상 클립 전체 처리 제한 시간을 초과했습니다.') from exc
    except FileNotFoundError as exc:
        raise RuntimeError(f'{Path(cmd[0]).name} 실행 파일을 찾을 수 없습니다.') from exc


def _timestamp_seconds(value: str) -> float:
    match = _TIMESTAMP_RE.fullmatch(str(value or '').strip())
    if not match:
        raise ValueError('타임스탬프는 MM:SS 또는 HH:MM:SS 형식이어야 합니다.')
    first, middle, seconds, millis = match.groups()
    if int(seconds) >= 60:
        raise ValueError('타임스탬프의 초 값은 60보다 작아야 합니다.')
    if first is not None and int(middle) >= 60:
        raise ValueError('HH:MM:SS 형식의 분 값은 60보다 작아야 합니다.')
    hours = int(first or 0)
    minutes = int(middle)
    fraction = int(millis or 0) / (10 ** len(millis)) if millis else 0.0
    return hours * 3600 + minutes * 60 + int(seconds) + fraction


def _safe_generated_path(raw_path: str, *, source: bool = False) -> Path:
    root = Path(_ensure_output_dir())
    candidate = Path(raw_path).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    name_re = _SOURCE_NAME_RE if source else _CLIP_NAME_RE
    if candidate.parent.resolve() != root or not name_re.fullmatch(candidate.name):
        raise ValueError('허용된 클립 출력 경로 밖의 파일은 처리할 수 없습니다.')
    if candidate.is_symlink():
        raise ValueError('심볼릭 링크 클립은 처리할 수 없습니다.')
    return candidate


def _output_bytes() -> int:
    root = Path(_ensure_output_dir())
    total = 0
    for path in root.glob('clip_*.mp4'):
        if path.is_file() and not path.is_symlink():
            total += path.stat().st_size
    return total


def _download_video(video_url: str, *, deadline: float | None = None) -> str:
    """yt-dlp로 YouTube 영상을 다운로드합니다.

    Args:
        video_url: YouTube 영상 URL

    Returns:
        다운로드된 영상 파일 경로

    Raises:
        RuntimeError: yt-dlp 실행 실패
    """
    effective_deadline = deadline or (time.monotonic() + MAX_PROCESSING_SECONDS)
    video_id = normalize_youtube_id(video_url)
    canonical_url = f'https://www.youtube.com/watch?v={video_id}'
    output_dir = _ensure_output_dir()
    output_path = os.path.join(output_dir, f'source_{uuid.uuid4().hex[:8]}.mp4')

    metadata = _run_process(
        ['yt-dlp', '--no-playlist', '--skip-download', '--dump-single-json', canonical_url],
        deadline=effective_deadline,
        timeout=60,
    )
    if metadata.returncode != 0:
        raise RuntimeError('영상 메타데이터를 확인하지 못했습니다.')
    try:
        duration = float(json.loads(metadata.stdout or '{}').get('duration') or 0)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError('영상 길이를 확인하지 못해 클립 추출을 중단했습니다.') from exc
    if duration <= 0 or duration > MAX_VIDEO_DURATION_SECONDS:
        raise ValueError(f'영상 길이는 최대 {MAX_VIDEO_DURATION_SECONDS // 60}분까지 허용됩니다.')

    cmd = [
        'yt-dlp',
        '-f', 'bestvideo[height<=720]+bestaudio/best[height<=720]',
        '--merge-output-format', 'mp4',
        '--no-progress',
        '--max-filesize', str(MAX_SOURCE_BYTES),
        '--match-filter', f'duration <= {MAX_VIDEO_DURATION_SECONDS}',
        '-o', output_path,
        '--no-playlist',
        canonical_url,
    ]

    try:
        result = run_monitored_download(
            cmd,
            watch_root=output_dir,
            watch_prefix=Path(output_path).stem,
            max_bytes=MAX_SOURCE_BYTES,
            timeout=300,
            deadline=effective_deadline,
        )
        if result.returncode != 0:
            raise RuntimeError('영상 다운로드에 실패했습니다.')
    except MonitoredDownloadError as exc:
        if exc.reason == 'size':
            raise ValueError('다운로드 영상 크기 상한을 초과했습니다.') from exc
        if exc.reason == 'timeout':
            raise RuntimeError('영상 클립 전체 처리 제한 시간을 초과했습니다.') from exc
        raise RuntimeError('영상 다운로드에 실패했습니다.') from exc
    except Exception:
        _cleanup_download_paths(Path(output_dir), Path(output_path).stem)
        raise

    if not os.path.exists(output_path):
        _cleanup_download_paths(Path(output_dir), Path(output_path).stem)
        raise RuntimeError('영상 다운로드 결과 파일이 없습니다.')
    source_path = _safe_generated_path(output_path, source=True)
    if source_path.stat().st_size > MAX_SOURCE_BYTES:
        _cleanup_download_paths(Path(output_dir), Path(output_path).stem)
        raise ValueError('다운로드 영상 크기 상한을 초과했습니다.')

    logger.info('영상 다운로드 완료: %s', output_path)
    return output_path


def _extract_clip(
    source_path: str,
    start: str,
    end: str,
    index: int,
    *,
    deadline: float | None = None,
) -> str:
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
        '-fs', str(MAX_CLIP_BYTES),
        '-y',  # 덮어쓰기
        clip_path,
    ]

    effective_deadline = deadline or (time.monotonic() + MAX_PROCESSING_SECONDS)
    try:
        result = _run_process(cmd, deadline=effective_deadline, timeout=120)
        if result.returncode != 0:
            raise RuntimeError('ffmpeg 클립 추출에 실패했습니다.')
    except Exception:
        try:
            _safe_generated_path(clip_path).unlink(missing_ok=True)
        except (OSError, ValueError):
            pass
        raise

    if not os.path.exists(clip_path):
        raise RuntimeError(f'클립 파일 생성 실패 (index={index})')
    safe_path = _safe_generated_path(clip_path)
    if safe_path.stat().st_size > MAX_CLIP_BYTES:
        safe_path.unlink(missing_ok=True)
        raise ValueError('생성된 클립 파일 크기 상한을 초과했습니다.')

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

    normalized: list[tuple[str, str, float]] = []
    total_duration = 0.0
    for i, clip in enumerate(clips):
        start = str(clip['start']).strip()
        end = str(clip['end']).strip()
        start_seconds = _timestamp_seconds(start)
        end_seconds = _timestamp_seconds(end)
        duration = end_seconds - start_seconds
        if duration <= 0:
            raise ValueError(f'클립 {i+1}의 종료 시각은 시작 시각보다 뒤여야 합니다.')
        if duration > MAX_CLIP_DURATION_SECONDS:
            raise ValueError(f'클립 한 개는 최대 {MAX_CLIP_DURATION_SECONDS}초까지 허용됩니다.')
        total_duration += duration
        normalized.append((start, end, duration))
    if total_duration > MAX_TOTAL_CLIP_DURATION_SECONDS:
        raise ValueError(f'클립 전체 길이는 최대 {MAX_TOTAL_CLIP_DURATION_SECONDS}초까지 허용됩니다.')

    # yt-dlp가 임의 URL 스킴/로컬 경로를 처리하지 못하게 YouTube ID로 정규화한다.
    video_id = normalize_youtube_id(video_url)
    canonical_url = f'https://www.youtube.com/watch?v={video_id}'
    if _output_bytes() >= MAX_OUTPUT_BYTES:
        raise ValueError('클립 영구 산출물 저장 용량 상한을 초과했습니다.')
    deadline = time.monotonic() + MAX_PROCESSING_SECONDS

    # 1. 원본 영상 다운로드
    source_path = _download_video(canonical_url, deadline=deadline)

    # 2. 각 클립 추출
    clip_paths = []
    try:
        for i, (start, end, _) in enumerate(normalized):
            path = _extract_clip(source_path, start, end, i, deadline=deadline)
            clip_paths.append(path)
            if _output_bytes() > MAX_OUTPUT_BYTES:
                raise ValueError('클립 영구 산출물 저장 용량 상한을 초과했습니다.')
            logger.info('클립 %d 추출 완료: %s → %s', i + 1, start, end)
    except Exception:
        if clip_paths:
            cleanup_clips(clip_paths)
        raise
    finally:
        # 원본 영상 정리
        try:
            _safe_generated_path(source_path, source=True).unlink(missing_ok=True)
        except (OSError, ValueError):
            logger.warning('원본 영상 정리 경로가 허용 루트 밖입니다.')

    return clip_paths


def cleanup_clips(clip_paths: List[str]) -> None:
    """허용된 클립 출력 루트에서 이 서비스가 만든 파일만 삭제합니다."""
    safe_paths = [_safe_generated_path(path) for path in clip_paths]
    for path in safe_paths:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            logger.warning('클립 파일 삭제 실패: %s', path)
