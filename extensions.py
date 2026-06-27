"""Flask 확장 모듈 — 블루프린트에서 공유할 확장 인스턴스 정의"""
import os
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

_storage_uri = os.getenv('REDIS_URL', 'memory://')
_is_redis_storage = _storage_uri.startswith(('redis://', 'rediss://'))


def _env_truthy(name: str, default: str = 'true') -> bool:
    return (os.getenv(name, default) or default).strip().lower() not in {'0', 'false', 'no', 'off'}


limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    storage_uri=_storage_uri,
    storage_options={"socket_connect_timeout": 3} if _is_redis_storage else {},
    enabled=_env_truthy('RATE_LIMIT_ENABLED', 'true'),
)
