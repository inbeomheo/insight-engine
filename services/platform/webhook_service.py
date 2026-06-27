"""웹훅 서비스 — 콘텐츠 생성 완료 시 외부 웹훅(n8n, Make, Zapier 등)으로 결과 전송."""
import logging
import threading
from datetime import datetime, timezone

import requests

from utils.url_safety import (
    is_dangerous_ip as _is_dangerous_ip,
    is_production as _is_production,
    public_url_error,
)

logger = logging.getLogger(__name__)


def _webhook_url_error(url: str, *, require_https: bool = False) -> str | None:
    """웹훅 URL 안전성 오류 메시지를 반환합니다.

    - http/https 스키마만 허용
    - production runtime에서는 https만 허용
    - 사설 IP, 루프백, localhost, 클라우드 메타데이터 엔드포인트 차단
    - 도메인인 경우 DNS 해석 후 실제 IP까지 검증 (TOCTOU 방어)
    """
    return public_url_error(url, require_https=require_https, label='웹훅 URL')


def _validate_webhook_url(url: str) -> bool:
    """웹훅 URL의 SSRF 안전성을 검증합니다."""
    return _webhook_url_error(url) is None


class WebhookService:
    def __init__(self, url: str, enabled: bool = False, timeout: int = 10):
        self.url = (url or '').strip()
        self.timeout = timeout
        self.failure_count = 0
        self._require_https = _is_production()
        self._url_error: str | None = None
        self._url_is_safe = self._refresh_url_safety()
        if enabled and self.url and not self._url_is_safe:
            logger.warning("웹훅 URL이 안전하지 않아 비활성화됨: %s", self._url_error)
            self.enabled = False
        else:
            self.enabled = enabled

    def _refresh_url_safety(self) -> bool:
        if not self.url:
            self._url_error = '웹훅 URL이 설정되지 않았습니다.'
            return False
        self._url_error = _webhook_url_error(self.url, require_https=self._require_https)
        return self._url_error is None

    def send(self, event: str, data: dict) -> None:
        """웹훅 비동기 전송 (fire-and-forget)"""
        if not self.enabled or not self.url or not self._refresh_url_safety():
            return
        thread = threading.Thread(target=self._send, args=(event, data), daemon=True)
        thread.start()

    def _send(self, event: str, data: dict):
        """실제 HTTP POST 전송 (5xx/네트워크 오류만 1회 재시도, 4xx는 즉시 중단)"""
        import time as _time

        if not self.enabled or not self.url or not self._refresh_url_safety():
            return

        payload = {
            "event": event,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data": data,
        }
        for attempt in range(2):
            try:
                resp = requests.post(
                    self.url,
                    json=payload,
                    timeout=self.timeout,
                    allow_redirects=False,
                )
                if 300 <= resp.status_code < 400:
                    self.failure_count += 1
                    logger.error("웹훅 리다이렉트 차단: %s %s", resp.status_code, event)
                    return
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
        if not self._refresh_url_safety():
            return {"success": False, "error": self._url_error or "웹훅 URL이 안전하지 않아 차단되었습니다."}
        payload = {
            "event": "webhook.test",
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data": {"message": "Insight Engine 웹훅 테스트"},
        }
        try:
            resp = requests.post(
                self.url,
                json=payload,
                timeout=self.timeout,
                allow_redirects=False,
            )
            if 300 <= resp.status_code < 400:
                return {
                    "success": False,
                    "status_code": resp.status_code,
                    "error": "웹훅 리다이렉트가 차단되었습니다.",
                }
            resp.raise_for_status()
            return {"success": True, "status_code": resp.status_code}
        except Exception as e:
            return {"success": False, "error": str(e)}
