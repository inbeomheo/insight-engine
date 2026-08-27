"""
URL 안전성 검증 유틸리티 — SSRF(Server-Side Request Forgery) 방지

사용자가 제공한 URL을 서버가 직접 fetch하기 전에 안전성을 검증합니다.
사설 IP/루프백/예약/링크로컬 주소, localhost, 클라우드 메타데이터 엔드포인트를 차단하고,
도메인은 DNS 해석 후 실제 IP까지 검증합니다. 네트워크 호출자는
``resolve_public_url``이 반환한 IP에 직접 연결해야 DNS 재바인딩을 방어할 수 있습니다.
"""
from dataclasses import dataclass
import http.client
import ipaddress
import logging
import re
import socket
import ssl
from urllib.parse import quote, urljoin, urlparse

import requests

logger = logging.getLogger(__name__)


# 클라우드 메타데이터 엔드포인트 등 위험한 호스트명 차단
BLOCKED_HOSTNAMES = frozenset({
    'localhost',
    'metadata.google.internal',      # GCP 메타데이터
    'metadata.internal',
    'instance-data',                  # AWS 메타데이터 별칭
})


class UnsafeURLError(ValueError):
    """공인 네트워크 대상으로 안전하게 해석할 수 없는 URL입니다."""


class PublicFetchTooLarge(requests.RequestException):
    """안전 fetch 응답이 호출자가 정한 바이트 상한을 초과했습니다."""


@dataclass(frozen=True)
class ResolvedPublicURL:
    """검증을 마친 URL과 실제 연결에 사용할 고정 IP입니다."""

    scheme: str
    hostname: str
    port: int
    ip: str
    request_target: str
    host_header: str


_VALID_PERCENT_ESCAPE = re.compile(r"%[0-9A-Fa-f]{2}")
_PATH_SAFE = "/:@!$&'()*+,;=-._~"
_QUERY_SAFE = "/?:@!$&'()*+,;=-._~"
_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})


def _quote_iri_component(value: str, safe: str) -> str:
    """기존 유효 escape는 보존하고 IRI 문자를 UTF-8 percent-encode합니다."""
    encoded: list[str] = []
    index = 0
    while index < len(value):
        if value[index] == '%' and _VALID_PERCENT_ESCAPE.match(value, index):
            encoded.append(value[index:index + 3].upper())
            index += 3
            continue
        encoded.append(quote(value[index], safe=safe, encoding='utf-8'))
        index += 1
    return ''.join(encoded)


