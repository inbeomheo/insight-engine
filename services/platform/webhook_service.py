"""
웹훅 서비스 — 콘텐츠 생성 완료 시 외부 웹훅(n8n, Make, Zapier 등)으로 결과 전송
Fire-and-forget 방식으로 메인 플로우를 블로킹하지 않음
"""
import http.client
import json
import logging
import socket
import ssl
import threading
from datetime import datetime, timezone

import requests

from utils.url_safety import (
    ResolvedPublicURL,
    UnsafeURLError,
    is_safe_public_url,
    resolve_public_url,
)

logger = logging.getLogger(__name__)


class _WebhookSecurityError(ValueError):
    """안전하지 않은 웹훅 요청을 네트워크 오류와 구분합니다."""


def _connect_to_ip(target: ResolvedPublicURL, timeout: int) -> socket.socket:
    """DNS를 다시 조회하지 않고 검증된 IPv4/IPv6 주소에 직접 연결합니다."""
    addr = target.ip
    family = socket.AF_INET6 if ':' in addr else socket.AF_INET
    sock = socket.socket(family, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        destination = (addr, target.port, 0, 0) if family == socket.AF_INET6 else (addr, target.port)
        sock.connect(destination)
        return sock
    except Exception:
        sock.close()
        raise


def _post_to_resolved_url(target: ResolvedPublicURL, payload: dict, timeout: int):
    """검증 IP에 POST하고 원래 Host 및 HTTPS 인증서 검증을 보존합니다."""
    sock = _connect_to_ip(target, timeout)
    connection = http.client.HTTPConnection(target.hostname, target.port, timeout=timeout)
    try:
        if target.scheme == 'https':
            context = ssl.create_default_context(cafile=requests.certs.where())
            # server_hostname으로 원래 도메인의 SNI와 인증서 호스트 검증을 유지합니다.
            sock = context.wrap_socket(sock, server_hostname=target.hostname)
        connection.sock = sock

        body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        connection.request(
            'POST',
            target.request_target,
            body=body,
            headers={
                'Host': target.host_header,
                'Content-Type': 'application/json; charset=utf-8',
                'Content-Length': str(len(body)),
                'User-Agent': 'Insight-Engine-Webhook/1.0',
                'Connection': 'close',
            },
        )
        raw_response = connection.getresponse()

        response = requests.Response()
        response.status_code = raw_response.status
        response.reason = raw_response.reason
        response.url = f'{target.scheme}://{target.host_header}{target.request_target}'
        response.headers = requests.structures.CaseInsensitiveDict(raw_response.getheaders())
        # 웹훅 응답 본문은 사용하지 않으므로 메모리 사용량을 제한합니다.
        response._content = raw_response.read(64 * 1024)
        response._content_consumed = True
        response.encoding = requests.utils.get_encoding_from_headers(response.headers)
        return response
    finally:
        connection.close()
        sock.close()


class WebhookService:
    def __init__(self, url: str, enabled: bool = False, timeout: int = 10):
        self.url = url
        self.timeout = timeout
        self.failure_count = 0
        if enabled and url and not is_safe_public_url(url):
            logger.warning("웹훅 URL이 안전하지 않아 비활성화됨")
            self.enabled = False
        else:
            self.enabled = enabled

    def send(self, event: str, data: dict) -> None:
        """웹훅 비동기 전송 (fire-and-forget)"""
        if not self.enabled or not self.url:
            return
        if not is_safe_public_url(self.url):
            logger.warning("웹훅 URL이 안전하지 않아 전송을 차단함")
            return
        thread = threading.Thread(target=self._send, args=(event, data), daemon=True)
        thread.start()

    def _post(self, payload: dict):
        """요청 직전 URL을 해석하고 검증된 IP에 고정하여 POST합니다."""
        try:
            target = resolve_public_url(self.url)
        except UnsafeURLError as exc:
            raise _WebhookSecurityError("안전하지 않은 웹훅 URL입니다.") from exc

        response = _post_to_resolved_url(target, payload, self.timeout)
        if 300 <= response.status_code < 400:
            close = getattr(response, "close", None)
            if callable(close):
                close()
            raise _WebhookSecurityError("웹훅 리다이렉트 응답은 허용되지 않습니다.")
        return response

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
                resp = self._post(payload)
                # 4xx 클라이언트 에러는 재시도 무의미 → 즉시 중단
                if 400 <= resp.status_code < 500:
                    self.failure_count += 1
                    logger.error("웹훅 클라이언트 에러 (재시도 안 함): %s %s", resp.status_code, event)
                    return
                resp.raise_for_status()
                logger.info("웹훅 전송 성공: %s", event)
                return
            except _WebhookSecurityError as e:
                self.failure_count += 1
                logger.error("웹훅 보안 검증 실패: %s", e)
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
            resp = self._post(payload)
            resp.raise_for_status()
            return {"success": True, "status_code": resp.status_code}
        except Exception as e:
            return {"success": False, "error": str(e)}
