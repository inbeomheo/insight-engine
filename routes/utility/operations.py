"""운영/모니터링 라우트 — utility_routes.py에서 분리.

헬스체크, 클라이언트 트래커(heartbeat/close), ChatMock 프로바이더 조회.
카운터 변수와 헬퍼는 utility_routes.py에서 import하여 사용 (외부 patch 호환성).
"""
import os
import re

import requests

from flask import current_app, jsonify, request

from extensions import limiter
from routes.blog_routes import blog_bp, _extract_client_id
from src.shared.infrastructure.supabase_client import get_supabase, is_supabase_enabled
from utils.production_readiness import (
    REQUIRED_SUPABASE_SCHEMA_VERSION,
    SUPABASE_SCHEMA_VERSION_RPC,
)

# 카운터/트래커는 공용 _state 모듈에서 import (순환 import 방지).
from routes.utility._state import (
    get_error_count,
    get_error_rate,
    get_request_count,
    increment_request_count,
    record_client_heartbeat,
)


_CLIENT_ID_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$')
_FULL_STACK_FRONTEND_URL = 'http://127.0.0.1:3000/'


def _check_chatmock_ready() -> bool:
    base_url = (os.getenv('CHATMOCK_BASE_URL') or '').strip().rstrip('/')
    if not base_url:
        return False
    request_headers = {}
    api_key = (os.getenv('CHATMOCK_API_KEY') or '').strip()
    if api_key:
        request_headers['Authorization'] = f'Bearer {api_key}'
    try:
        response = requests.get(
            f'{base_url}/models',
            headers=request_headers,
            timeout=3,
            allow_redirects=False,
        )
        return 200 <= response.status_code < 300
    except requests.RequestException:
        return False


def _check_redis_ready() -> bool:
    redis_url = (os.getenv('REDIS_URL') or '').strip()
    if not redis_url:
        return False
    try:
        from redis import Redis
        client = Redis.from_url(
            redis_url,
            socket_connect_timeout=3,
            socket_timeout=3,
            retry_on_timeout=False,
        )
        return bool(client.ping())
    except Exception:
        return False


def _check_full_stack_frontend_ready() -> bool | None:
    """Probe Next.js only for the single-container full-stack runtime."""
    configured_url = (
        os.getenv('FULL_STACK_FRONTEND_READINESS_URL') or ''
    ).strip()
    if not configured_url:
        return None
    # The supervisor injects this exact loopback URL. Fail closed instead of
    # turning an operator-controlled readiness value into a general SSRF probe.
    if configured_url != _FULL_STACK_FRONTEND_URL:
        return False
    try:
        response = requests.get(
            configured_url,
            timeout=3,
            allow_redirects=False,
        )
        return 200 <= response.status_code < 400
    except requests.RequestException:
        return False


def _supabase_schema_status(*, skipped: bool = False) -> dict[str, object]:
    """Return an evidence-visible, non-mutating Supabase schema readiness result."""
    enabled = is_supabase_enabled()
    status: dict[str, object] = {
        'ready': False,
        'enabled': enabled,
        'checked': False,
        'required_version': REQUIRED_SUPABASE_SCHEMA_VERSION,
        'current_version': None,
        'rpc': SUPABASE_SCHEMA_VERSION_RPC,
    }

    if skipped:
        status.update({
            'ready': True,
            'reason': 'skipped_outside_production',
        })
        return status

    if not enabled:
        status['reason'] = 'configuration_disabled'
        return status

    status['checked'] = True
    try:
        client = get_supabase()
    except Exception:
        status['reason'] = 'client_error'
        return status

    if client is None:
        status['reason'] = 'client_unavailable'
        return status

    try:
        # ``get=True`` makes PostgREST invoke the STABLE RPC in read-only mode.
        response = client.rpc(SUPABASE_SCHEMA_VERSION_RPC, get=True).execute()
    except Exception:
        status['reason'] = 'rpc_error'
        return status

    version = getattr(response, 'data', None)
    # bool is an int subclass, so use an exact type check for a strict payload.
    if type(version) is not int:
        status['reason'] = 'malformed_version'
        return status

    status['current_version'] = version
    if version < REQUIRED_SUPABASE_SCHEMA_VERSION:
        status['reason'] = 'schema_outdated'
        return status

    status.update({'ready': True, 'reason': 'ok'})
    return status


@blog_bp.route('/health')
def health():
    """헬스체크 엔드포인트 (Railway/Docker용)"""
    increment_request_count()
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
    """운영 트래픽 수신 준비 상태. 필수 외부 의존성 장애 시 실패 폐쇄합니다."""
    if (os.getenv('FLASK_ENV') or '').strip().lower() != 'production':
        return jsonify({
            'status': 'ready',
            'dependencies': {
                'chatmock': 'skipped',
                'frontend': 'skipped',
                'redis': 'skipped',
                'supabase_schema': _supabase_schema_status(skipped=True),
            },
        }), 200

    supabase_schema = _supabase_schema_status()
    frontend = _check_full_stack_frontend_ready()
    dependencies = {
        'chatmock': _check_chatmock_ready(),
        'frontend': frontend if frontend is not None else 'not_required',
        'redis': _check_redis_ready(),
        'supabase_schema': supabase_schema,
    }
    ready_for_traffic = (
        dependencies['chatmock'] is True
        and frontend is not False
        and dependencies['redis'] is True
        and supabase_schema['ready'] is True
    )
    return jsonify({
        'status': 'ready' if ready_for_traffic else 'not_ready',
        'dependencies': dependencies,
    }), 200 if ready_for_traffic else 503


@blog_bp.route('/')
def home():
    """API 서버 상태를 반환합니다. 프론트엔드는 Next.js에서 제공."""
    return jsonify({'status': 'ok', 'message': 'Insight Engine API Server'})


@blog_bp.route('/api/heartbeat', methods=['POST'])
@limiter.limit("60/minute")
def api_heartbeat():
    """클라이언트 연결 상태를 추적합니다."""
    client_id = _extract_client_id(request)
    if not client_id:
        return jsonify({'ok': False, 'error': 'clientId required'}), 400
    if not _CLIENT_ID_RE.fullmatch(client_id):
        return jsonify({'ok': False, 'error': 'invalid clientId'}), 400
    record_client_heartbeat(client_id)
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
        'hasAutoFallback': True
    })
