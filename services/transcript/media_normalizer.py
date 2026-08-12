"""업로드 미디어를 안전하게 검사하고 Whisper용 mono 16kHz WAV로 정규화한다."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


class MediaValidationError(ValueError):
    """지원하지 않거나 정책 한도를 넘는 미디어."""


@dataclass(frozen=True)
class MediaProbe:
    duration_seconds: float
    format_name: str
    audio_codec: str


def _tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise RuntimeError(f'{name} 실행 파일이 서버에 없습니다.')
    return path


def probe_media(path: str, *, max_duration_seconds: int) -> MediaProbe:
    """FFprobe로 실제 오디오 트랙과 재생시간을 검사한다."""
    command = [
        _tool('ffprobe'), '-v', 'error',
        '-show_entries', 'format=duration,format_name:stream=codec_type,codec_name',
        '-of', 'json', path,
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        payload = json.loads(result.stdout)
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError) as exc:
        raise MediaValidationError('손상되었거나 읽을 수 없는 미디어 파일입니다.') from exc

    streams = payload.get('streams') if isinstance(payload, dict) else None
    audio_stream = next(
        (item for item in streams or [] if item.get('codec_type') == 'audio'),
        None,
    )
    if not audio_stream:
        raise MediaValidationError('오디오 트랙이 없는 영상은 전사할 수 없습니다.')

    try:
        duration = float(payload.get('format', {}).get('duration'))
    except (TypeError, ValueError) as exc:
        raise MediaValidationError('미디어 재생시간을 확인할 수 없습니다.') from exc
    if duration <= 0:
        raise MediaValidationError('비어 있는 미디어 파일은 전사할 수 없습니다.')
    if duration > max_duration_seconds:
        minutes = max_duration_seconds // 60
        raise MediaValidationError(f'미디어 재생시간은 최대 {minutes}분까지 지원합니다.')

    return MediaProbe(
        duration_seconds=round(duration, 3),
        format_name=str(payload.get('format', {}).get('format_name') or ''),
        audio_codec=str(audio_stream.get('codec_name') or ''),
    )


def normalize_media(
    source_path: str,
    *,
    max_duration_seconds: int,
    timeout_seconds: int,
) -> tuple[str, MediaProbe]:
    """검증된 로컬 미디어를 PCM WAV로 변환한다. 호출자가 반환 파일을 삭제해야 한다."""
    source = Path(source_path)
    if not source.is_file():
        raise MediaValidationError('업로드 파일을 찾을 수 없습니다.')

    probe = probe_media(str(source), max_duration_seconds=max_duration_seconds)
    fd, output_path = tempfile.mkstemp(prefix='media_whisper_', suffix='.wav')
    os.close(fd)
    try:
        command = [
            _tool('ffmpeg'), '-v', 'error', '-nostdin', '-y',
            '-i', str(source), '-map', '0:a:0', '-vn',
            '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le', output_path,
        ]
        subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            timeout=timeout_seconds,
        )
        if not os.path.isfile(output_path) or os.path.getsize(output_path) == 0:
            raise MediaValidationError('미디어에서 음성을 추출하지 못했습니다.')
        return output_path, probe
    except subprocess.TimeoutExpired as exc:
        try:
            os.remove(output_path)
        except OSError:
            pass
        raise MediaValidationError('미디어 음성 추출 시간이 제한을 초과했습니다.') from exc
    except subprocess.SubprocessError as exc:
        try:
            os.remove(output_path)
        except OSError:
            pass
        raise MediaValidationError('미디어에서 음성을 추출하지 못했습니다.') from exc
    except Exception:
        try:
            os.remove(output_path)
        except OSError:
            pass
        raise
