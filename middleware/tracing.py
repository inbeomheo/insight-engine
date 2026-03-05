"""
요청 추적 미들웨어 (F9-23)
UUID 기반 요청 ID 생성, 로그 컨텍스트 전파
OpenTelemetry 선택적 통합
"""
import logging
import time
import uuid
from contextvars import ContextVar
from functools import wraps
from typing import Optional

from flask import request, g

logger = logging.getLogger(__name__)

# 현재 요청 ID를 스레드/코루틴 컨텍스트에 저장
_request_id_var: ContextVar[str] = ContextVar('request_id', default='')

# OpenTelemetry 선택적 import
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    _OTEL_AVAILABLE = True
except ImportError:
    _OTEL_AVAILABLE = False


def get_request_id() -> str:
    """현재 요청 ID 반환 (없으면 빈 문자열)"""
    return _request_id_var.get('')


def generate_request_id() -> str:
    """새 요청 ID 생성 (UUID4)"""
    return str(uuid.uuid4())


class RequestIdFilter(logging.Filter):
    """로그 레코드에 request_id 필드 자동 추가"""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id() or '-'
        return True


class TracingMiddleware:
    """
    요청 추적 미들웨어

    - X-Request-ID 헤더 전파 (없으면 자동 생성)
    - 요청/응답 로깅
    - g.request_id 저장
    - 응답 헤더에 X-Request-ID 포함
    """

    def __init__(self, app=None):
        self._otel_tracer = None
        if app:
            self.init_app(app)

    def init_app(self, app):
        app.before_request(self._before_request)
        app.after_request(self._after_request)

        # 루트 로거에 request_id 필터 추가
        for handler in logging.root.handlers:
            handler.addFilter(RequestIdFilter())

        # OpenTelemetry 초기화 (선택적)
        if _OTEL_AVAILABLE:
            self._init_otel(app)

        logger.info("TracingMiddleware 초기화 완료")

    def _init_otel(self, app):
        """OpenTelemetry 트레이서 초기화"""
        try:
            provider = TracerProvider()
            trace.set_tracer_provider(provider)
            self._otel_tracer = trace.get_tracer('insight-engine')
            logger.info("OpenTelemetry 트레이서 초기화 완료")
        except Exception as e:
            logger.warning("OpenTelemetry 초기화 실패: %s", e)

    def _before_request(self):
        """요청 시작 처리"""
        # X-Request-ID 헤더에서 전파받거나 새로 생성
        req_id = request.headers.get('X-Request-ID') or generate_request_id()
        _request_id_var.set(req_id)
        g.request_id = req_id
        g.start_time = time.time()

        logger.debug(
            "요청 시작 [%s] %s %s",
            req_id,
            request.method,
            request.path
        )

    def _after_request(self, response):
        """요청 완료 처리"""
        req_id = getattr(g, 'request_id', get_request_id())
        duration_ms = int((time.time() - getattr(g, 'start_time', time.time())) * 1000)

        # 응답 헤더에 요청 ID 추가
        response.headers['X-Request-ID'] = req_id
        response.headers['X-Response-Time'] = f"{duration_ms}ms"

        # 4xx, 5xx 오류 로깅
        if response.status_code >= 400:
            logger.warning(
                "요청 완료 [%s] %s %s → %d (%dms)",
                req_id, request.method, request.path,
                response.status_code, duration_ms
            )
        else:
            logger.debug(
                "요청 완료 [%s] %s %s → %d (%dms)",
                req_id, request.method, request.path,
                response.status_code, duration_ms
            )

        return response


def traced(span_name: Optional[str] = None):
    """함수에 OpenTelemetry 스팬 추가 데코레이터"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not _OTEL_AVAILABLE:
                return f(*args, **kwargs)

            tracer = trace.get_tracer('insight-engine')
            name = span_name or f.__qualname__
            with tracer.start_as_current_span(name) as span:
                span.set_attribute('request.id', get_request_id())
                return f(*args, **kwargs)
        return wrapper
    return decorator
