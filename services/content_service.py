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

import requests
from flask import current_app
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
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
HTTP_TIMEOUT: int = 30
USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

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


def _ensure_cache_dir() -> None:
    """캐시 디렉토리가 존재하는지 확인하고 없으면 생성합니다."""
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)


def _get_cache_path(video_id: str, cache_type: str) -> str:
    """캐시 파일 경로를 반환합니다."""
    return os.path.join(CACHE_DIR, f"{video_id}_{cache_type}.json")


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

    deleted = 0
    for filename in os.listdir(CACHE_DIR):
        if video_id is None or filename.startswith(f"{video_id}_"):
            try:
                os.remove(os.path.join(CACHE_DIR, filename))
                deleted += 1
            except IOError:
                pass
    return deleted


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
            params={"video_id": video_id, "text": "true"},
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
            return None

        if response.status_code == 401:
            return {'error': 'Supadata API 키가 유효하지 않습니다.'}
        if response.status_code == 402:
            return {'error': 'Supadata API 사용량이 초과되었습니다. 플랜을 업그레이드하세요.'}

        return None

    except (requests.exceptions.Timeout, requests.exceptions.RequestException):
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
    for is_generated in [False, True]:
        for lang in PREFERRED_LANGUAGES:
            ordered.extend([
                t for t in tracks
                if getattr(t, 'is_generated', False) == is_generated
                and getattr(t, 'language_code', '') == lang
                and t not in ordered
            ])
        ordered.extend([
            t for t in tracks
            if getattr(t, 'is_generated', False) == is_generated
            and t not in ordered
        ])
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


def _download_caption_from_url(base_url: str) -> str:
    """자막 URL에서 자막을 다운로드합니다."""
    if not isinstance(base_url, str) or not base_url:
        return ""

    url = base_url
    if 'fmt=' not in url:
        url += ('&' if '?' in url else '?') + 'fmt=vtt'

    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "ko,en-US;q=0.9,en;q=0.8",
    }

    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()
    text = response.text or ""

    if text.lstrip().startswith('WEBVTT'):
        return _parse_vtt(text)
    if '<transcript' in text or '<text' in text:
        return _parse_timedtext_xml(text)

    return text.strip()


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

        response = requests.get(watch_url, headers=headers, timeout=15)
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


def get_transcript(video_id: str) -> TranscriptResult:
    """
    YouTube 자막을 가져옵니다.
    Supadata API 키는 환경변수(SUPADATA_API_KEY)에서 로드됩니다.

    Args:
        video_id: YouTube 비디오 ID

    Returns:
        자막 텍스트 문자열 또는 에러 딕셔너리

    우선순위:
    0. 캐시 (있으면 바로 반환)
    1. Supadata API (키가 있는 경우)
    2. youtube-transcript-api 라이브러리
    3. watch 페이지 직접 파싱
    """
    # 0순위: 캐시 확인
    cached = _load_cache(video_id, 'transcript')
    if cached:
        _log_info(f"Transcript loaded from cache for video_id={video_id}")
        return cached

    # 1순위: Supadata API (환경변수에서 키 로드)
    supadata_api_key = os.getenv('SUPADATA_API_KEY', '')
    if supadata_api_key:
        result = get_transcript_via_supadata(video_id, supadata_api_key)
        if isinstance(result, str) and result.strip():
            _log_info(f"Transcript fetched via Supadata for video_id={video_id}")
            _save_cache(video_id, 'transcript', result)
            return result
        if isinstance(result, dict) and result.get('error'):
            return result

    # 2순위: youtube-transcript-api
    try:
        ytt_api = _build_ytt_api()
        fetched = None

        for attempt in range(MAX_RETRY_ATTEMPTS):
            fetched = _fetch_transcript_with_api(ytt_api, video_id)
            if fetched:
                break
            time.sleep(0.5 * (2 ** attempt))

        if not fetched:
            watch_result = _get_transcript_from_watch_page(video_id)
            if isinstance(watch_result, str) and watch_result.strip():
                _log_info(f"Transcript fallback succeeded from watch page for video_id={video_id}")
                _save_cache(video_id, 'transcript', watch_result)
                return watch_result
            if isinstance(watch_result, dict) and watch_result.get('error'):
                _log_warning(f"Transcript fallback failed for video_id={video_id}: {watch_result.get('error')}")
                return watch_result
            return {'error': '자막을 찾을 수 없습니다.'}

        text = _extract_text_from_transcript(fetched)
        if text:
            _save_cache(video_id, 'transcript', text)
            return text
        return {'error': '자막을 가져오지 못했습니다.'}

    except TranscriptsDisabled:
        return {'error': '자막을 가져올 수 없습니다. 이 영상은 자막이 비활성화되어 있습니다.'}
    except NoTranscriptFound:
        return {'error': '자막을 찾을 수 없습니다. 이 영상에 제공되는 자막 트랙이 없습니다.'}
    except PoTokenRequired:
        return {'error': '자막을 가져올 수 없습니다. YouTube가 봇 차단 상태로 판단하여 요청이 거부되었습니다.'}
    except (IpBlocked, RequestBlocked):
        return {'error': '자막을 가져올 수 없습니다. 네트워크/IP 차단으로 YouTube 요청이 거부되었습니다.'}
    except AgeRestricted:
        return {'error': '자막을 가져올 수 없습니다. 연령 제한 콘텐츠입니다.'}
    except VideoUnplayable:
        return {'error': '자막을 가져올 수 없습니다. 재생 불가 영상입니다.'}
    except VideoUnavailable:
        return {'error': '자막을 가져올 수 없습니다. 비공개/삭제/지역 제한 영상입니다.'}
    except InvalidVideoId:
        return {'error': '유효하지 않은 YouTube video_id 입니다.'}
    except (YouTubeRequestFailed, CouldNotRetrieveTranscript) as e:
        msg = str(e)
        if '429' in msg or 'Too Many Requests' in msg:
            return {'error': '자막을 가져올 수 없습니다. 요청이 너무 많아 일시적으로 차단되었습니다.'}
        return {'error': f'자막을 가져올 수 없습니다. YouTube 요청 실패: {msg}'}
    except Exception as e:
        return {'error': f'자막 처리 중 오류 발생: {str(e)}'}


# ==================== YouTube API Functions ====================

def get_youtube_title(video_id: str) -> Optional[str]:
    """YouTube 영상 제목을 가져옵니다."""
    try:
        api_key = current_app.config.get('YOUTUBE_API_KEY')
        if not api_key:
            return None

        youtube = build('youtube', 'v3', developerKey=api_key)
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
        api_key = current_app.config.get('YOUTUBE_API_KEY')
        if not api_key:
            _log_warning("YouTube API key not configured, skipping comments")
            return []

        youtube = build('youtube', 'v3', developerKey=api_key)
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


# ==================== Utilities ====================

def truncate_text(text: str, max_tokens: int) -> str:
    """텍스트를 최대 토큰 수로 자릅니다."""
    if not isinstance(text, str):
        return ""

    tokens = text.split()
    if len(tokens) > max_tokens:
        return " ".join(tokens[:max_tokens]) + "..."
    return text
