"""운영/모니터링 라우트 — utility_routes.py에서 분리.

헬스체크, 클라이언트 트래커(heartbeat/close), ChatMock 프로바이더 조회.
카운터 변수와 헬퍼는 utility_routes.py에서 import하여 사용 (외부 patch 호환성).
"""
import os
import time

from flask import current_app, jsonify, request

from routes.blog_routes import blog_bp, _extract_client_id

# 카운터/트래커는 공용 _state 모듈에서 import (순환 import 방지).
from routes.utility._state import (
    _CLIENT_TRACKER,
    _cleanup_stale_clients,
    get_error_count,
    get_error_rate,
    get_request_count,
)


@blog_bp.route('/health')
def health():
    """Liveness — 프로세스 생존만 확인. 의존성 검사는 /ready."""
    env = 'production' if os.environ.get('FLASK_ENV') != 'development' and not current_app.debug else 'development'
    # 프로세스 메모리 사용량 (MB) — 표준 라이브러리만 사용
    mem_mb = None
    try:
        import resource
        # Linux/macOS: ru_maxrss는 KB 단위 (macOS는 bytes이지만 보통 KB)
        mem_mb = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)
    except ImportError:
        # Windows: /proc 없으므로 ctypes 사용
        try:
            import ctypes
            import ctypes.wintypes
            class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
                _fields_ = [
                    ('cb', ctypes.wintypes.DWORD),
                    ('PageFaultCount', ctypes.wintypes.DWORD),
                    ('PeakWorkingSetSize', ctypes.c_size_t),
                    ('WorkingSetSize', ctypes.c_size_t),
                    ('QuotaPeakPagedPoolUsage', ctypes.c_size_t),
                    ('QuotaPagedPoolUsage', ctypes.c_size_t),
                    ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t),
                    ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
                    ('PagefileUsage', ctypes.c_size_t),
                    ('PeakPagefileUsage', ctypes.c_size_t),
                ]
            pmc = PROCESS_MEMORY_COUNTERS()
            pmc.cb = ctypes.sizeof(pmc)
            handle = ctypes.windll.kernel32.GetCurrentProcess()
            if ctypes.windll.psapi.GetProcessMemoryInfo(handle, ctypes.byref(pmc), pmc.cb):
                mem_mb = round(pmc.WorkingSetSize / (1024 * 1024), 1)
        except Exception:
            pass
    except Exception:
        pass
    return jsonify({
        'status': 'healthy', 'environment': env, 'api_version': 'v2.0',
        'request_count': get_request_count(), 'error_count': get_error_count(),
        'error_rate': get_error_rate(), 'memory_usage_mb': mem_mb,
    }), 200


@blog_bp.route('/ready')
def ready():
    """Readiness — 필수 의존성 확인. 실패해도 프로세스는 살아 있음(/health)."""
    checks = {}
    ready_ok = True

    redis_url = (os.environ.get('REDIS_URL') or '').strip()
    if redis_url and not redis_url.startswith('memory'):
        try:
            from routes.utility._state import _get_redis
            client = _get_redis()
            if client is None:
                raise RuntimeError('redis unavailable')
            client.ping()
            checks['redis'] = 'ok'
        except Exception:
            checks['redis'] = 'error'
            ready_ok = False
    else:
        checks['redis'] = 'skipped'

    try:
        cache = getattr(current_app, 'ai_cache', None)
        if cache is not None:
            cache.get_stats()
        checks['ai_cache'] = 'ok'
    except Exception:
        checks['ai_cache'] = 'error'
        ready_ok = False

    status = 'ready' if ready_ok else 'not_ready'
    return jsonify({'status': status, 'checks': checks}), (200 if ready_ok else 503)


@blog_bp.route('/')
def home():
    """API 서버 상태를 반환합니다. 프론트엔드는 Next.js에서 제공."""
    return jsonify({'status': 'ok', 'message': 'Insight Engine API Server'})


@blog_bp.route('/api/heartbeat', methods=['POST'])
def api_heartbeat():
    """클라이언트 연결 상태를 추적합니다."""
    client_id = _extract_client_id(request)
    if not client_id:
        return jsonify({'ok': False, 'error': 'clientId required'}), 400
    _CLIENT_TRACKER[client_id] = time.time()
    _cleanup_stale_clients()
    return jsonify({'ok': True})


@blog_bp.route('/api/providers', methods=['GET'])
def api_providers():
    """활성 AI 프로바이더 및 모델 목록을 반환합니다."""
    from config import get_available_providers, SUPADATA_API_KEY

    providers = get_available_providers()
    styles = current_app.config.get('STYLE_OPTIONS', [])

    # 각 프로바이더에 model_count 필드 추가 (원본 dict 변형 금지 — 복사본 사용)
    enriched = {}
    for pid, pdata in providers.items():
        models = pdata.get('models', [])
        enriched[pid] = {
            **pdata,
            'models': models,
            'model_count': len(models),
            'default_model': models[0]['id'] if models else None,
        }

    return jsonify({
        'providers': enriched,
        'styles': [{'id': s[0], 'name': s[1]} for s in styles],
        'supadataConfigured': bool(SUPADATA_API_KEY),
        'hasAutoFallback': len(enriched) > 1,
    })
