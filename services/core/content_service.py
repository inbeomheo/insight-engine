"""
YouTube 콘텐츠 서비스
자막, 댓글, 제목 추출 기능 제공

자막 폴백 4단계 구현은 services/transcript/fallbacks/ 패키지에 분리되어 있다.
공통 헬퍼/상수는 services/transcript/_shared.py 참조.

[모킹/monkeypatch 안내]
폴백 구현이 fallbacks/ 와 _shared.py 로 분리된 이후, 본 모듈에 재노출된
헬퍼 별칭(`_create_http_session`, `_get_proxy_config`, `_is_safe_caption_url`,
`_download_caption_from_url` 등)을 patch해도 폴백 내부 호출에는 영향을 주지
못한다. 동작을 제어하려면 정식(canonical) 위치를 patch할 것:
  - HTTP 세션/프록시: `services.transcript._shared.create_http_session`,
    `services.transcript._shared.get_proxy_config`
  - 자막 URL 검증/다운로드: `services.transcript.fallbacks.watch_page.*`
  - Supadata 호출: `services.transcript.fallbacks.supadata.*`
(`requests.get`은 공유 모듈 싱글톤이므로 어느 모듈 경로로 patch해도 전역 적용됨.)
"""
from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Dict, List, Optional, Union

import functools

import requests
from flask import current_app

# 공통 상수/타입/헬퍼는 services/transcript/_shared 에서 import
from services.transcript._shared import (
    CaptionTrack,
    HTTP_TIMEOUT,
    PREFERRED_LANGUAGES,
    SUPADATA_API_URL,
    TIMEOUT_CONNECT,
    TIMEOUT_READ_LONG,
    TIMEOUT_READ_MEDIUM,
    TIMEOUT_READ_SHORT,
    TranscriptResult,
    USER_AGENT,
    create_http_session as _create_http_session,
    get_proxy_config as _get_proxy_config,
    log_info as _log_info,
    log_warning as _log_warning,
)

# 자막 폴백 함수들은 services/transcript/fallbacks/ 에서 import
from services.transcript.fallbacks.supadata import (
    get_transcript_via_supadata,
)
from services.transcript.fallbacks.youtube_api import (
    build_ytt_api as _build_ytt_api,
    detect_auto_caption as _detect_auto_caption,
    extract_segments_from_transcript as _extract_segments_from_transcript,
    extract_text_from_transcript as _extract_text_from_transcript,
    fetch_transcript_with_api as _fetch_transcript_with_api,
    order_transcript_tracks as _order_transcript_tracks,
)
from services.transcript.fallbacks.watch_page import (
    download_caption_from_url as _download_caption_from_url,
    extract_caption_tracks as _extract_caption_tracks,
    extract_yt_initial_player_response as _extract_yt_initial_player_response,
    get_transcript_from_watch_page as _get_transcript_from_watch_page,
    is_safe_caption_url as _is_safe_caption_url,
    parse_timedtext_xml as _parse_timedtext_xml,
    parse_vtt as _parse_vtt,
    pick_caption_track as _pick_caption_track,
)


@functools.lru_cache(maxsize=1)
def _get_youtube_build():
    """googleapiclient를 지연 로딩합니다 (cold start 최적화)."""
    from googleapiclient.discovery import build
    return build


# googleapiclient.errors.HttpError — 지연 import (콜드 스타트 200-400ms 절감)
# YouTube API 함수 내부에서 로컬 import 사용
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)

# 버전 호환: 일부 예외는 구버전에는 존재하지 않을 수 있음
try:
    from youtube_transcript_api import (
        RequestBlocked,
        IpBlocked,
        AgeRestricted,
        PoTokenRequired,
        VideoUnplayable,
        YouTubeRequestFailed,
        InvalidVideoId,
        CouldNotRetrieveTranscript,
    )
