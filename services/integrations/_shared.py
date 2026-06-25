"""integrations 패키지 공용 상수 + 웹훅 응답 헬퍼.

telegram/slack/discord 봇 서비스가 공유하는 YouTube URL 매칭 정규식과,
Slack/Discord 웹훅 응답을 통일된 결과 dict로 변환하는 헬퍼를 제공한다.
"""
import re
from collections.abc import Iterable
from typing import Any

# YouTube watch/단축 URL 매칭 (봇 메시지에서 URL 추출/검증용)
YOUTUBE_URL_RE = re.compile(
    r'https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[\w-]+'
)


def disabled_result(reason: str) -> dict[str, Any]:
    """웹훅 미설정 시 반환할 결과 dict."""
    return {'ok': False, 'reason': reason}


def webhook_result(resp: Any, success_codes: Iterable[int]) -> dict[str, Any]:
    """requests.Response를 통일된 결과 dict로 변환.

    success_codes에 응답 status_code가 포함되면 성공.
    호출 측에서 requests.post를 직접 실행해야 한다(테스트가 각 서비스
    모듈의 requests.post를 patch하므로, 실제 POST 호출은 공통화하지 않음).
    """
    if resp.status_code in tuple(success_codes):
        return {'ok': True}
    return {'ok': False, 'status': resp.status_code, 'body': resp.text}
