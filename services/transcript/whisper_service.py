"""Whisper 기반 음성->텍스트 변환 서비스

YouTube 자막이 없는 영상에 대해 오디오를 추출하고
faster-whisper로 음성 인식하여 텍스트를 반환합니다.
"""
import os
import re
import shutil
import tempfile
import logging

logger = logging.getLogger(__name__)


def download_audio(video_url: str) -> str | None:
    """yt-dlp로 YouTube 영상에서 오디오만 추출합니다.

    Args:
        video_url: YouTube 영상 URL

    Returns:
        추출된 오디오 파일 경로 (wav). 실패 시 None.
    """
    try:
        import yt_dlp
    except ImportError:
        logger.error("yt-dlp가 설치되어 있지 않습니다: pip install yt-dlp")
        return None

    tmp_dir = None
    try:
        tmp_dir = tempfile.mkdtemp(prefix='ytdlp_audio_')
        out_template = os.path.join(tmp_dir, 'audio')

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': out_template,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
                'preferredquality': '16',
            }],
            'quiet': True,
            'no_warnings': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

        # yt-dlp가 실제 생성한 .wav 파일 탐색
        for f in os.listdir(tmp_dir):
            fpath = os.path.join(tmp_dir, f)
            if f.endswith('.wav') and os.path.getsize(fpath) > 0:
                return fpath

        logger.warning("오디오 다운로드 후 wav 파일을 찾을 수 없습니다: %s", tmp_dir)
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return None

    except Exception as e:
        logger.error("오디오 다운로드 실패: %s", str(e))
        if tmp_dir:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        return None


def transcribe_audio(audio_path: str, model_size: str = 'base', language: str | None = None) -> str | None:
    """faster-whisper로 오디오를 텍스트로 변환합니다.

    Args:
        audio_path: 오디오 파일 경로
        model_size: Whisper 모델 크기 (tiny, base, small, medium, large-v3, large-v3-turbo)

    Returns:
        인식된 텍스트. 실패 시 None.
    """
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        logger.error("faster-whisper가 설치되어 있지 않습니다: pip install faster-whisper")
        return None

    try:
        # GPU 가용 시 CUDA + float16, 아니면 CPU + int8
        try:
            import torch
            if torch.cuda.is_available():
                device, compute_type = "cuda", "float16"
            else:
                device, compute_type = "cpu", "int8"
        except ImportError:
            device, compute_type = "cpu", "int8"

        logger.info("Whisper 모델 로딩: %s (device=%s, compute=%s)", model_size, device, compute_type)
        try:
            model = WhisperModel(model_size, device=device, compute_type=compute_type)
        except Exception:
            if device != "cpu":
                logger.warning("CUDA 초기화 실패, CPU로 폴백합니다")
                device, compute_type = "cpu", "int8"
                model = WhisperModel(model_size, device=device, compute_type=compute_type)
            else:
                raise
        segments, info = model.transcribe(audio_path, language=language, beam_size=5)

        texts = [segment.text.strip() for segment in segments if segment.text.strip()]
        if not texts:
            logger.warning("Whisper 인식 결과가 비어 있습니다 (언어: %s)", info.language)
            return None

        result = " ".join(texts)
        logger.info(
            "Whisper 변환 완료: 언어=%s, 확률=%.2f, 길이=%d자",
            info.language, info.language_probability, len(result)
        )
        return result

    except Exception as e:
        logger.error("Whisper 변환 실패: %s", str(e))
        return None


