"""Flask 확장 모듈 — 블루프린트에서 공유할 확장 인스턴스 정의

프로덕션에서는 REDIS_URL이 반드시 설정되어야 합니다. 멀티 워커 환경에서
memory:// 백엔드는 워커별로 카운터가 분리되어 사실상 rate limiting이 작동하지
않습니다.
"""
import os
import logging

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

logger = logging.getLogger(__name__)

_redis_url = os.getenv('REDIS_URL', '').strip()
_flask_env = os.getenv('FLASK_ENV', '').strip().lower()
_is_production = _flask_env == 'production'

if not _redis_url:
    if _is_production:
        raise RuntimeError(
            "REDIS_URL 환경변수가 필요합니다. 프로덕션 환경에서는 멀티 워커 간 "
            "rate limit 공유를 위해 Redis 백엔드가 필수입니다. "
            "(예: REDIS_URL=redis://redis:6379/0) 또는 FLASK_ENV를 production이 아닌 "
            "값으로 설정하세요."
        )
    _storage_uri = 'memory://'
    logger.warning(
        "REDIS_URL 미설정 → 인메모리 rate limiter 사용 (단일 프로세스 개발용). "
        "프로덕션에서는 REDIS_URL을 반드시 설정하세요."
    )
else:
    _storage_uri = _redis_url

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    storage_uri=_storage_uri,
    storage_options={"socket_connect_timeout": 3} if _storage_uri.startswith("redis") else {},
    enabled=os.getenv('RATE_LIMIT_ENABLED', 'true').lower() == 'true',
)
