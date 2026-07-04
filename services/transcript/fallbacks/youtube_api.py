"""youtube-transcript-api 라이브러리 기반 자막 폴백 (1단계 폴백)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from youtube_transcript_api import (
    YouTubeTranscriptApi,
    NoTranscriptFound,
)

# 버전 호환: 일부 예외는 구버전에는 존재하지 않을 수 있음
try:
    from youtube_transcript_api import (
        PoTokenRequired,
        YouTubeRequestFailed,
        CouldNotRetrieveTranscript,
    )
except ImportError:
    try:
        from youtube_transcript_api import YouTubeTranscriptApiException as _YTBase
    except ImportError:
        class _YTBase(Exception):
            pass
    PoTokenRequired = YouTubeRequestFailed = CouldNotRetrieveTranscript = _YTBase

from services.transcript._shared import (
    PREFERRED_LANGUAGES,
    create_http_session,
)


def build_ytt_api() -> YouTubeTranscriptApi:
    """YouTubeTranscriptApi 인스턴스를 생성합니다."""
    try:
        http_client = create_http_session()
        return YouTubeTranscriptApi(http_client=http_client)
    except Exception:
        return YouTubeTranscriptApi()


def order_transcript_tracks(tracks: List[Any], preferred_language: Optional[str] = None) -> List[Any]:
    """자막 트랙을 우선순위에 따라 정렬합니다.

    Args:
        tracks: 자막 트랙 목록
        preferred_language: 사용자가 요청한 언어 코드(예: 'ko'). 지정 시 해당
            언어 트랙을 최우선으로 배치하고, 없으면 기존 PREFERRED_LANGUAGES 순서로 폴백.
    """
    languages = PREFERRED_LANGUAGES
    if preferred_language:
        languages = (preferred_language,) + tuple(
            lang for lang in PREFERRED_LANGUAGES if lang != preferred_language
        )

    ordered: List[Any] = []
    seen: set = set()
    for is_generated in [False, True]:
        for lang in languages:
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


def fetch_transcript_with_api(
    ytt_api: YouTubeTranscriptApi, video_id: str, preferred_language: Optional[str] = None,
) -> Optional[Any]:
    """youtube-transcript-api를 사용하여 자막을 가져옵니다.

    Args:
        ytt_api: YouTubeTranscriptApi 인스턴스
        video_id: YouTube 비디오 ID
        preferred_language: 사용자가 지정한 자막 언어(예: 'ko'). None이면 기존 기본 순서(PREFERRED_LANGUAGES) 사용.
            지정 언어 트랙이 없으면 기존 순서로 자동 폴백한다(생성 실패로 이어지지 않음).
    """
    fetched = None
    languages = (preferred_language,) + tuple(
        lang for lang in PREFERRED_LANGUAGES if lang != preferred_language
    ) if preferred_language else PREFERRED_LANGUAGES

    if hasattr(ytt_api, "fetch") and hasattr(ytt_api, "list"):
        try:
            fetched = ytt_api.fetch(video_id, languages=languages)
        except (NoTranscriptFound, PoTokenRequired, YouTubeRequestFailed, CouldNotRetrieveTranscript):
            transcript_list = ytt_api.list(video_id)
            ordered_tracks = order_transcript_tracks(list(transcript_list), preferred_language)

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
            ordered_tracks = order_transcript_tracks(list(transcript_list), preferred_language)

            for track in ordered_tracks:
                try:
                    fetched = track.fetch()
                    break
                except Exception:
                    continue
        except Exception:
            try:
                fetched = YouTubeTranscriptApi.get_transcript(video_id, languages=languages)
            except Exception:
                fetched = None

    return fetched


def extract_text_from_transcript(fetched: Any) -> Optional[str]:
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


def extract_segments_from_transcript(fetched: Any) -> List[Dict[str, Any]]:
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


def detect_auto_caption(ytt_api: YouTubeTranscriptApi, video_id: str) -> bool:
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
