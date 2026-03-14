"""Flask 확장 모듈 — 블루프린트에서 공유할 확장 인스턴스 정의"""
import os
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

_storage_uri = os.getenv('REDIS_URL', 'memory://')

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    storage_uri=_storage_uri,
    storage_options={"socket_connect_timeout": 3} if _storage_uri.startswith("redis") else {},
    enabled=os.getenv('RATE_LIMIT_ENABLED', 'true').lower() == 'true',
)
