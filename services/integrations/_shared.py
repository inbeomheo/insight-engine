"""integrations 패키지 공용 상수.

telegram/slack/discord 봇 서비스가 공유하는 YouTube URL 매칭 정규식.
"""
import re

# YouTube watch/단축 URL 매칭 (봇 메시지에서 URL 추출/검증용)
YOUTUBE_URL_RE = re.compile(
    r'https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[\w-]+'
)
