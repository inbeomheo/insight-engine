"""
YouTube 콘텐츠 서비스
자막, 댓글, 제목 추출 기능 제공
"""
from __future__ import annotations

import html as html_module
import json
import os
import re
import time
from typing import Any, Dict, List, Optional, Union
from xml.etree import ElementTree

import functools

import requests
from flask import current_app


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

# Type aliases
TranscriptResult = Union[str, Dict[str, str]]
CaptionTrack = Dict[str, Any]

# Constants
SUPADATA_API_URL: str = "https://api.supadata.ai/v1/youtube/transcript"
PREFERRED_LANGUAGES: tuple[str, ...] = ("ko", "en")
MAX_RETRY_ATTEMPTS: int = 3
USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

# P2 버그 #8: HTTP 타임아웃 상수 정의
TIMEOUT_CONNECT: int = 5        # 연결 타임아웃 (초)
TIMEOUT_READ_SHORT: int = 10    # 짧은 읽기 타임아웃
TIMEOUT_READ_MEDIUM: int = 20   # 중간 읽기 타임아웃
TIMEOUT_READ_LONG: int = 30     # 긴 읽기 타임아웃 (기본)
HTTP_TIMEOUT: tuple[int, int] = (TIMEOUT_CONNECT, TIMEOUT_READ_LONG)  # (connect, read)

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


def clear_cache(video_id: Optional[str] = None) -> int:
    """캐시를 삭제합니다. video_id가 None이면 전체 삭제."""
    if not os.path.exists(CACHE_DIR):
        return 0

    # video_id가 지정된 경우 형식 검증 (Path Traversal 방지)
    if video_id is not None:
        _sanitize_video_id(video_id)

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


# ==================== HTTP Client ====================