except ImportError:
    try:
        from youtube_transcript_api import YouTubeTranscriptApiException as _YTBase
    except ImportError:
        class _YTBase(Exception):
            pass
    RequestBlocked = IpBlocked = AgeRestricted = PoTokenRequired = _YTBase
    VideoUnplayable = InvalidVideoId = YouTubeRequestFailed = CouldNotRetrieveTranscript = _YTBase

# 재시도 최대 횟수 (자막 API)
MAX_RETRY_ATTEMPTS: int = 3

# YouTube URL Patterns
YOUTUBE_URL_REGEX = re.compile(
    r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/'
    r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
)
VIDEO_ID_PATTERNS = [
    re.compile(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*'),
    re.compile(r'(?:embed\/)([0-9A-Za-z_-]{11})'),
    re.compile(r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})')
]

# ==================== Cache System ====================

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'cache')

# YouTube video_id 형식: 11자 영숫자 + 하이픈 + 언더스코어
VIDEO_ID_PATTERN = re.compile(r'^[A-Za-z0-9_-]{11}$')


def _sanitize_video_id(video_id: str) -> str:
    """
    video_id 형식을 검증하여 Path Traversal 공격을 방지합니다.

    Args:
        video_id: YouTube 비디오 ID

    Returns:
        검증된 video_id

    Raises:
        ValueError: 유효하지 않은 video_id 형식
    """
    if not video_id or not VIDEO_ID_PATTERN.match(video_id):
        raise ValueError(f"Invalid video_id format: {video_id[:20] if video_id else 'None'}")
    return video_id


def _ensure_cache_dir() -> None:
    """캐시 디렉토리가 존재하는지 확인하고 없으면 생성합니다."""
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)


def _get_cache_path(video_id: str, cache_type: str) -> str:
    """
    캐시 파일 경로를 반환합니다.
    Path Traversal 방지를 위해 video_id를 검증합니다.
    """
    safe_id = _sanitize_video_id(video_id)
    safe_type = cache_type if cache_type in ('transcript', 'comments') else 'unknown'
    return os.path.join(CACHE_DIR, f"{safe_id}_{safe_type}.json")


def _load_cache(video_id: str, cache_type: str) -> Optional[Any]:
    """캐시에서 데이터를 로드합니다."""
    cache_path = _get_cache_path(video_id, cache_type)
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None
    return None


def _save_cache(video_id: str, cache_type: str, data: Any) -> None:
    """데이터를 캐시에 저장합니다."""
    _ensure_cache_dir()
    cache_path = _get_cache_path(video_id, cache_type)
    try:
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except IOError:
        pass  # 캐시 저장 실패는 무시


def get_cached_transcript(video_id: str) -> Optional[dict]:
    """video_id의 자막 파일 캐시를 반환한다 (없으면 None).

    AI 캐시 히트 시 YouTube 재추출 없이 자막을 응답에 채우기 위한 공개 헬퍼.
    구버전(str) 캐시는 dict 형태로 정규화하고, 잘못된 video_id는 None 처리한다.
    """
    try:
        cached = _load_cache(video_id, 'transcript')
    except ValueError:
        return None
    if cached is None:
        return None
    if isinstance(cached, dict) and 'text' in cached:
        return cached
    return {'text': cached, 'source': 'cache'}


def clear_cache(video_id: Optional[str] = None) -> int:
    """캐시를 삭제합니다. video_id가 None이면 전체 삭제."""
    # video_id가 지정된 경우 형식 검증 (Path Traversal 방지) — 캐시 디렉토리 존재 여부와 무관하게 입력 검증 선행
    if video_id is not None:
        _sanitize_video_id(video_id)

    if not os.path.exists(CACHE_DIR):
        return 0

    deleted = 0
    for filename in os.listdir(CACHE_DIR):
        if video_id is None or filename.startswith(f"{video_id}_"):
            try:
                os.remove(os.path.join(CACHE_DIR, filename))
                deleted += 1
            except IOError:
                pass
    return deleted


