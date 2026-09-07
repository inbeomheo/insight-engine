"""YouTube 채널 전체 분석 서비스

채널 URL에서 영상 목록을 조회하고, 주제 클러스터링 및 통계를 제공합니다.
"""
import logging
import os
import re
from collections import Counter
from typing import Callable, Dict, List, Optional

import requests

from services.usage.usage_lock import UsageLockUnavailable

logger = logging.getLogger(__name__)

YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY', '')
_API_BASE = 'https://www.googleapis.com/youtube/v3'
_REQUEST_TIMEOUT = 15


def analyze_channel(
    channel_url: str,
    on_cost_start: Optional[Callable[[], None]] = None,
) -> Dict:
    """YouTube 채널을 분석하여 통계와 주제 클러스터를 반환합니다.

    Args:
        channel_url: YouTube 채널 URL
        on_cost_start: YouTube API 호출 직전에 실행할 콜백

    Returns:
        {"channel_name": str, "stats": dict, "topic_clusters": list,
         "recent_videos": list}

    Raises:
        ValueError: API 키 미설정, 유효하지 않은 URL, 채널을 찾을 수 없는 경우
    """
    if not YOUTUBE_API_KEY:
        raise ValueError('YOUTUBE_API_KEY가 설정되지 않았습니다.')

    channel_id = _extract_channel_id(
        channel_url,
        on_cost_start=on_cost_start,
    )
    if not channel_id:
        raise ValueError('유효하지 않은 YouTube 채널 URL입니다.')

    # 채널 기본 정보 조회
    channel_info = _get_channel_info(
        channel_id,
        on_cost_start=on_cost_start,
    )
    if not channel_info:
        raise ValueError('채널 정보를 가져올 수 없습니다.')

    # 최근 영상 목록 조회 (최대 50개)
    videos = _get_recent_videos(
        channel_id,
        max_results=50,
        on_cost_start=on_cost_start,
    )

    # 통계 계산
    stats = _compute_stats(channel_info, videos)

    # 주제 클러스터링
    topic_clusters = _cluster_topics(videos)

    return {
        'channel_name': channel_info.get('title', ''),
        'stats': stats,
        'topic_clusters': topic_clusters,
        'recent_videos': videos[:20],  # UI에는 최근 20개만 반환
    }


def _extract_channel_id(
    url: str,
    on_cost_start: Optional[Callable[[], None]] = None,
) -> Optional[str]:
    """YouTube 채널 URL에서 channel ID를 추출합니다."""
    # /channel/UC... 패턴
    match = re.search(r'/channel/(UC[\w-]+)', url)
    if match:
        return match.group(1)

    # /@handle 또는 /c/customname 패턴 → API로 변환
    handle_match = re.search(r'/@([\w.-]+)', url)
    custom_match = re.search(r'/c/([\w.-]+)', url)
    identifier = None
    if handle_match:
        identifier = handle_match.group(1)
    elif custom_match:
        identifier = custom_match.group(1)

    if identifier:
        if on_cost_start is None:
            return _resolve_channel_id(identifier)
        return _resolve_channel_id(
            identifier,
            on_cost_start=on_cost_start,
        )

    return None


