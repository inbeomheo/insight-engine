"""YouTube 재생목록·채널 URL 탐지와 영상 목록 조회."""
from __future__ import annotations

import functools
import os
import re
from typing import Any, Callable, Dict, Optional

from services.transcript._shared import log_warning as _log_warning
from services.usage.usage_lock import UsageLockUnavailable


@functools.lru_cache(maxsize=1)
def _get_youtube_build():
    """googleapiclient build 함수를 지연 로딩합니다."""
    from googleapiclient.discovery import build
    return build


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
    return any(pattern.search(url) for pattern in PLAYLIST_URL_PATTERNS)


def is_channel_url(url: str) -> bool:
    """URL이 YouTube 채널 URL인지 확인합니다."""
    if not url:
        return False
    return any(pattern.search(url) for pattern in CHANNEL_URL_PATTERNS)


def _get_playlist_id(url: str) -> Optional[str]:
    """URL에서 재생목록 ID를 추출합니다."""
    for pattern in PLAYLIST_URL_PATTERNS:
        match = pattern.search(url)
        if match:
            return match.group(1)
    return None


def _get_channel_identifier(url: str) -> Optional[Dict[str, str]]:
    """URL에서 채널 식별자를 추출합니다."""
    match = re.search(r'youtube\.com/@([\w.-]+)', url)
    if match:
        return {'type': 'handle', 'value': match.group(1)}

    match = re.search(r'youtube\.com/channel/(UC[\w-]+)', url)
    if match:
        return {'type': 'id', 'value': match.group(1)}

    match = re.search(r'youtube\.com/c/([\w.-]+)', url)
    if match:
        return {'type': 'custom', 'value': match.group(1)}

    return None


def _execute_youtube_request(
    provider_request: Any,
    on_cost_start: Optional[Callable[[], None]],
) -> Any:
    """Execute one quota-bearing YouTube API request at the cost boundary."""
    from services.usage.usage_decorator import mark_usage_charge_committed

    if callable(on_cost_start):
        on_cost_start()
    else:
        mark_usage_charge_committed()
    return provider_request.execute()


def get_playlist_videos(
    url: str,
    max_results: int = 10,
    on_cost_start: Optional[Callable[[], None]] = None,
) -> Dict[str, Any]:
    """재생목록에서 영상 목록을 가져옵니다."""
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
        provider_request = youtube.playlistItems().list(
            part='snippet',
            playlistId=playlist_id,
            maxResults=max_results,
        )
        response = _execute_youtube_request(provider_request, on_cost_start)

        videos = []
        for item in response.get('items', []):
            snippet = item.get('snippet', {})
            video_id = snippet.get('resourceId', {}).get('videoId')
            if video_id:
                videos.append({
                    'videoId': video_id,
                    'title': snippet.get('title', ''),
                    'thumbnail': snippet.get(
                        'thumbnails', {}
                    ).get('medium', {}).get('url', ''),
                })

        total = response.get('pageInfo', {}).get('totalResults', len(videos))
        return {'videos': videos, 'total': total}

    except UsageLockUnavailable:
        raise
    except HttpError as exc:
        status = getattr(getattr(exc, 'resp', None), 'status', 'unknown')
        _log_warning(f"Playlist API error: status={status}")
        return {'error': f'재생목록 조회 실패: {status}'}
    except Exception as exc:
        _log_warning(f"Playlist fetch error: type={type(exc).__name__}")
        return {'error': '재생목록 영상 목록을 가져올 수 없습니다.'}


def get_channel_videos(
    url: str,
    max_results: int = 10,
    on_cost_start: Optional[Callable[[], None]] = None,
) -> Dict[str, Any]:
    """채널에서 최신 영상 목록을 가져옵니다."""
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

        channel_id = None
        if identifier['type'] == 'id':
            channel_id = identifier['value']
        else:
            search_query = (
                f"@{identifier['value']}"
                if identifier['type'] == 'handle'
                else identifier['value']
            )
            search_request = youtube.search().list(
                part='snippet',
                q=search_query,
                type='channel',
                maxResults=1,
            )
            search_response = _execute_youtube_request(
                search_request,
                on_cost_start,
            )
            items = search_response.get('items', [])
            if items:
                channel_id = items[0]['snippet']['channelId']

        if not channel_id:
            return {'error': '채널을 찾을 수 없습니다.'}

        channel_request = youtube.channels().list(
            part='contentDetails',
            id=channel_id,
        )
        channel_response = _execute_youtube_request(
            channel_request,
            on_cost_start,
        )
        channel_items = channel_response.get('items', [])
        if not channel_items:
            return {'error': '채널 정보를 가져올 수 없습니다.'}

        uploads_id = channel_items[0][
            'contentDetails'
        ]['relatedPlaylists']['uploads']
        playlist_request = youtube.playlistItems().list(
            part='snippet',
            playlistId=uploads_id,
            maxResults=max_results,
        )
        playlist_response = _execute_youtube_request(
            playlist_request,
            on_cost_start,
        )

        videos = []
        for item in playlist_response.get('items', []):
            snippet = item.get('snippet', {})
            video_id = snippet.get('resourceId', {}).get('videoId')
            if video_id:
                videos.append({
                    'videoId': video_id,
                    'title': snippet.get('title', ''),
                    'thumbnail': snippet.get(
                        'thumbnails', {}
                    ).get('medium', {}).get('url', ''),
                })

        total = playlist_response.get(
            'pageInfo', {}
        ).get('totalResults', len(videos))
        return {'videos': videos, 'total': total}

    except UsageLockUnavailable:
        raise
    except HttpError as exc:
        status = getattr(getattr(exc, 'resp', None), 'status', 'unknown')
        _log_warning(f"Channel API error: status={status}")
        return {'error': f'채널 조회 실패: {status}'}
    except Exception as exc:
        _log_warning(f"Channel fetch error: type={type(exc).__name__}")
        return {'error': '채널 영상 목록을 가져올 수 없습니다.'}


__all__ = [
    'CHANNEL_URL_PATTERNS',
    'PLAYLIST_URL_PATTERNS',
    '_get_channel_identifier',
    '_get_playlist_id',
    'get_channel_videos',
    'get_playlist_videos',
    'is_channel_url',
    'is_playlist_url',
]
