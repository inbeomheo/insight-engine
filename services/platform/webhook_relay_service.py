"""
Webhook Relay 서비스 (F7-19)

다수의 웹훅 URL에 동시에 이벤트를 발송합니다.
ThreadPoolExecutor로 병렬 전송, 각 URL별 결과를 수집합니다.
"""
import json
import logging
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

logger = logging.getLogger(__name__)

_MAX_WORKERS = 10
_DEFAULT_TIMEOUT = 15
_MAX_RETRIES = 1


class WebhookRelayService:
    """다중 웹훅 동시 발송 서비스"""

    def send_all(
        self,
        urls: list[str],
        payload: dict,
        headers: Optional[dict] = None,
        timeout: int = _DEFAULT_TIMEOUT,
    ) -> dict:
        """모든 웹훅 URL에 payload를 병렬 전송

        Args:
            urls: 웹훅 URL 목록
            payload: 전송할 JSON 데이터
            headers: 추가 HTTP 헤더
            timeout: 요청 타임아웃 (초)

        Returns:
            {
                "total": int,
                "success": int,
                "failed": int,
                "results": [{"url": str, "success": bool, "status": int, "error": str | None}]
            }
        """
        if not urls:
            return {'total': 0, 'success': 0, 'failed': 0, 'results': []}

        results = []
        workers = min(_MAX_WORKERS, len(urls))

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(self._send_one, url, payload, headers, timeout): url
                for url in urls
            }
            for future in as_completed(futures):
                url = futures[future]
                try:
                    result = future.result()
                except Exception as e:
                    result = {'url': url, 'success': False, 'status': 0, 'error': str(e)}
                results.append(result)

        success_count = sum(1 for r in results if r.get('success'))
        return {
            'total': len(urls),
            'success': success_count,
            'failed': len(urls) - success_count,
            'results': results,
        }

    def _send_one(
        self,
        url: str,
        payload: dict,
        headers: Optional[dict],
        timeout: int,
    ) -> dict:
        """단일 웹훅 URL에 전송 (1회 재시도)"""
        all_headers = {
            'Content-Type': 'application/json',
            'X-Insight-Engine': '1',
        }
        if headers:
            all_headers.update(headers)

        body = json.dumps(payload, ensure_ascii=False).encode()

        for attempt in range(_MAX_RETRIES + 1):
            try:
                req = urllib.request.Request(url, data=body, headers=all_headers)
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    return {
                        'url': url,
                        'success': True,
                        'status': resp.status,
                        'error': None,
                    }
            except urllib.error.HTTPError as e:
                if attempt < _MAX_RETRIES and e.code >= 500:
                    time.sleep(1)
                    continue
                return {
                    'url': url,
                    'success': False,
                    'status': e.code,
                    'error': f'HTTP {e.code}',
                }
            except Exception as e:
                if attempt < _MAX_RETRIES:
                    time.sleep(1)
                    continue
                return {
                    'url': url,
                    'success': False,
                    'status': 0,
                    'error': str(e),
                }

        return {'url': url, 'success': False, 'status': 0, 'error': '재시도 초과'}

    def relay_content_generated(
        self,
        webhook_urls: list[str],
        title: str,
        content: str,
        style: str,
        source_url: str = '',
    ) -> dict:
        """콘텐츠 생성 완료 이벤트 릴레이"""
        payload = {
            'event': 'content.generated',
            'data': {
                'title': title,
                'style': style,
                'source_url': source_url,
                'content_preview': content[:500],
                'content_length': len(content),
            },
            'timestamp': time.time(),
        }
        return self.send_all(webhook_urls, payload)


webhook_relay_service = WebhookRelayService()
