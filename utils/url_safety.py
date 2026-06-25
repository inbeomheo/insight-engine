"""
URL 안전성 검증 유틸리티 — SSRF(Server-Side Request Forgery) 방지

사용자가 제공한 URL을 서버가 직접 fetch하기 전에 안전성을 검증합니다.
사설 IP/루프백/예약/링크로컬 주소, localhost, 클라우드 메타데이터 엔드포인트를 차단하고,
도메인은 DNS 해석 후 실제 IP까지 검증하여 DNS 리바인딩을 부분 방어합니다.
"""
import ipaddress
import logging
import socket
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


# 클라우드 메타데이터 엔드포인트 등 위험한 호스트명 차단
BLOCKED_HOSTNAMES = frozenset({
    'localhost',
    'metadata.google.internal',      # GCP 메타데이터
    'metadata.internal',
    'instance-data',                  # AWS 메타데이터 별칭
})


def is_dangerous_ip(addr: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """IP 주소가 사설/루프백/예약/링크로컬인지 검사합니다."""
    if addr.is_private or addr.is_loopback or addr.is_reserved or addr.is_link_local:
        return True
    # IPv4-mapped IPv6 (::ffff:127.0.0.1 등) 우회 차단
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped:
        mapped = addr.ipv4_mapped
        if mapped.is_private or mapped.is_loopback or mapped.is_reserved or mapped.is_link_local:
            return True
    return False


def is_safe_public_url(url: str) -> bool:
    """URL의 안전성을 검증합니다 (SSRF 방지).

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
    if hostname.lower() in BLOCKED_HOSTNAMES:
        return False

    # IP 리터럴 검사
    try:
        addr = ipaddress.ip_address(hostname)
        if is_dangerous_ip(addr):
            return False
        return True
    except ValueError:
        pass

    # 도메인인 경우 — DNS 해석 후 실제 IP 검증 (DNS 리바인딩 부분 방어)
    try:
        resolved = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        for family, _type, _proto, _canonname, sockaddr in resolved:
            ip_str = sockaddr[0]
            try:
                addr = ipaddress.ip_address(ip_str)
                if is_dangerous_ip(addr):
                    logger.warning("URL DNS 해석 결과 위험한 IP 감지: %s → %s", hostname, ip_str)
                    return False
            except ValueError:
                continue
    except socket.gaierror:
        # DNS 해석 실패 — 존재하지 않는 도메인이므로 차단
        return False

    return True