def _create_http_session() -> requests.Session:
    """HTTP 세션을 생성하고 헤더/프록시를 설정합니다."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "en-US,en;q=0.9"
    })

    http_proxy = _get_proxy_config('HTTP')
    https_proxy = _get_proxy_config('HTTPS')

    if http_proxy or https_proxy:
        session.proxies = {}
        if http_proxy:
            session.proxies['http'] = http_proxy
        if https_proxy:
            session.proxies['https'] = https_proxy

    return session


def _get_proxy_config(proxy_type: str) -> Optional[str]:
    """프록시 설정을 가져옵니다."""
    config_key = f'YT_{proxy_type}_PROXY'
    env_key = f'{proxy_type}_PROXY'

    try:
        proxy = current_app.config.get(config_key)
    except RuntimeError:
        proxy = None

    return proxy or os.getenv(config_key) or os.getenv(env_key)


# ==================== Supadata API ====================

def get_transcript_via_supadata(video_id: str, api_key: str) -> Optional[TranscriptResult]:
    """Supadata API를 통해 YouTube 자막을 가져옵니다."""
    if not api_key:
        return None

    try:
        response = requests.get(
            SUPADATA_API_URL,
            params={"videoId": video_id, "text": "true"},
            headers={"x-api-key": api_key},
            timeout=HTTP_TIMEOUT
        )

        if response.status_code == 200:
            data = response.json()
            content = data.get("content", "")
            if content:
                return content

            transcript = data.get("transcript", [])
            if transcript:
                texts = [item.get("text", "") for item in transcript if item.get("text")]
                return " ".join(texts)
            _log_warning(f"Supadata returned empty content for video_id={video_id}")
            return None

        if response.status_code == 401:
            return {'error': 'Supadata API 키가 유효하지 않습니다.'}
        if response.status_code == 402:
            return {'error': 'Supadata API 사용량이 초과되었습니다. 플랜을 업그레이드하세요.'}

        _log_warning(f"Supadata API returned status {response.status_code} for video_id={video_id}")
        return None

    except requests.exceptions.Timeout:
        _log_warning(f"Supadata API timeout for video_id={video_id}")
        return None
    except requests.exceptions.RequestException as e:
        _log_warning(f"Supadata API request failed for video_id={video_id}: {str(e)}")
        return None


# ==================== YouTube Transcript API ====================

def _build_ytt_api() -> YouTubeTranscriptApi:
    """YouTubeTranscriptApi 인스턴스를 생성합니다."""
    try:
        http_client = _create_http_session()
        return YouTubeTranscriptApi(http_client=http_client)
    except Exception:
        return YouTubeTranscriptApi()


def _order_transcript_tracks(tracks: List[Any]) -> List[Any]:
    """자막 트랙을 우선순위에 따라 정렬합니다."""
    ordered: List[Any] = []
    seen: set = set()
    for is_generated in [False, True]:
        for lang in PREFERRED_LANGUAGES:
            for t in tracks:
                tid = id(t)
                if tid not in seen and getattr(t, 'is_generated', False) == is_generated and getattr(t, 'language_code', '') == lang:
                    ordered.append(t)
                    seen.add(tid)
        for t in tracks:
            tid = id(t)
            if tid not in seen and getattr(t, 'is_generated', False) == is_generated:
                ordered.append(t)
                seen.add(tid)
    return ordered


def _fetch_transcript_with_api(ytt_api: YouTubeTranscriptApi, video_id: str) -> Optional[Any]:
    """youtube-transcript-api를 사용하여 자막을 가져옵니다."""
    fetched = None

    if hasattr(ytt_api, "fetch") and hasattr(ytt_api, "list"):
        try:
            fetched = ytt_api.fetch(video_id, languages=PREFERRED_LANGUAGES)
        except (NoTranscriptFound, PoTokenRequired, YouTubeRequestFailed, CouldNotRetrieveTranscript):
            transcript_list = ytt_api.list(video_id)
            ordered_tracks = _order_transcript_tracks(list(transcript_list))

            for track in ordered_tracks:
                try:
                    fetched = track.fetch()
                    break
                except (PoTokenRequired, YouTubeRequestFailed, CouldNotRetrieveTranscript):
                    continue
    else:
        # 구버전 폴백
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            ordered_tracks = _order_transcript_tracks(list(transcript_list))

            for track in ordered_tracks:
                try:
                    fetched = track.fetch()
                    break
                except Exception:
                    continue
        except Exception:
            try:
                fetched = YouTubeTranscriptApi.get_transcript(video_id, languages=PREFERRED_LANGUAGES)
            except Exception:
                fetched = None

    return fetched


def _extract_text_from_transcript(fetched: Any) -> Optional[str]:
    """자막 객체에서 텍스트를 추출합니다."""
    texts: List[str] = []
    try:
        for snippet in fetched:
            text = getattr(snippet, 'text', None)
            if text is None and isinstance(snippet, dict):
                text = snippet.get('text')
            if text:
                texts.append(text)
    except TypeError:
        if hasattr(fetched, 'to_raw_data'):
            for item in fetched.to_raw_data():
                text = item.get('text')
                if text:
                    texts.append(text)

    return " ".join(texts) if texts else None


def _extract_segments_from_transcript(fetched: Any) -> List[Dict[str, Any]]:
    """자막 객체에서 타임스탬프가 포함된 세그먼트 목록을 추출합니다.

    Args:
        fetched: youtube-transcript-api가 반환한 자막 객체

    Returns:
        세그먼트 목록 [{'start': float, 'text': str, 'duration': float}, ...]
        타임스탬프 정보가 없으면 빈 리스트
    """
    segments: List[Dict[str, Any]] = []
    try:
        for snippet in fetched:
            # FetchedTranscript snippet 또는 dict
            start = getattr(snippet, 'start', None)
            text = getattr(snippet, 'text', None)
            duration = getattr(snippet, 'duration', None)

            if start is None and isinstance(snippet, dict):
                start = snippet.get('start')
                text = snippet.get('text')
                duration = snippet.get('duration', 0)

            if start is not None and text:
                segments.append({
                    'start': float(start),
                    'text': text.strip(),
                    'duration': float(duration) if duration is not None else 0.0,
                })
    except TypeError:
        if hasattr(fetched, 'to_raw_data'):
            for item in fetched.to_raw_data():
                start = item.get('start')
                text = item.get('text')
                if start is not None and text:
                    segments.append({
                        'start': float(start),
                        'text': text.strip(),
                        'duration': float(item.get('duration', 0)),
                    })

    return segments


# ==================== Watch Page Fallback ====================

def _extract_yt_initial_player_response(html_text: str) -> Optional[Dict[str, Any]]:
    """HTML에서 ytInitialPlayerResponse를 추출합니다."""
    if not isinstance(html_text, str) or not html_text:
        return None

    patterns = [
        r"ytInitialPlayerResponse\s*=\s*(\{.*?\})\s*;",
        r"var\s+ytInitialPlayerResponse\s*=\s*(\{.*?\})\s*;",
    ]

    for pattern in patterns:
        match = re.search(pattern, html_text, flags=re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                continue
    return None


def _extract_caption_tracks(player_response: Optional[Dict[str, Any]]) -> List[CaptionTrack]:
    """플레이어 응답에서 자막 트랙을 추출합니다."""
    try:
        captions = (player_response or {}).get('captions', {})
        renderer = captions.get('playerCaptionsTracklistRenderer', {})
        tracks = renderer.get('captionTracks', [])
        return tracks if isinstance(tracks, list) else []
    except Exception:
        return []


def _pick_caption_track(
    tracks: List[CaptionTrack],
    preferred: tuple[str, ...] = PREFERRED_LANGUAGES
) -> Optional[CaptionTrack]:
    """우선순위에 따라 자막 트랙을 선택합니다."""
    if not isinstance(tracks, list) or not tracks:
        return None

    pref_list = list(preferred or ())

    def score(track: CaptionTrack) -> tuple[int, int]:
        lang = (track or {}).get('languageCode', '')
        is_asr = (track or {}).get('kind') == 'asr'
        try:
            lang_idx = pref_list.index(lang)
        except ValueError:
            lang_idx = len(pref_list) + 10
        return (lang_idx, 1 if is_asr else 0)

    return min(tracks, key=score)


def _parse_vtt(vtt_text: str) -> str:
    """VTT 형식의 자막을 파싱합니다."""
    if not isinstance(vtt_text, str) or not vtt_text.strip():
        return ""

    lines: List[str] = []
    for raw in vtt_text.splitlines():
        line = raw.strip('\ufeff').strip()
        if not line or line.upper().startswith('WEBVTT') or '-->' in line:
            continue
        if re.match(r'^\d+$', line):
            continue
        line = re.sub(r'<[^>]+>', '', line).strip()
        if line:
            lines.append(line)

    return " ".join(lines)


def _parse_timedtext_xml(xml_text: str) -> str:
    """TimedText XML을 파싱합니다."""
    if not isinstance(xml_text, str) or not xml_text.strip():
        return ""

    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError:
        return ""

    texts: List[str] = []
    for node in root.findall('.//text'):
        if node.text:
            texts.append(html_module.unescape(node.text).replace('\n', ' ').strip())

    return " ".join(filter(None, texts))


def _is_safe_caption_url(url: str) -> bool:
    """자막 URL이 YouTube 도메인인지 검증합니다 (SSRF 방지)."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https'):
            return False
        host = (parsed.hostname or '').lower()
        return host.endswith('.youtube.com') or host.endswith('.google.com') or host.endswith('.googlevideo.com')
    except Exception:
        return False