def _resolve_channel_id(
    handle: str,
    on_cost_start: Optional[Callable[[], None]] = None,
) -> Optional[str]:
    """핸들 또는 커스텀 이름으로 채널 ID를 조회합니다."""
    try:
        # forHandle 파라미터로 조회
        if on_cost_start is not None:
            on_cost_start()
        resp = requests.get(
            f'{_API_BASE}/channels',
            params={
                'key': YOUTUBE_API_KEY,
                'forHandle': handle,
                'part': 'id',
            },
            timeout=_REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        items = resp.json().get('items', [])
        if items:
            return items[0]['id']

        # forUsername 폴백
        if on_cost_start is not None:
            on_cost_start()
        resp = requests.get(
            f'{_API_BASE}/channels',
            params={
                'key': YOUTUBE_API_KEY,
                'forUsername': handle,
                'part': 'id',
            },
            timeout=_REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        items = resp.json().get('items', [])
        if items:
            return items[0]['id']

    except UsageLockUnavailable:
        raise
    except Exception as exc:
        logger.warning(
            "채널 ID 조회 실패 (@%s, type=%s)",
            handle,
            type(exc).__name__,
        )

    return None


def _get_channel_info(
    channel_id: str,
    on_cost_start: Optional[Callable[[], None]] = None,
) -> Optional[Dict]:
    """채널 기본 정보(제목, 구독자 수, 영상 수)를 조회합니다."""
    try:
        if on_cost_start is not None:
            on_cost_start()
        resp = requests.get(
            f'{_API_BASE}/channels',
            params={
                'key': YOUTUBE_API_KEY,
                'id': channel_id,
                'part': 'snippet,statistics',
            },
            timeout=_REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        items = resp.json().get('items', [])
        if not items:
            return None

        item = items[0]
        snippet = item.get('snippet', {})
        statistics = item.get('statistics', {})

        return {
            'title': snippet.get('title', ''),
            'description': snippet.get('description', ''),
            'subscriber_count': int(statistics.get('subscriberCount', 0)),
            'video_count': int(statistics.get('videoCount', 0)),
            'view_count': int(statistics.get('viewCount', 0)),
        }
    except UsageLockUnavailable:
        raise
    except Exception as exc:
        logger.error(
            "채널 정보 조회 실패 (%s, type=%s)",
            channel_id,
            type(exc).__name__,
        )
        return None


def _get_recent_videos(
    channel_id: str,
    max_results: int = 50,
    on_cost_start: Optional[Callable[[], None]] = None,
) -> List[Dict]:
    """채널의 최근 영상 목록을 조회합니다."""
    try:
        if on_cost_start is not None:
            on_cost_start()
        resp = requests.get(
            f'{_API_BASE}/search',
            params={
                'key': YOUTUBE_API_KEY,
                'channelId': channel_id,
                'order': 'date',
                'maxResults': min(max_results, 50),
                'type': 'video',
                'part': 'snippet',
            },
            timeout=_REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        items = resp.json().get('items', [])

        video_ids = [item['id']['videoId'] for item in items if 'videoId' in item.get('id', {})]
        if not video_ids:
            return []

        # 조회수 등 상세 통계 조회
        stats_map = _get_video_stats(
            video_ids,
            on_cost_start=on_cost_start,
        )

        videos = []
        for item in items:
            vid = item.get('id', {}).get('videoId')
            if not vid:
                continue
            snippet = item.get('snippet', {})
            stat = stats_map.get(vid, {})
            videos.append({
                'video_id': vid,
                'title': snippet.get('title', ''),
                'description': snippet.get('description', ''),
                'published_at': snippet.get('publishedAt', ''),
                'view_count': stat.get('viewCount', 0),
                'like_count': stat.get('likeCount', 0),
            })

        return videos
    except UsageLockUnavailable:
        raise
    except Exception as exc:
        logger.error(
            "최근 영상 조회 실패 (%s, type=%s)",
            channel_id,
            type(exc).__name__,
        )
        return []


def _get_video_stats(
    video_ids: List[str],
    on_cost_start: Optional[Callable[[], None]] = None,
) -> Dict[str, Dict]:
    """영상 ID 목록의 조회수/좋아요 통계를 조회합니다."""
    try:
        if on_cost_start is not None:
            on_cost_start()
        resp = requests.get(
            f'{_API_BASE}/videos',
            params={
                'key': YOUTUBE_API_KEY,
                'id': ','.join(video_ids),
                'part': 'statistics',
            },
            timeout=_REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        items = resp.json().get('items', [])

        stats = {}
        for item in items:
            s = item.get('statistics', {})
            stats[item['id']] = {
                'viewCount': int(s.get('viewCount', 0)),
                'likeCount': int(s.get('likeCount', 0)),
            }
        return stats
    except UsageLockUnavailable:
        raise
    except Exception as exc:
        logger.warning(
            "영상 통계 조회 실패 (type=%s)",
            type(exc).__name__,
        )
        return {}


def _compute_stats(channel_info: Dict, videos: List[Dict]) -> Dict:
    """채널 통계를 계산합니다."""
    view_counts = [v.get('view_count', 0) for v in videos if v.get('view_count')]
    avg_views = round(sum(view_counts) / len(view_counts)) if view_counts else 0

    return {
        'total_videos': channel_info.get('video_count', 0),
        'total_views': channel_info.get('view_count', 0),
        'subscriber_count': channel_info.get('subscriber_count', 0),
        'recent_video_count': len(videos),
        'avg_views_recent': avg_views,
    }


def _cluster_topics(videos: List[Dict], top_n: int = 5) -> List[Dict]:
    """영상 제목/설명에서 키워드를 추출하여 주제 클러스터를 생성합니다.

    간단한 키워드 빈도 기반 클러스터링을 사용합니다.
    """
    # 불용어 (한국어 + 영어 일반)
    stopwords = {
        '의', '가', '이', '은', '는', '을', '를', '에', '에서', '와', '과', '도',
        '로', '으로', '그', '저', '것', '수', '등', '및', '더', '한', '하', '합',
        'the', 'a', 'an', 'is', 'are', 'was', 'in', 'on', 'at', 'to', 'for',
        'of', 'and', 'or', 'but', 'with', 'this', 'that', 'it', 'my', 'your',
        'how', 'what', 'why', 'who', 'when', 'where',
    }

    word_counter: Counter = Counter()

    for video in videos:
        text = f"{video.get('title', '')} {video.get('description', '')}"
        # 한글 단어 (2글자 이상) + 영문 단어 (3글자 이상)
        words = re.findall(r'[가-힣]{2,}|[a-zA-Z]{3,}', text)
        for word in words:
            lower = word.lower()
            if lower not in stopwords and len(lower) >= 2:
                word_counter[lower] += 1

    # 상위 N개 키워드
    top_keywords = word_counter.most_common(top_n)
    total = sum(count for _, count in top_keywords) if top_keywords else 1

    return [
        {'topic': keyword, 'count': count, 'ratio': round(count / total, 3)}
        for keyword, count in top_keywords
    ]
