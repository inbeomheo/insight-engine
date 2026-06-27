"""채널 신규 업로드 감지 서비스"""
import os
import logging
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


def get_latest_video(channel_id: str) -> Optional[dict]:
    """YouTube 채널의 최신 영상 정보를 가져옵니다.

    Returns:
        {'video_id': str, 'title': str, 'published_at': str} or None
    """
    api_key = os.getenv('YOUTUBE_API_KEY', '')
    if not api_key:
        logger.warning("YOUTUBE_API_KEY 미설정")
        return None

    import requests
    try:
        # 채널의 최신 영상 검색
        resp = requests.get(
            'https://www.googleapis.com/youtube/v3/search',
            params={
                'key': api_key,
                'channelId': channel_id,
                'order': 'date',
                'maxResults': 1,
                'type': 'video',
                'part': 'snippet',
            },
            timeout=10,
            allow_redirects=False,
        )
        status_code = getattr(resp, "status_code", 0)
        if isinstance(status_code, int) and 300 <= status_code < 400:
            logger.error("YouTube API 리다이렉트 차단: %s", resp.status_code)
            return None
        resp.raise_for_status()
        items = resp.json().get('items', [])
        if not items:
            return None

        item = items[0]
        return {
            'video_id': item['id']['videoId'],
            'title': item['snippet']['title'],
            'published_at': item['snippet']['publishedAt'],
        }
    except Exception as e:
        logger.error(f"채널 {channel_id} 최신 영상 조회 실패: {e}")
        return None


def check_monitors(supabase_client: Any = None) -> list:
    """활성 모니터를 확인하고 신규 영상이 있으면 목록을 반환합니다.

    Returns:
        [{'monitor_id': str, 'channel_id': str, 'video_id': str, 'style_id': str, 'modifiers': dict}, ...]
    """
    if not supabase_client:
        return []

    try:
        result = supabase_client.table('ie_channel_monitors') \
            .select('*') \
            .eq('is_active', True) \
            .execute()

        monitors = result.data or []
        new_videos = []

        for monitor in monitors:
            latest = get_latest_video(monitor['channel_id'])
            if not latest:
                continue

            # 이전에 처리한 영상과 다르면 신규
            if latest['video_id'] != monitor.get('last_video_id'):
                new_videos.append({
                    'monitor_id': monitor['id'],
                    'user_id': monitor['user_id'],
                    'channel_id': monitor['channel_id'],
                    'video_id': latest['video_id'],
                    'title': latest['title'],
                    'style_id': monitor.get('style_id', 'blog_seo'),
                    'modifiers': monitor.get('modifiers', {}),
                })

                # last_video_id 업데이트
                supabase_client.table('ie_channel_monitors') \
                    .update({
                        'last_video_id': latest['video_id'],
                        'last_checked_at': datetime.now(timezone.utc).isoformat(),
                    }) \
                    .eq('id', monitor['id']) \
                    .execute()

        return new_videos
    except Exception as e:
        logger.error(f"모니터 체크 실패: {e}")
        return []