def _download_caption_from_url(base_url: str) -> str:
    """자막 URL에서 자막을 다운로드합니다.

    P2 버그 #8: 타임아웃 상수 사용 및 예외 처리 강화
    """
    if not isinstance(base_url, str) or not base_url:
        return ""

    if not _is_safe_caption_url(base_url):
        _log_warning(f"안전하지 않은 자막 URL 차단: {base_url[:60]}")
        return ""

    url = base_url
    if 'fmt=' not in url:
        url += ('&' if '?' in url else '?') + 'fmt=vtt'

    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "ko,en-US;q=0.9,en;q=0.8",
    }

    try:
        response = requests.get(url, headers=headers, timeout=(TIMEOUT_CONNECT, TIMEOUT_READ_SHORT),
                                allow_redirects=False)
        response.raise_for_status()
        text = response.text or ""

        if text.lstrip().startswith('WEBVTT'):
            return _parse_vtt(text)
        if '<transcript' in text or '<text' in text:
            return _parse_timedtext_xml(text)

        return text.strip()

    except requests.exceptions.Timeout:
        _log_warning(f"Caption download timeout: {url[:50]}...")
        return ""
    except requests.exceptions.HTTPError as e:
        _log_warning(f"Caption download HTTP error: {e.response.status_code if e.response else 'unknown'}")
        return ""
    except requests.exceptions.RequestException as e:
        _log_warning(f"Caption download failed: {str(e)[:100]}")
        return ""


