"""
Prometheus 메트릭 서비스 (F9-09)
prometheus_client 미설치 시 노옵(no-op) 폴백
"""
import time
import logging
from functools import wraps

logger = logging.getLogger(__name__)

# prometheus_client 선택적 import
try:
    from prometheus_client import (
        Counter, Histogram, Gauge, Summary,
        generate_latest, CONTENT_TYPE_LATEST, REGISTRY
    )
    _PROMETHEUS_AVAILABLE = True
except ImportError:
    _PROMETHEUS_AVAILABLE = False
    logger.info("prometheus_client 미설치 — 메트릭 비활성화 (pip install prometheus-client)")

# ── 메트릭 정의 ──────────────────────────────────────────────────────────────

if _PROMETHEUS_AVAILABLE:
    # HTTP 요청 카운터
    HTTP_REQUESTS_TOTAL = Counter(
        'insight_http_requests_total',
        'HTTP 요청 총 수',
        ['method', 'endpoint', 'status_code']
    )

    # HTTP 요청 레이턴시
    HTTP_REQUEST_DURATION = Histogram(
        'insight_http_request_duration_seconds',
        'HTTP 요청 처리 시간 (초)',
        ['method', 'endpoint'],
        buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0]
    )

    # AI 생성 카운터
    AI_GENERATION_TOTAL = Counter(
        'insight_ai_generation_total',
        'AI 콘텐츠 생성 총 수',
        ['style', 'provider', 'status']
    )

    # AI 생성 레이턴시
    AI_GENERATION_DURATION = Histogram(
        'insight_ai_generation_duration_seconds',
        'AI 콘텐츠 생성 처리 시간 (초)',
        ['style', 'provider'],
        buckets=[1, 5, 10, 20, 30, 60, 120]
    )

    # 활성 연결 게이지
    ACTIVE_CONNECTIONS = Gauge(
        'insight_active_connections',
        '현재 처리 중인 요청 수'
    )

    # 캐시 히트/미스
    CACHE_HITS = Counter('insight_cache_hits_total', '캐시 히트 수', ['cache_type'])
    CACHE_MISSES = Counter('insight_cache_misses_total', '캐시 미스 수', ['cache_type'])

    # 오류 카운터
    ERRORS_TOTAL = Counter(
        'insight_errors_total',
        '오류 총 수',
        ['error_type', 'service']
    )

    # 사용량 게이지
    USAGE_REMAINING = Gauge(
        'insight_usage_remaining',
        '사용자별 남은 사용량',
        ['user_id']
    )

    # 자막 추출 소스 통계
    TRANSCRIPT_SOURCE = Counter(
        'insight_transcript_source_total',
        '자막 추출 소스별 카운트',
        ['source']
    )

else:
    # 노옵 클래스 — prometheus 없어도 코드 동작
    class _Noop:
        """Prometheus 미설치 시 노옵 대체 객체"""
        def labels(self, **kwargs):
            """레이블 선택 (노옵)"""
            return self
        def inc(self, *a, **k):
            """카운터 증가 (노옵)"""
            pass
        def observe(self, *a, **k):
            """히스토그램 관측 (노옵)"""
            pass
        def set(self, *a, **k):
            """게이지 설정 (노옵)"""
            pass

    HTTP_REQUESTS_TOTAL = _Noop()
    HTTP_REQUEST_DURATION = _Noop()
    AI_GENERATION_TOTAL = _Noop()
    AI_GENERATION_DURATION = _Noop()
    ACTIVE_CONNECTIONS = _Noop()
    CACHE_HITS = _Noop()
    CACHE_MISSES = _Noop()
    ERRORS_TOTAL = _Noop()
    USAGE_REMAINING = _Noop()
    TRANSCRIPT_SOURCE = _Noop()


# ── 헬퍼 함수 ─────────────────────────────────────────────────────────────────

def record_http_request(method: str, endpoint: str, status_code: int, duration_s: float):
    """HTTP 요청 메트릭 기록"""
    HTTP_REQUESTS_TOTAL.labels(
        method=method, endpoint=endpoint, status_code=str(status_code)
    ).inc()
    HTTP_REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration_s)


def record_ai_generation(style: str, provider: str, status: str, duration_s: float):
    """AI 생성 메트릭 기록"""
    AI_GENERATION_TOTAL.labels(style=style, provider=provider, status=status).inc()
    if status == 'success':
        AI_GENERATION_DURATION.labels(style=style, provider=provider).observe(duration_s)


def record_cache_hit(cache_type: str = 'ai'):
    """캐시 히트 카운터 증가"""
    CACHE_HITS.labels(cache_type=cache_type).inc()


def record_cache_miss(cache_type: str = 'ai'):
    """캐시 미스 카운터 증가"""
    CACHE_MISSES.labels(cache_type=cache_type).inc()


def record_error(error_type: str, service: str = 'unknown'):
    """에러 카운터 증가"""
    ERRORS_TOTAL.labels(error_type=error_type, service=service).inc()


def record_transcript_source(source: str):
    """자막 추출 소스별 카운터 증가"""
    TRANSCRIPT_SOURCE.labels(source=source).inc()


def get_metrics_output():
    """Prometheus 텍스트 포맷 메트릭 반환"""
    if _PROMETHEUS_AVAILABLE:
        return generate_latest(REGISTRY), CONTENT_TYPE_LATEST
    return b"# prometheus_client not installed\n", "text/plain; version=0.0.4"


# ── Flask 미들웨어 데코레이터 ─────────────────────────────────────────────────

def track_request_metrics(f):
    """Flask 라우트에 HTTP 메트릭 자동 기록 데코레이터"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        from flask import request
        start = time.time()
        ACTIVE_CONNECTIONS.inc()
        status_code = 500
        try:
            result = f(*args, **kwargs)
            # Flask Response or tuple 처리
            if isinstance(result, tuple):
                status_code = result[1] if len(result) > 1 else 200
            else:
                status_code = getattr(result, 'status_code', 200)
            return result
        except Exception:
            status_code = 500
            raise
        finally:
            duration = time.time() - start
            ACTIVE_CONNECTIONS.dec()
            record_http_request(
                method=request.method,
                endpoint=request.endpoint or 'unknown',
                status_code=status_code,
                duration_s=duration
            )
    return wrapper


def init_metrics_endpoint(app):
    """Flask 앱에 /metrics 엔드포인트 등록"""
    @app.route('/metrics')
    def metrics_endpoint():
        """Prometheus 메트릭 엔드포인트 핸들러"""
        from flask import Response
        data, content_type = get_metrics_output()
        return Response(data, mimetype=content_type)

    logger.info("Prometheus /metrics 엔드포인트 등록 완료")