def purge_expired_cache(max_age_hours: int = 24) -> dict:
    """만료된 캐시 파일만 선택적으로 삭제합니다.

    Args:
        max_age_hours: 이 시간(시)보다 오래된 캐시 삭제 (기본 24시간)

    Returns:
        {'purged': 삭제 수, 'remaining': 남은 수, 'freed_bytes': 삭제로 확보된 바이트}
    """
    if not os.path.exists(CACHE_DIR):
        return {'purged': 0, 'remaining': 0, 'freed_bytes': 0}

    now = time.time()
    cutoff = now - (max_age_hours * 3600)
    purged = 0
    remaining = 0
    freed_bytes = 0

    for filename in os.listdir(CACHE_DIR):
        filepath = os.path.join(CACHE_DIR, filename)
        if not os.path.isfile(filepath):
            continue
        try:
            mtime = os.path.getmtime(filepath)
            if mtime < cutoff:
                try:
                    freed_bytes += os.path.getsize(filepath)
                except OSError:
                    pass
                os.remove(filepath)
                purged += 1
            else:
                remaining += 1
        except IOError:
            remaining += 1

    return {'purged': purged, 'remaining': remaining, 'freed_bytes': freed_bytes}


# ==================== URL Utilities ====================

def is_youtube_url(url: str) -> bool:
    """URL이 유효한 YouTube URL인지 확인합니다."""
    return bool(YOUTUBE_URL_REGEX.match(url))


def get_video_id(url: str) -> Optional[str]:
    """URL에서 YouTube 비디오 ID를 추출합니다."""
    if not url:
        return None

    for pattern in VIDEO_ID_PATTERNS:
        match = pattern.search(url)
        if match:
            return match.group(1)
    return None


# ==================== Main Transcript Function ====================
#
# HTTP 세션, 프록시, Supadata/YouTube API/Watch Page 폴백 함수들,
# 그리고 _log_info / _log_warning / _detect_auto_caption 등은
# 모두 services/transcript/_shared.py 및 services/transcript/fallbacks/
# 패키지에서 alias 형태로 import된다 (파일 상단 참조).


def _detect_language_from_text(text: str) -> str:
    """텍스트 첫 200자를 분석하여 간단한 언어 감지를 수행합니다 (단일 순회).

    한글 자모(\u3130-\u318F), 히라가나(\u3040-\u309F), 가타카나(\u30A0-\u30FF),
    가타카나 반각(\uFF65-\uFF9F) 범위를 포함하여 정확도를 높입니다.
    """
    if not text:
        return 'unknown'
    sample = text[:200]
    ko_count = 0
    ja_kana_count = 0
    cjk_count = 0
    for c in sample:
        if '\uac00' <= c <= '\ud7a3' or '\u3130' <= c <= '\u318f':
            ko_count += 1
        elif '\u3040' <= c <= '\u309f' or '\u30a0' <= c <= '\u30ff' or '\uff65' <= c <= '\uff9f':
            ja_kana_count += 1
        elif '\u4e00' <= c <= '\u9fff':
            cjk_count += 1
    sample_len = len(sample)
    if ko_count > sample_len * 0.1:
        return 'ko'
    if ja_kana_count > sample_len * 0.05:
        return 'ja'
    if cjk_count > sample_len * 0.1:
        return 'zh'
    return 'en'


# ==================== 병렬 폴백 전략 ====================

def _try_watch_page_fallback(video_id: str):
    """watch 페이지 직접 파싱으로 자막 추출."""
    wr = _get_transcript_from_watch_page(video_id)
    if isinstance(wr, str) and wr.strip():
        return ('watch', wr, 0.85, False)
    return None


def _try_ytdlp_fallback(video_id: str):
    """yt-dlp로 자막 파일 직접 추출."""
    try:
        from services.transcript.whisper_service import extract_subtitles_ytdlp
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        text = extract_subtitles_ytdlp(video_url)
        if text and text.strip():
            return ('ytdlp', text, 0.9, True)
    except Exception:
        pass
    return None


def _try_nlm_fallback(video_id: str):
    """NotebookLM을 통한 YouTube 자막 추출."""
    try:
        from services.notebooklm.notebooklm_service import NotebookLmService
        nlm = NotebookLmService()
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        content = nlm.extract_youtube_transcript(video_url)
        if content:
            return ('nlm', content, 0.88, False)
    except Exception:
        pass
    return None


