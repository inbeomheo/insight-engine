"""자막 처리 공유 상수/헬퍼 — 폴백 모듈들이 공통으로 사용.

content_service.py 및 fallbacks/ 서브패키지가 import.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional, Union

import requests
from flask import current_app

# Type aliases
TranscriptResult = Union[str, Dict[str, str]]
CaptionTrack = Dict[str, Any]

# Constants
SUPADATA_API_URL: str = "https://api.supadata.ai/v1/youtube/transcript"
PREFERRED_LANGUAGES: tuple[str, ...] = ("ko", "en")
USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

# HTTP 타임아웃 (초)
TIMEOUT_CONNECT: int = 5
TIMEOUT_READ_SHORT: int = 10
TIMEOUT_READ_MEDIUM: int = 20
TIMEOUT_READ_LONG: int = 30
HTTP_TIMEOUT: tuple[int, int] = (TIMEOUT_CONNECT, TIMEOUT_READ_LONG)  # (connect, read)


def log_info(message: str) -> None:
    """안전하게 로그를 기록합니다 (Flask 컨텍스트 없으면 무시)."""
    try:
        current_app.logger.info(message)
    except RuntimeError:
        pass


def log_warning(message: str) -> None:
    """안전하게 경고 로그를 기록합니다 (Flask 컨텍스트 없으면 무시)."""
    try:
        current_app.logger.warning(message)
    except RuntimeError:
        pass


def get_proxy_config(proxy_type: str) -> Optional[str]:
    """프록시 설정을 가져옵니다 (Flask config > 환경변수)."""
    config_key = f'YT_{proxy_type}_PROXY'
    env_key = f'{proxy_type}_PROXY'

    try:
        proxy = current_app.config.get(config_key)
    except RuntimeError:
        proxy = None

    return proxy or os.getenv(config_key) or os.getenv(env_key)


def create_http_session() -> requests.Session:
    """HTTP 세션을 생성하고 헤더/프록시를 설정합니다."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "en-US,en;q=0.9"
    })

    http_proxy = get_proxy_config('HTTP')
    https_proxy = get_proxy_config('HTTPS')

    if http_proxy or https_proxy:
        session.proxies = {}
        if http_proxy:
            session.proxies['http'] = http_proxy
        if https_proxy:
            session.proxies['https'] = https_proxy

    return session
