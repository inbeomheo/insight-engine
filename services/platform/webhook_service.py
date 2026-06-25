"""
웹훅 서비스 — 콘텐츠 생성 완료 시 외부 웹훅(n8n, Make, Zapier 등)으로 결과 전송
Fire-and-forget 방식으로 메인 플로우를 블로킹하지 않음
"""
import logging
import threading
from datetime import datetime, timezone

import requests

from utils.url_safety import is_safe_public_url

logger = logging.getLogger(__name__)


class WebhookService:
    def __init__(self, url: str, enabled: bool = False, timeout: int = 10):
        self.url = url
        self.timeout = timeout
        self.failure_count = 0
        if enabled and url and not is_safe_public_url(url):
            logger.warning("웹훅 URL이 안전하지 않아 비활성화됨: %s", url)
            self.enabled = False
        else:
            self.enabled = enabled

    def send(self, event: str, data: dict) -> None:
        """웹훅 비동기 전송 (fire-and-forget)"""
        if not self.enabled or not self.url:
            return
        thread = threading.Thread(target=self._send, args=(event, data), daemon=True)
        thread.start()

    def _send(self, event: str, data: dict):
        """실제 HTTP POST 전송 (5xx/네트워크 오류만 1회 재시도, 4xx는 즉시 중단)"""
        import time as _time

        payload = {
            "event": event,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data": data,
        }
        for attempt in range(2):
            try:
                resp = requests.post(self.url, json=payload, timeout=self.timeout)
                # 4xx 클라이언트 에러는 재시도 무의미 → 즉시 중단
                if 400 <= resp.status_code < 500:
                    self.failure_count += 1
                    logger.error("웹훅 클라이언트 에러 (재시도 안 함): %s %s", resp.status_code, event)
                    return
                resp.raise_for_status()
                logger.info("웹훅 전송 성공: %s", event)
                return
            except Exception as e:
                if attempt == 0:
                    logger.warning("웹훅 전송 실패 (2초 후 재시도): %s", e)
                    _time.sleep(2)
                else:
                    self.failure_count += 1
                    logger.error("웹훅 전송 최종 실패: %s", e)

    def test(self) -> dict:
        """웹훅 테스트 전송 (동기, 결과 반환)"""
        if not self.url:
            return {"success": False, "error": "웹훅 URL이 설정되지 않았습니다."}
        payload = {
            "event": "webhook.test",
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data": {"message": "Insight Engine 웹훅 테스트"},
        }
        try:
            resp = requests.post(self.url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            return {"success": True, "status_code": resp.status_code}
        except Exception as e:
            return {"success": False, "error": str(e)}