def _run_parallel_fallbacks(
    video_id: str, overall_start: float, requested_language: Optional[str] = None,
) -> Optional[dict]:
    """watch_page + yt-dlp + NLM을 병렬 실행하여 첫 성공 결과를 반환.

    이 3개 폴백은 언어 선택 파라미터를 지원하지 않아(watch 페이지 파싱은 트랙
    자체가 언어 무관, yt-dlp/NLM은 자동 추출) requested_language는 결과의
    source_meta 기록용으로만 전달되고 실제 추출 동작에는 영향을 주지 않는다.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    _log_info(f"Starting parallel fallback (watch_page + yt-dlp + NLM) for video_id={video_id}")

    # with 블록을 쓰지 않는 이유: 첫 성공 시 느린 폴백(yt-dlp 수십 초)의 완료를
    # 기다리지 않고 즉시 반환하기 위해 shutdown(wait=False)로 직접 정리한다
    executor = ThreadPoolExecutor(max_workers=3)
    futures = {
        executor.submit(_try_watch_page_fallback, video_id): 'watch_page',
        executor.submit(_try_ytdlp_fallback, video_id): 'ytdlp',
        executor.submit(_try_nlm_fallback, video_id): 'nlm',
    }

    try:
        for future in as_completed(futures, timeout=90):
            try:
                res = future.result()
                if res is not None:
                    source_name, text, quality, is_auto = res
                    _log_info(f"Parallel fallback succeeded: {source_name} for video_id={video_id}")
                    executor.shutdown(wait=False, cancel_futures=True)
                    return _build_transcript_result(
                        text, source_name, quality, is_auto, overall_start, video_id,
                        requested_language=requested_language,
                    )
            except Exception as e:
                _log_warning(f"Parallel fallback {futures[future]} error: {str(e)[:100]}")
    finally:
        executor.shutdown(wait=False, cancel_futures=True)

    return None


# ==================== 자막 결과 빌더 ====================

def _build_transcript_result(
    text: str, source: str, quality: float, is_auto: bool,
    start_time: float, video_id: str, segments: list = None,
    requested_language: Optional[str] = None,
) -> dict:
    """자막 결과 딕셔너리를 생성하고 캐시에 저장한다."""
    detected_language = _detect_language_from_text(text)
    source_meta = {
        'source_type': source,
        'quality_score': quality,
        'is_auto': is_auto,
        'language': detected_language,
    }
    if requested_language:
        source_meta['requested_language'] = requested_language
        source_meta['language_matched'] = requested_language == detected_language
    elapsed_ms = round((time.time() - start_time) * 1000, 1)
    result = {
        'text': text,
        'source': source,
        'source_meta': source_meta,
        'extraction_time_ms': elapsed_ms,
    }
    if segments:
        result['segments'] = segments
    _save_cache(video_id, 'transcript', result)
    return result


def get_transcript(video_id: str, transcript_language: Optional[str] = None) -> TranscriptResult:
    """
    YouTube 자막을 가져옵니다.
    Supadata API 키는 환경변수(SUPADATA_API_KEY)에서 로드됩니다.

    Args:
        video_id: YouTube 비디오 ID
        transcript_language: 사용자가 지정한 자막 언어 코드(예: 'ko', 'en', 'ja').
            None이면 기존 기본 동작(PREFERRED_LANGUAGES 순서)과 동일하게 처리한다.
            지정 언어의 자막이 없어도 생성 실패로 이어지지 않고 기존 우선순위로 자동 폴백한다.

    Returns:
        성공: {'text': '자막 내용', 'source': 'api'|'watch'|'supadata'|'cache'}
        실패: {'error': '에러 메시지'}

    우선순위:
    0. 캐시 (있으면 바로 반환)
    1. youtube-transcript-api 라이브러리 (무료) — transcript_language 반영
    2. watch 페이지 직접 파싱 (무료) — 언어 파라미터 미지원
    2.5. yt-dlp 자막 직접 추출 (무료, 음성인식 없이) — 언어 파라미터 미지원
    3. Supadata API (유료) — transcript_language 반영
    4. Whisper 음성 인식 (로컬, 느림) — 자동 감지라 언어 파라미터 미지원
    """
    overall_start = time.time()

    # 0순위: 캐시 확인
    # 언어를 지정한 요청은 언어 무관 캐시를 그대로 재사용하지 않고 재추출한다
    # (기존 캐시가 다른 언어 자막일 수 있음 — 캐시 키 자체는 이번 스코프 밖).
    cached = None if transcript_language else _load_cache(video_id, 'transcript')
    if cached:
        _log_info(f"Transcript loaded from cache for video_id={video_id}")
        elapsed_ms = round((time.time() - overall_start) * 1000, 1)
        # 캐시된 데이터가 새 형식(dict)인지 구버전(str)인지 확인
        if isinstance(cached, dict) and 'text' in cached:
            cached['extraction_time_ms'] = elapsed_ms
            return cached
        return {'text': cached, 'source': 'cache', 'extraction_time_ms': elapsed_ms}

    supadata_api_key = os.getenv('SUPADATA_API_KEY', '')
    last_error = None

    # 1순위: youtube-transcript-api (무료)
    try:
        ytt_api = _build_ytt_api()
        fetched = None

        for attempt in range(MAX_RETRY_ATTEMPTS):
            fetched = _fetch_transcript_with_api(ytt_api, video_id, preferred_language=transcript_language)
            if fetched:
                break
            # 마지막 시도 후에는 폴백으로 바로 넘어간다 (불필요한 대기 제거)
            if attempt < MAX_RETRY_ATTEMPTS - 1:
                time.sleep(0.5 * (2 ** attempt))

        if fetched:
            text = _extract_text_from_transcript(fetched)
            if text:
                segments = _extract_segments_from_transcript(fetched)
                # fetch 결과에 이미 포함된 메타데이터 사용 (list() 추가 왕복 제거)
                is_auto = getattr(fetched, 'is_generated', False)
                return _build_transcript_result(
                    text, 'api', 0.95 if not is_auto else 0.85, is_auto,
                    overall_start, video_id, segments=segments,
                    requested_language=transcript_language,
                )

    except (TranscriptsDisabled, NoTranscriptFound) as e:
        # 자막 자체가 없는 경우 - Supadata도 불가능하므로 바로 에러 반환
        if isinstance(e, TranscriptsDisabled):
            return {'error': '자막을 가져올 수 없습니다. 이 영상은 자막이 비활성화되어 있습니다.'}
        return {'error': '자막을 찾을 수 없습니다. 이 영상에 제공되는 자막 트랙이 없습니다.'}
    except (AgeRestricted, VideoUnplayable, VideoUnavailable, InvalidVideoId) as e:
        # 영상 자체 문제 - Supadata도 불가능하므로 바로 에러 반환
        if isinstance(e, AgeRestricted):
            return {'error': '자막을 가져올 수 없습니다. 연령 제한 콘텐츠입니다.'}
        if isinstance(e, VideoUnplayable):
            return {'error': '자막을 가져올 수 없습니다. 재생 불가 영상입니다.'}
        if isinstance(e, VideoUnavailable):
            return {'error': '자막을 가져올 수 없습니다. 비공개/삭제/지역 제한 영상입니다.'}
        return {'error': '유효하지 않은 YouTube video_id 입니다.'}
    except (PoTokenRequired, IpBlocked, RequestBlocked, YouTubeRequestFailed, CouldNotRetrieveTranscript) as e:
        # 네트워크/차단 문제 - 폴백 시도 가능
        last_error = str(e)
        _log_warning(f"youtube-transcript-api failed for video_id={video_id}: {last_error}")
    except Exception as e:
        last_error = str(e)
        _log_warning(f"youtube-transcript-api unexpected error for video_id={video_id}: {last_error}")

    # ── 병렬 폴백: watch_page + yt-dlp + NLM 동시 실행 ──
    parallel_result = _run_parallel_fallbacks(video_id, overall_start, requested_language=transcript_language)
    if parallel_result:
        return parallel_result

    # ── 순차 폴백: 느리거나 유료인 방법들 ──

    # Whisper 음성 인식 (WHISPER_ENABLED=True일 때만, 무료 로컬 처리)
    whisper_enabled = os.getenv('WHISPER_ENABLED', 'false').lower() == 'true'
    if whisper_enabled:
        _log_info(f"Trying Whisper fallback for video_id={video_id}")
        try:
            from services.transcript.whisper_service import extract_transcript_whisper
            whisper_model = os.getenv('WHISPER_MODEL_SIZE', 'base')
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            whisper_text = extract_transcript_whisper(video_url, whisper_model)
            if whisper_text and whisper_text.strip():
                _log_info(f"Transcript extracted via Whisper for video_id={video_id}")
                return _build_transcript_result(
                    whisper_text, 'whisper', 0.75, True, overall_start, video_id,
                    requested_language=transcript_language,
                )
        except Exception as e:
            _log_warning(f"Whisper fallback failed for video_id={video_id}: {str(e)}")

    # Supadata API (유료 - 마지막 폴백)
    if supadata_api_key:
        _log_info(f"Trying Supadata API fallback for video_id={video_id}")
        supadata_result = get_transcript_via_supadata(video_id, supadata_api_key, preferred_language=transcript_language)
        if isinstance(supadata_result, str) and supadata_result.strip():
            _log_info(f"Transcript fetched via Supadata for video_id={video_id}")
            return _build_transcript_result(
                supadata_result, 'supadata', 0.8, False, overall_start, video_id,
                requested_language=transcript_language,
            )
        if isinstance(supadata_result, dict) and supadata_result.get('error'):
            return supadata_result

    # 모든 방법 실패
    if last_error:
        if '429' in last_error or 'Too Many Requests' in last_error:
            return {'error': '자막을 가져올 수 없습니다. 요청이 너무 많아 일시적으로 차단되었습니다.'}
        if 'IpBlocked' in last_error or 'RequestBlocked' in last_error:
            return {'error': '자막을 가져올 수 없습니다. 네트워크/IP 차단으로 YouTube 요청이 거부되었습니다.'}
        if 'PoTokenRequired' in last_error:
            return {'error': '자막을 가져올 수 없습니다. YouTube가 봇 차단 상태로 판단하여 요청이 거부되었습니다.'}
        return {'error': f'자막을 가져올 수 없습니다: {last_error}'}
    return {'error': '자막을 찾을 수 없습니다.'}


# ==================== YouTube API Functions ====================

def get_youtube_title(video_id: str) -> Optional[str]:
    """YouTube 영상 제목을 가져옵니다."""
    try:
        from googleapiclient.errors import HttpError
        api_key = current_app.config.get('YOUTUBE_API_KEY')
        if not api_key:
            return None

        youtube = _get_youtube_build()('youtube', 'v3', developerKey=api_key)
        results = youtube.videos().list(part="snippet", id=video_id).execute()

        items = results.get("items", [])
        if items:
            return items[0]["snippet"]["title"]
        return None

    except HttpError as e:
        _log_warning(f"YouTube API error getting title: {e}")
        return None
    except Exception as e:
        _log_warning(f"Error getting YouTube title: {e}")
        return None


def get_content_title(url: str) -> Optional[str]:
    """URL에서 콘텐츠 제목을 가져옵니다."""
    if not is_youtube_url(url):
        return None

    video_id = get_video_id(url)
    if video_id:
        return get_youtube_title(video_id)
    return None


def get_top_comments(video_id: str) -> List[str]:
    """YouTube 영상의 인기 댓글을 가져옵니다."""
    # 캐시 확인
    cached = _load_cache(video_id, 'comments')
    if cached is not None:
        _log_info(f"Comments loaded from cache for video_id={video_id}")
        return cached

    try:
        from googleapiclient.errors import HttpError
        api_key = current_app.config.get('YOUTUBE_API_KEY')
        if not api_key:
            _log_warning("YouTube API key not configured, skipping comments")
            return []

        youtube = _get_youtube_build()('youtube', 'v3', developerKey=api_key)
        results = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            textFormat="plainText",
            order="relevance",
            maxResults=50
        ).execute()

        comments: List[str] = []
        for item in results.get("items", []):
            comment = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
            comments.append(comment)

        # 댓글이 있으면 캐시에 저장
        if comments:
            _save_cache(video_id, 'comments', comments)

        return comments

    except HttpError as e:
        if e.resp.status == 403:
            _log_warning("YouTube API quota exceeded or comments disabled")
        else:
            _log_warning(f"YouTube API error: {e}")
        return []
    except Exception as e:
        _log_warning(f"Error getting comments: {e}")
        return []


# ==================== Playlist / Channel ====================

# URL 패턴
PLAYLIST_URL_PATTERNS = [
    re.compile(r'[?&]list=(PL[\w-]+)'),
    re.compile(r'playlist\?list=(PL[\w-]+)'),
]

CHANNEL_URL_PATTERNS = [
    re.compile(r'youtube\.com/@([\w.-]+)'),
    re.compile(r'youtube\.com/channel/(UC[\w-]+)'),
    re.compile(r'youtube\.com/c/([\w.-]+)'),
]


def is_playlist_url(url: str) -> bool:
    """URL이 YouTube 재생목록 URL인지 확인합니다."""
    if not url:
        return False
    return any(p.search(url) for p in PLAYLIST_URL_PATTERNS)


def is_channel_url(url: str) -> bool:
    """URL이 YouTube 채널 URL인지 확인합니다."""
    if not url:
        return False
    return any(p.search(url) for p in CHANNEL_URL_PATTERNS)


def _get_playlist_id(url: str) -> Optional[str]:
    """URL에서 재생목록 ID를 추출합니다."""
    for pattern in PLAYLIST_URL_PATTERNS:
        match = pattern.search(url)
        if match:
            return match.group(1)
    return None


def _get_channel_identifier(url: str) -> Optional[Dict[str, str]]:
    """URL에서 채널 식별자를 추출합니다.

    Returns:
        {'type': 'handle'|'id'|'custom', 'value': '...'} 또는 None
    """
    # @handle
    match = re.search(r'youtube\.com/@([\w.-]+)', url)
    if match:
        return {'type': 'handle', 'value': match.group(1)}

    # /channel/UCxxxx
    match = re.search(r'youtube\.com/channel/(UC[\w-]+)', url)
    if match:
        return {'type': 'id', 'value': match.group(1)}

    # /c/CustomName
    match = re.search(r'youtube\.com/c/([\w.-]+)', url)
    if match:
        return {'type': 'custom', 'value': match.group(1)}

    return None


def get_playlist_videos(url: str, max_results: int = 10) -> Dict[str, Any]:
    """재생목록에서 영상 목록을 가져옵니다.

    Args:
        url: YouTube 재생목록 URL
        max_results: 최대 결과 수 (기본 10, 최대 50)

    Returns:
        {'videos': [{'videoId': '...', 'title': '...', 'thumbnail': '...'}], 'total': N}
    """
    api_key = os.getenv('YOUTUBE_API_KEY', '')
    if not api_key:
        return {'error': 'YouTube API 키가 설정되지 않았습니다.'}

    playlist_id = _get_playlist_id(url)
    if not playlist_id:
        return {'error': '유효한 재생목록 URL이 아닙니다.'}

    max_results = min(max_results, 50)

    try:
        from googleapiclient.errors import HttpError
        youtube = _get_youtube_build()('youtube', 'v3', developerKey=api_key)
        response = youtube.playlistItems().list(
            part='snippet',
            playlistId=playlist_id,
            maxResults=max_results
        ).execute()

        videos = []
        for item in response.get('items', []):
            snippet = item.get('snippet', {})
            vid = snippet.get('resourceId', {}).get('videoId')
            if vid:
                videos.append({
                    'videoId': vid,
                    'title': snippet.get('title', ''),
                    'thumbnail': snippet.get('thumbnails', {}).get('medium', {}).get('url', '')
                })

        total = response.get('pageInfo', {}).get('totalResults', len(videos))
        return {'videos': videos, 'total': total}

    except HttpError as e:
        _log_warning(f"Playlist API error: {e}")
        return {'error': f'재생목록 조회 실패: {e.resp.status}'}
    except Exception as e:
        _log_warning(f"Playlist fetch error: {e}")
        return {'error': '재생목록 영상 목록을 가져올 수 없습니다.'}


def get_channel_videos(url: str, max_results: int = 10) -> Dict[str, Any]:
    """채널에서 최신 영상 목록을 가져옵니다.

    Args:
        url: YouTube 채널 URL
        max_results: 최대 결과 수 (기본 10, 최대 50)

    Returns:
        {'videos': [{'videoId': '...', 'title': '...', 'thumbnail': '...'}], 'total': N}
    """
    api_key = os.getenv('YOUTUBE_API_KEY', '')
    if not api_key:
        return {'error': 'YouTube API 키가 설정되지 않았습니다.'}

    identifier = _get_channel_identifier(url)
    if not identifier:
        return {'error': '유효한 채널 URL이 아닙니다.'}

    max_results = min(max_results, 50)

    try:
        from googleapiclient.errors import HttpError
        youtube = _get_youtube_build()('youtube', 'v3', developerKey=api_key)

        # 채널 ID 조회
        channel_id = None
        if identifier['type'] == 'id':
            channel_id = identifier['value']
        else:
            # handle 또는 custom name으로 채널 검색
            if identifier['type'] == 'handle':
                search_query = f"@{identifier['value']}"
            else:
                search_query = identifier['value']

            search_resp = youtube.search().list(
                part='snippet',
                q=search_query,
                type='channel',
                maxResults=1
            ).execute()
            items = search_resp.get('items', [])
            if items:
                channel_id = items[0]['snippet']['channelId']

        if not channel_id:
            return {'error': '채널을 찾을 수 없습니다.'}

        # 채널의 uploads 재생목록 ID 조회
        channel_resp = youtube.channels().list(
            part='contentDetails',
            id=channel_id
        ).execute()
        channel_items = channel_resp.get('items', [])
        if not channel_items:
            return {'error': '채널 정보를 가져올 수 없습니다.'}

        uploads_id = channel_items[0]['contentDetails']['relatedPlaylists']['uploads']

        # uploads 재생목록에서 영상 목록 조회
        playlist_resp = youtube.playlistItems().list(
            part='snippet',
            playlistId=uploads_id,
            maxResults=max_results
        ).execute()

        videos = []
        for item in playlist_resp.get('items', []):
            snippet = item.get('snippet', {})
            vid = snippet.get('resourceId', {}).get('videoId')
            if vid:
                videos.append({
                    'videoId': vid,
                    'title': snippet.get('title', ''),
                    'thumbnail': snippet.get('thumbnails', {}).get('medium', {}).get('url', '')
                })

        total = playlist_resp.get('pageInfo', {}).get('totalResults', len(videos))
        return {'videos': videos, 'total': total}

    except HttpError as e:
        _log_warning(f"Channel API error: {e}")
        return {'error': f'채널 조회 실패: {e.resp.status}'}
    except Exception as e:
        _log_warning(f"Channel fetch error: {e}")
        return {'error': '채널 영상 목록을 가져올 수 없습니다.'}


# ==================== Utilities ====================

def truncate_text(text: str, max_tokens: int) -> str:
    """텍스트를 최대 토큰 수로 자릅니다."""
    if not isinstance(text, str):
        return ""

    tokens = text.split()
    if len(tokens) > max_tokens:
        return " ".join(tokens[:max_tokens]) + "..."
    return text