def _get_transcript_from_watch_page(video_id: str) -> TranscriptResult:
    """Watch 페이지에서 직접 자막을 가져옵니다."""
    if not video_id:
        return {'error': '유효하지 않은 YouTube video_id입니다.'}

    try:
        headers = {
            "User-Agent": USER_AGENT,
            "Accept-Language": "ko,en-US;q=0.9,en;q=0.8",
        }
        watch_url = f"https://www.youtube.com/watch?v={video_id}"

        response = requests.get(watch_url, headers=headers, timeout=HTTP_TIMEOUT)
        response.raise_for_status()

        player = _extract_yt_initial_player_response(response.text)
        tracks = _extract_caption_tracks(player)
        track = _pick_caption_track(tracks)

        if not track:
            return {'error': 'watch 페이지에서 자막 트랙(captionTracks)을 찾지 못했습니다.'}

        text = _download_caption_from_url(track.get('baseUrl', ''))
        if not text:
            return {'error': 'watch 페이지 자막 다운로드에 실패했습니다.'}

        return text

    except Exception as e:
        return {'error': f'watch 페이지 자막 폴백 실패: {str(e)}'}


# ==================== Main Transcript Function ====================

def _log_info(message: str) -> None:
    """안전하게 로그를 기록합니다."""
    try:
        current_app.logger.info(message)
    except RuntimeError:
        pass


def _log_warning(message: str) -> None:
    """안전하게 경고 로그를 기록합니다."""
    try:
        current_app.logger.warning(message)
    except RuntimeError:
        pass


def _detect_auto_caption(ytt_api: YouTubeTranscriptApi, video_id: str) -> bool:
    """현재 가져온 자막이 자동 생성(ASR)인지 판별합니다."""
    try:
        if hasattr(ytt_api, 'list'):
            transcript_list = ytt_api.list(video_id)
            for track in transcript_list:
                if getattr(track, 'is_generated', False):
                    return True
    except Exception:
        pass
    return False


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