def is_dangerous_ip(addr: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """IP 주소가 인터넷에서 직접 접근 가능한 공인 주소가 아닌지 검사합니다."""
    # IPv4-mapped IPv6 (::ffff:127.0.0.1 등) 우회 차단
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped:
        return not addr.ipv4_mapped.is_global
    return not addr.is_global


def resolve_public_url(url: str) -> ResolvedPublicURL:
    """URL을 검증하고 한 번 검증한 공인 IP를 반환합니다.

    반환된 ``ip``를 실제 소켓 연결 대상으로 사용해야 합니다. 호스트명을 다시
    해석하면 검증과 연결 사이 DNS 재바인딩 공격에 노출됩니다.
    """
    if not isinstance(url, str):
        raise UnsafeURLError("URL은 문자열이어야 합니다.")
    if any(ord(char) < 0x20 or ord(char) == 0x7f for char in url):
        raise UnsafeURLError("제어 문자가 포함된 URL은 허용되지 않습니다.")

    try:
        parsed = urlparse(url)
        port = parsed.port
    except (TypeError, ValueError) as exc:
        raise UnsafeURLError("올바르지 않은 URL입니다.") from exc

    scheme = parsed.scheme.lower()
    if scheme not in ('http', 'https'):
        raise UnsafeURLError("HTTP 또는 HTTPS URL만 허용됩니다.")

    hostname = parsed.hostname
    if not hostname:
        raise UnsafeURLError("URL 호스트가 필요합니다.")
    if parsed.username is not None or parsed.password is not None:
        raise UnsafeURLError("사용자 정보가 포함된 URL은 허용되지 않습니다.")

    try:
        hostname = hostname.rstrip('.').encode('idna').decode('ascii').lower()
    except UnicodeError as exc:
        raise UnsafeURLError("올바르지 않은 URL 호스트입니다.") from exc
    if not hostname:
        raise UnsafeURLError("URL 호스트가 필요합니다.")

    if hostname in BLOCKED_HOSTNAMES:
        raise UnsafeURLError("차단된 URL 호스트입니다.")
    if '%' in hostname:
        # IPv6 zone id는 로컬 인터페이스를 지정할 수 있으므로 허용하지 않습니다.
        raise UnsafeURLError("IPv6 zone id가 포함된 URL은 허용되지 않습니다.")

    if port is None:
        port = 443 if scheme == 'https' else 80
    elif port < 1:
        raise UnsafeURLError("URL 포트 범위가 올바르지 않습니다.")
    resolved_ips: list[str] = []

    try:
        literal = ipaddress.ip_address(hostname)
    except ValueError:
        try:
            answers = socket.getaddrinfo(
                hostname,
                port,
                socket.AF_UNSPEC,
                socket.SOCK_STREAM,
            )
        except (socket.gaierror, OSError) as exc:
            raise UnsafeURLError("URL 호스트를 해석할 수 없습니다.") from exc

        for _family, _type, _proto, _canonname, sockaddr in answers:
            ip_str = sockaddr[0]
            try:
                addr = ipaddress.ip_address(ip_str)
            except ValueError as exc:
                raise UnsafeURLError("DNS가 올바르지 않은 IP를 반환했습니다.") from exc
            if is_dangerous_ip(addr):
                logger.warning("URL DNS 해석 결과 위험한 IP 감지: %s → %s", hostname, ip_str)
                raise UnsafeURLError("DNS가 공인 IP가 아닌 주소를 반환했습니다.")
            normalized = str(addr)
            if normalized not in resolved_ips:
                resolved_ips.append(normalized)
    else:
        if is_dangerous_ip(literal):
            raise UnsafeURLError("공인 IP가 아닌 URL은 허용되지 않습니다.")
        resolved_ips.append(str(literal))

    if not resolved_ips:
        raise UnsafeURLError("URL 호스트의 IP를 찾을 수 없습니다.")

    try:
        request_target = _quote_iri_component(parsed.path or '/', _PATH_SAFE)
        if parsed.query:
            request_target += f'?{_quote_iri_component(parsed.query, _QUERY_SAFE)}'
    except UnicodeError as exc:
        raise UnsafeURLError("올바르지 않은 URL 경로입니다.") from exc

    host_for_header = f'[{hostname}]' if ':' in hostname else hostname
    default_port = 443 if scheme == 'https' else 80
    host_header = host_for_header if port == default_port else f'{host_for_header}:{port}'

    return ResolvedPublicURL(
        scheme=scheme,
        hostname=hostname,
        port=port,
        ip=resolved_ips[0],
        request_target=request_target,
        host_header=host_header,
    )


def _connect_to_public_ip(target: ResolvedPublicURL, timeout: float) -> socket.socket:
    """DNS를 다시 조회하지 않고 검증을 마친 IP에 직접 연결합니다."""
    family = socket.AF_INET6 if ':' in target.ip else socket.AF_INET
    sock = socket.socket(family, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    destination = (
        (target.ip, target.port, 0, 0)
        if family == socket.AF_INET6
        else (target.ip, target.port)
    )
    try:
        sock.connect(destination)
        return sock
    except Exception:
        sock.close()
        raise


def _response_url(target: ResolvedPublicURL) -> str:
    return f'{target.scheme}://{target.host_header}{target.request_target}'


def _read_bounded_body(raw_response, max_bytes: int) -> bytes:
    """Content-Length와 실제 스트림 모두에 바이트 상한을 적용합니다."""
    content_length = raw_response.getheader('Content-Length')
    if content_length is not None:
        try:
            declared_length = int(content_length)
        except (TypeError, ValueError) as exc:
            raise requests.RequestException(
                '올바르지 않은 Content-Length 응답입니다.'
            ) from exc
        if declared_length < 0:
            raise requests.RequestException('올바르지 않은 Content-Length 응답입니다.')
        if declared_length > max_bytes:
            raise PublicFetchTooLarge('응답이 허용 크기를 초과했습니다.')

    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = raw_response.read(min(64 * 1024, max_bytes + 1 - total))
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
        if total > max_bytes:
            raise PublicFetchTooLarge('응답이 허용 크기를 초과했습니다.')
    return b''.join(chunks)


def _get_from_public_target(
    target: ResolvedPublicURL,
    *,
    headers: dict[str, str],
    timeout: tuple[float, float],
    max_bytes: int,
) -> requests.Response:
    """검증된 IP로 GET하며 원래 호스트의 Host/SNI/인증서를 유지합니다."""
    connect_timeout, read_timeout = timeout
    sock = _connect_to_public_ip(target, connect_timeout)
    connection = http.client.HTTPConnection(
        target.hostname,
        target.port,
        timeout=read_timeout,
    )
    try:
        if target.scheme == 'https':
            context = ssl.create_default_context(cafile=requests.certs.where())
            sock = context.wrap_socket(sock, server_hostname=target.hostname)
        sock.settimeout(read_timeout)
        connection.sock = sock
        connection.request(
            'GET',
            target.request_target,
            headers={
                **headers,
                'Host': target.host_header,
                'Connection': 'close',
            },
        )
        raw_response = connection.getresponse()
        response = requests.Response()
        response.status_code = raw_response.status
        response.reason = raw_response.reason
        response.url = _response_url(target)
        response.headers = requests.structures.CaseInsensitiveDict(
            raw_response.getheaders()
        )
        if response.status_code in _REDIRECT_STATUSES:
            content = b''
        else:
            content = _read_bounded_body(raw_response, max_bytes)

        # requests.Response.iter_content()는 이 플래그가 False이고 raw가 None이면
        # raw.stream을 호출해 실패합니다. 합성 응답은 이미 전부 읽었음을 명시합니다.
        response._content = content
        response._content_consumed = True
        response.encoding = requests.utils.get_encoding_from_headers(response.headers)
        return response
    finally:
        connection.close()
        sock.close()


def fetch_public_url(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: tuple[float, float] | float = (5, 15),
    max_bytes: int = 2 * 1024 * 1024,
    max_redirects: int = 3,
) -> requests.Response:
    """공인 IP에 고정해 GET하고 리다이렉트마다 다시 검증합니다.

    반환 응답은 메모리에 ``max_bytes``까지만 보관하며 실제
    ``requests.Response.iter_content``/``json`` API와 호환됩니다.
    """
    if max_bytes < 0 or max_redirects < 0:
        raise ValueError('크기 및 리다이렉트 제한은 음수일 수 없습니다.')
    if isinstance(timeout, (int, float)):
        normalized_timeout = (float(timeout), float(timeout))
    else:
        normalized_timeout = (float(timeout[0]), float(timeout[1]))

    current_url = url
    request_headers = dict(headers or {})
    for redirect_count in range(max_redirects + 1):
        target = resolve_public_url(current_url)
        try:
            response = _get_from_public_target(
                target,
                headers=request_headers,
                timeout=normalized_timeout,
                max_bytes=max_bytes,
            )
        except (OSError, ssl.SSLError, http.client.HTTPException) as exc:
            raise requests.RequestException('공인 URL 요청에 실패했습니다.') from exc

        if response.status_code not in _REDIRECT_STATUSES:
            return response
        location = response.headers.get('Location')
        if not location:
            return response
        if redirect_count >= max_redirects:
            raise requests.TooManyRedirects('리다이렉트가 너무 많습니다.')
        current_url = urljoin(response.url, location)

    raise requests.TooManyRedirects('리다이렉트가 너무 많습니다.')


def is_safe_public_url(url: str) -> bool:
    """URL의 안전성을 검증합니다 (SSRF 방지).

    - http/https 스키마만 허용
    - 사설 IP, 루프백, localhost, 클라우드 메타데이터 엔드포인트 차단
    - 도메인인 경우 DNS 해석 후 실제 IP까지 검증 (TOCTOU 방어)
    """
    try:
        resolve_public_url(url)
    except (UnsafeURLError, TypeError):
        return False
    return True
