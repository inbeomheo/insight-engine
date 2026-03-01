"""
웹훅 서비스 — 콘텐츠 생성 완료 시 외부 웹훅(n8n, Make, Zapier 등)으로 결과 전송
Fire-and-forget 방식으로 메인 플로우를 블로킹하지 않음
"""
import logging
import threading
from datetime import datetime, timezone

import requests

logger = logging.getLogger(__name__)


class WebhookService:
    def __init__(self, url: str, enabled: bool = False, timeout: int = 10):
        self.url = url
        self.enabled = enabled
        self.timeout = timeout

    def send(self, event: str, data: dict):
        """웹훅 비동기 전송 (fire-and-forget)"""
        if not self.enabled or not self.url:
            return
        thread = threading.Thread(target=self._send, args=(event, data), daemon=True)
        thread.start()

    def _send(self, event: str, data: dict):
        """실제 HTTP POST 전송 (재시도 1회)"""
        payload = {
            "event": event,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data": data,
        }
        for attempt in range(2):
            try:
                resp = requests.post(self.url, json=payload, timeout=self.timeout)
                resp.raise_for_status()
                logger.info(f"웹훅 전송 성공: {event}")
                return
            except Exception as e:
                if attempt == 0:
                    logger.warning(f"웹훅 전송 실패 (재시도): {e}")
                else:
                    logger.error(f"웹훅 전송 최종 실패: {e}")

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