def _run_parallel_fallbacks(video_id: str, overall_start: float) -> Optional[dict]:
    """watch_page + yt-dlp + NLM을 병렬 실행하여 첫 성공 결과를 반환."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    _log_info(f"Starting parallel fallback (watch_page + yt-dlp + NLM) for video_id={video_id}")

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(_try_watch_page_fallback, video_id): 'watch_page',
            executor.submit(_try_ytdlp_fallback, video_id): 'ytdlp',
            executor.submit(_try_nlm_fallback, video_id): 'nlm',
        }

        for future in as_completed(futures, timeout=90):
            try:
                res = future.result()
                if res is not None:
                    source_name, text, quality, is_auto = res
                    _log_info(f"Parallel fallback succeeded: {source_name} for video_id={video_id}")
                    for f in futures:
                        f.cancel()
                    return _build_transcript_result(
                        text, source_name, quality, is_auto, overall_start, video_id,
                    )
            except Exception as e:
                _log_warning(f"Parallel fallback {futures[future]} error: {str(e)[:100]}")

    return None


# ==================== 자막 결과 빌더 ====================

def _build_transcript_result(
    text: str, source: str, quality: float, is_auto: bool,
    start_time: float, video_id: str, segments: list = None,
) -> dict:
    """자막 결과 딕셔너리를 생성하고 캐시에 저장한다."""
    source_meta = {
        'source_type': source,
        'quality_score': quality,
        'is_auto': is_auto,
        'language': _detect_language_from_text(text),
    }
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


def get_transcript(video_id: str) -> TranscriptResult:
    """
    YouTube 자막을 가져옵니다.
    Supadata API 키는 환경변수(SUPADATA_API_KEY)에서 로드됩니다.

    Args:
        video_id: YouTube 비디오 ID

    Returns:
        성공: {'text': '자막 내용', 'source': 'api'|'watch'|'supadata'|'cache'}
        실패: {'error': '에러 메시지'}

    우선순위:
    0. 캐시 (있으면 바로 반환)
    1. youtube-transcript-api 라이브러리 (무료)
    2. watch 페이지 직접 파싱 (무료)
    2.5. yt-dlp 자막 직접 추출 (무료, 음성인식 없이)
    3. Supadata API (유료)
    4. Whisper 음성 인식 (로컬, 느림)
    """
    overall_start = time.time()

    # 0순위: 캐시 확인
    cached = _load_cache(video_id, 'transcript')
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
            fetched = _fetch_transcript_with_api(ytt_api, video_id)
            if fetched:
                break
            time.sleep(0.5 * (2 ** attempt))

        if fetched:
            text = _extract_text_from_transcript(fetched)
            if text:
                segments = _extract_segments_from_transcript(fetched)
                is_auto = _detect_auto_caption(ytt_api, video_id)
                return _build_transcript_result(
                    text, 'api', 0.95 if not is_auto else 0.85, is_auto,
                    overall_start, video_id, segments=segments,
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
    parallel_result = _run_parallel_fallbacks(video_id, overall_start)
    if parallel_result:
        return parallel_result

    # ── 순차 폴백: 느리거나 유료인 방법들 ──

    # Whisper 음성 인식 (WHISPER_ENABLED=True일 때만, 무료 로컬 처리)
    whisper_enabled = os.getenv('WHISPER_ENABLED', 'false').lower() == 'true'
    if whisper_enabled:
        _log_info(f"Trying Whisper fallback for video_id={video_id}")
        try:
            from services.transcript.whisper_service import extract_transcript_whisper
            whisper_model = os.getenv('WHISPER_MODEL_SIZE', 'large-v3-turbo')
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            whisper_text = extract_transcript_whisper(video_url, whisper_model)
            if whisper_text and whisper_text.strip():
                _log_info(f"Transcript extracted via Whisper for video_id={video_id}")
                return _build_transcript_result(
                    whisper_text, 'whisper', 0.75, True, overall_start, video_id,
                )
        except Exception as e:
            _log_warning(f"Whisper fallback failed for video_id={video_id}: {str(e)}")

    # Supadata API (유료 - 마지막 폴백)
    if supadata_api_key:
        _log_info(f"Trying Supadata API fallback for video_id={video_id}")
        supadata_result = get_transcript_via_supadata(video_id, supadata_api_key)
        if isinstance(supadata_result, str) and supadata_result.strip():
            _log_info(f"Transcript fetched via Supadata for video_id={video_id}")
            return _build_transcript_result(
                supadata_result, 'supadata', 0.8, False, overall_start, video_id,
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

