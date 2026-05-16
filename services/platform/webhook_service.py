"""
웹훅 서비스 — 콘텐츠 생성 완료 시 외부 웹훅(n8n, Make, Zapier 등)으로 결과 전송
Fire-and-forget 방식으로 메인 플로우를 블로킹하지 않음
"""
import ipaddress
import logging
import threading
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)


# 클라우드 메타데이터 엔드포인트 등 위험한 호스트명 차단
_BLOCKED_HOSTNAMES = frozenset({
    'localhost',
    'metadata.google.internal',      # GCP 메타데이터
    'metadata.internal',
    'instance-data',                  # AWS 메타데이터 별칭
})


def _build_webhook_payload(event: str, data: dict, now=None) -> dict:
    """Build the standard webhook payload."""
    timestamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return {
        "event": event,
        "timestamp": timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "data": data,
    }


def _is_dangerous_ip(addr: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """IP 주소가 사설/루프백/예약/링크로컬인지 검사합니다."""
    if addr.is_private or addr.is_loopback or addr.is_reserved or addr.is_link_local:
        return True
    # IPv4-mapped IPv6 (::ffff:127.0.0.1 등) 우회 차단
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped:
        mapped = addr.ipv4_mapped
        if mapped.is_private or mapped.is_loopback or mapped.is_reserved or mapped.is_link_local:
            return True
    return False


def _validate_webhook_url(url: str) -> bool:
    """웹훅 URL의 안전성을 검증합니다 (SSRF 방지).

    - http/https 스키마만 허용
    - 사설 IP, 루프백, localhost, 클라우드 메타데이터 엔드포인트 차단
    - 도메인인 경우 DNS 해석 후 실제 IP까지 검증 (TOCTOU 방어)
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return False

    if parsed.scheme not in ('http', 'https'):
        return False

    hostname = parsed.hostname
    if not hostname:
        return False

    # 알려진 위험 호스트명 차단
    if hostname.lower() in _BLOCKED_HOSTNAMES:
        return False

    # IP 리터럴 검사
    try:
        addr = ipaddress.ip_address(hostname)
        if _is_dangerous_ip(addr):
            return False
        return True
    except ValueError:
        pass

    # 도메인인 경우 — DNS 해석 후 실제 IP 검증 (DNS 리바인딩 부분 방어)
    import socket
    try:
        resolved = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        for family, _type, _proto, _canonname, sockaddr in resolved:
            ip_str = sockaddr[0]
            try:
                addr = ipaddress.ip_address(ip_str)
                if _is_dangerous_ip(addr):
                    logger.warning("웹훅 DNS 해석 결과 위험한 IP 감지: %s → %s", hostname, ip_str)
                    return False
            except ValueError:
                continue
    except socket.gaierror:
        # DNS 해석 실패 — 존재하지 않는 도메인이므로 차단
        return False

    return True


class WebhookService:
    def __init__(self, url: str, enabled: bool = False, timeout: int = 10):
        self.url = url
        self.timeout = timeout
        self.failure_count = 0
        if enabled and url and not _validate_webhook_url(url):
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

        payload = _build_webhook_payload(event, data)
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
        payload = _build_webhook_payload(
            "webhook.test",
            {"message": "Insight Engine 웹훅 테스트"},
        )
        try:
            resp = requests.post(self.url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            return {"success": True, "status_code": resp.status_code}
        except Exception as e:
            return {"success": False, "error": str(e)}
