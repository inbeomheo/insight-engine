"""
Flask 확장 모듈 — 블루프린트에서 공유할 확장 인스턴스 정의
"""
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    storage_uri="memory://",
)
