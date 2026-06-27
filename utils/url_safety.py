"""Public URL validation and fetch helpers.

These helpers are used before server-side requests to user-controlled URLs.
They block local/private/metadata targets and prevent redirects from turning a
public URL into an internal request.
"""
from __future__ import annotations

import ipaddress
import logging
import os
import socket
from collections.abc import Iterable
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)

_BLOCKED_HOSTNAMES = frozenset({
    "localhost",
    "metadata.google.internal",
    "metadata.internal",
    "instance-data",
})


def is_production() -> bool:
    return (os.getenv("FLASK_ENV") or "").strip().lower() == "production"


def is_dangerous_ip(addr: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Return True for IPs that must not be fetched by server-side URL inputs."""
    if (
        addr.is_private
        or addr.is_loopback
        or addr.is_reserved
        or addr.is_link_local
        or addr.is_multicast
        or addr.is_unspecified
    ):
        return True
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped:
        mapped = addr.ipv4_mapped
        return (
            mapped.is_private
            or mapped.is_loopback
            or mapped.is_reserved
            or mapped.is_link_local
            or mapped.is_multicast
            or mapped.is_unspecified
        )
    return False


def public_url_error(url: str, *, require_https: bool = False, label: str = "URL") -> str | None:
    """Return a validation error for a public http(s) URL, or None if safe.

    The validation includes DNS resolution so hostnames that currently resolve
    to private or metadata IPs are rejected before the caller opens a socket.
    """
    try:
        parsed = urlparse(url)
        port = parsed.port
    except Exception:
        return f"{label} 형식이 올바르지 않습니다."

    if parsed.scheme not in ("http", "https"):
        return f"{label}은 http 또는 https여야 합니다."
    if require_https and parsed.scheme != "https":
        return f"운영 환경에서는 HTTPS {label}만 허용됩니다."

    hostname = parsed.hostname
    if not hostname:
        return f"{label} 호스트가 필요합니다."

    hostname_lower = hostname.lower()
    if hostname_lower in _BLOCKED_HOSTNAMES:
        return f"{label} 호스트가 안전하지 않아 차단되었습니다."

    try:
        addr = ipaddress.ip_address(hostname_lower)
        if is_dangerous_ip(addr):
            return f"{label} IP가 안전하지 않아 차단되었습니다."
        return None
    except ValueError:
        pass

    try:
        resolved = socket.getaddrinfo(hostname_lower, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
        for _family, _type, _proto, _canonname, sockaddr in resolved:
            try:
                addr = ipaddress.ip_address(sockaddr[0])
            except ValueError:
                continue
            if is_dangerous_ip(addr):
                logger.warning("%s DNS 해석 결과 위험한 IP 감지: %s -> %s", label, hostname_lower, sockaddr[0])
                return f"{label} DNS 해석 결과가 안전하지 않아 차단되었습니다."
    except socket.gaierror:
        return f"{label} DNS 해석에 실패했습니다."

    return None


def validate_public_url(url: str, *, require_https: bool = False, label: str = "URL") -> bool:
    return public_url_error(url, require_https=require_https, label=label) is None


def hostname_matches(
    hostname: str | None,
    allowed_hosts: Iterable[str],
    *,
    allow_subdomains: bool = True,
) -> bool:
    """Return True when hostname is one of allowed_hosts or its subdomain."""
    if not hostname:
        return False
    host = hostname.lower().rstrip(".")
    for allowed in allowed_hosts:
        normalized = allowed.lower().rstrip(".")
        if host == normalized:
            return True
        if allow_subdomains and host.endswith(f".{normalized}"):
            return True
    return False


def url_hostname(url: str) -> str | None:
    try:
        return urlparse(url).hostname
    except Exception:
        return None


def fetch_public_url(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: float | tuple[float, float] = 10,
    require_https: bool = False,
    label: str = "URL",
) -> requests.Response:
    """GET a validated public URL without following redirects."""
    url_error = public_url_error(url, require_https=require_https, label=label)
    if url_error:
        raise ValueError(url_error)

    response = requests.get(
        url,
        headers=headers,
        timeout=timeout,
        allow_redirects=False,
    )
    status_code = getattr(response, "status_code", 0)
    if isinstance(status_code, int) and 300 <= status_code < 400:
        raise ValueError(f"{label} 리다이렉트가 차단되었습니다.")
    response.raise_for_status()
    return response