def extract_subtitles_ytdlp(video_url: str) -> str | None:
    """yt-dlp로 YouTube 자막 파일을 직접 다운로드합니다 (음성인식 없이).

    영상에 업로드된 자막 또는 자동 생성 자막이 있으면 텍스트로 반환합니다.
    Whisper보다 훨씬 빠르고 (수초), 정확도도 높습니다.

    Args:
        video_url: YouTube 영상 URL

    Returns:
        자막 텍스트. 자막 없으면 None.
    """
    try:
        import yt_dlp
    except ImportError:
        logger.error("yt-dlp가 설치되어 있지 않습니다: pip install yt-dlp")
        return None

    tmp_dir = None
    try:
        tmp_dir = tempfile.mkdtemp(prefix='ytdlp_subs_')
        out_path = os.path.join(tmp_dir, 'subs')

        ydl_opts = {
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['ko', 'en', 'ja'],
            'subtitlesformat': 'vtt/srt/best',
            'outtmpl': out_path,
            'quiet': True,
            'no_warnings': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

        # 다운로드된 자막 파일 찾기 (ko > en > ja > 기타)
        sub_file = None
        for lang in ['ko', 'en', 'ja']:
            for ext in ['.vtt', '.srt']:
                candidate = f'{out_path}.{lang}{ext}'
                if os.path.exists(candidate) and os.path.getsize(candidate) > 0:
                    sub_file = candidate
                    break
            if sub_file:
                break

        # 언어 특정 파일이 없으면 아무 자막 파일이나 사용
        if not sub_file:
            for f in os.listdir(tmp_dir):
                if f.endswith(('.vtt', '.srt')) and os.path.getsize(os.path.join(tmp_dir, f)) > 0:
                    sub_file = os.path.join(tmp_dir, f)
                    break

        if not sub_file:
            logger.info("yt-dlp: 다운로드 가능한 자막 없음")
            return None

        with open(sub_file, 'r', encoding='utf-8', errors='ignore') as f:
            raw = f.read()
        text = _parse_subtitle_text(raw)

        if text and len(text.strip()) > 50:
            logger.info("yt-dlp 자막 추출 성공: %d자 (%s)", len(text), os.path.basename(sub_file))
            return text.strip()

        logger.info("yt-dlp: 자막 파일이 너무 짧음 (%d자)", len(text) if text else 0)
        return None

    except Exception as e:
        logger.warning("yt-dlp 자막 추출 실패: %s", str(e))
        return None
    finally:
        if tmp_dir:
            shutil.rmtree(tmp_dir, ignore_errors=True)


def _parse_subtitle_text(raw: str) -> str:
    """VTT/SRT 자막 파일에서 순수 텍스트만 추출합니다."""
    lines = raw.split('\n')
    texts = []
    seen = set()

    for line in lines:
        line = line.strip()
        # 타임스탬프, 시퀀스 번호, 헤더 스킵
        if not line or line.startswith('WEBVTT') or line.startswith('NOTE'):
            continue
        if re.match(r'^\d+$', line):
            continue
        if re.match(r'[\d:.,]+\s*-->', line):
            continue
        # HTML 태그 제거
        clean = re.sub(r'<[^>]+>', '', line).strip()
        if clean and clean not in seen:
            seen.add(clean)
            texts.append(clean)

    return ' '.join(texts)


def extract_transcript_whisper(video_url: str, model_size: str = 'base') -> str | None:
    """YouTube URL에서 Whisper 자막을 추출합니다 (전체 파이프라인).

    1. yt-dlp로 오디오 다운로드
    2. faster-whisper로 텍스트 변환
    3. 임시 파일 정리

    Args:
        video_url: YouTube 영상 URL
        model_size: Whisper 모델 크기

    Returns:
        인식된 텍스트. 실패 시 None.
    """
    audio_path = None
    try:
        logger.info("Whisper 자막 추출 시작: %s (모델: %s)", video_url, model_size)

        audio_path = download_audio(video_url)
        if not audio_path:
            logger.warning("오디오 다운로드 실패로 Whisper 추출 중단")
            return None

        text = transcribe_audio(audio_path, model_size)
        if not text:
            logger.warning("Whisper 텍스트 변환 실패")
            return None

        logger.info("Whisper 자막 추출 성공: %d자", len(text))
        return text

    except Exception as e:
        logger.error("Whisper 파이프라인 오류: %s", str(e))
        return None
    finally:
        if audio_path:
            # download_audio가 tmp_dir 내부 파일을 반환하므로 디렉토리 통째 삭제
            audio_dir = os.path.dirname(audio_path)
            if audio_dir and os.path.basename(audio_dir).startswith('ytdlp_audio_'):
                shutil.rmtree(audio_dir, ignore_errors=True)
            else:
                _cleanup_file(audio_path)


def _cleanup_file(path: str) -> None:
    """임시 파일을 안전하게 삭제합니다."""
    if not path:
        return
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError as e:
        logger.warning("임시 파일 삭제 실패: %s (%s)", path, str(e))
