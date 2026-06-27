"""운영/모니터링 라우트 — utility_routes.py에서 분리.

헬스체크, 클라이언트 트래커(heartbeat/close), 프로바이더 조회/검증, Ollama 헬스.
카운터 변수와 헬퍼는 utility_routes.py에서 import하여 사용 (외부 patch 호환성).
"""
import os
import time
import hmac

from flask import Response, current_app, jsonify, request

from routes.blog_routes import blog_bp, _extract_client_id
from src.contexts.identity.interface.auth_decorators import require_auth
from utils.runtime_readiness import runtime_readiness_report
from utils.responses import sanitize_error_for_client
from utils.release_metadata import release_metadata

# 카운터/트래커는 공용 _state 모듈에서 import (순환 import 방지).
from routes.utility._state import (
    _CLIENT_TRACKER,
    _cleanup_stale_clients,
    get_error_count,
    get_error_rate,
    get_request_count,
    get_active_requests,
    increment_request_count,
)

GENERATION_PROVIDER_IDS = ('chatmock', 'zhipuai')

GENERATION_PROVIDER_LABELS = {
    'chatmock': 'ChatMock Spark',
    'zhipuai': 'GLM',
}


def _env_present(*names: str) -> bool:
    """환경변수 존재 여부만 확인합니다. 값은 절대 응답에 포함하지 않습니다."""
    return any(bool((os.getenv(name) or '').strip()) for name in names)


def _prometheus_escape_label(value: object) -> str:
    """Escape label values for Prometheus text exposition."""
    return str(value).replace('\\', '\\\\').replace('\n', '\\n').replace('"', '\\"')


def _metrics_token_from_request() -> str:
    auth_header = (request.headers.get('Authorization') or '').strip()
    if auth_header.lower().startswith('bearer '):
        return auth_header[7:].strip()
    return (request.headers.get('X-Metrics-Auth-Token') or '').strip()


def _metrics_authorized() -> bool:
    configured_token = (os.getenv('METRICS_AUTH_TOKEN') or '').strip()
    if not configured_token:
        return (os.getenv('FLASK_ENV') or '').strip().lower() != 'production'
    return hmac.compare_digest(configured_token, _metrics_token_from_request())


def _metrics_payload() -> str:
    release = release_metadata()
    labels = ','.join([
        f'version="{_prometheus_escape_label(release["version"])}"',
        f'release="{_prometheus_escape_label(release["release"])}"',
        f'git_sha="{_prometheus_escape_label(release["gitSha"])}"',
    ])
    lines = [
        '# HELP insight_engine_info Insight Engine release metadata.',
        '# TYPE insight_engine_info gauge',
        f'insight_engine_info{{{labels}}} 1',
        '# HELP insight_engine_requests_total Total requests observed by the app counters.',
        '# TYPE insight_engine_requests_total counter',
        f'insight_engine_requests_total {get_request_count()}',
        '# HELP insight_engine_errors_total Total error responses observed by the app counters.',
        '# TYPE insight_engine_errors_total counter',
        f'insight_engine_errors_total {get_error_count()}',
        '# HELP insight_engine_error_rate Ratio of errors to observed requests.',
        '# TYPE insight_engine_error_rate gauge',
        f'insight_engine_error_rate {get_error_rate()}',
        '# HELP insight_engine_active_requests Current active requests.',
        '# TYPE insight_engine_active_requests gauge',
        f'insight_engine_active_requests {get_active_requests()}',
        '# HELP insight_engine_tracked_clients Current heartbeat-tracked clients.',
        '# TYPE insight_engine_tracked_clients gauge',
        f'insight_engine_tracked_clients {len(_CLIENT_TRACKER)}',
        '',
    ]
    return '\n'.join(lines)


def _provider_health(pid: str, pdata: dict, *, available: bool) -> dict:
    """사용자에게 노출 가능한 provider 상태 설명을 생성합니다."""
    models = pdata.get('models') or []
    has_models = len(models) > 0
    base_configured = bool(pdata.get('api_base'))

    if pid == 'chatmock':
        status = 'ready' if available and has_models else 'unavailable'
        return {
            'status': status,
            'severity': 'ok' if status == 'ready' else 'error',
            'label': '기본 모델 사용 가능' if status == 'ready' else 'ChatMock 확인 필요',
            'message': (
                'ChatMock Spark가 기본 생성 모델로 준비되었습니다. 생성 실패 시 프록시 연결 상태를 함께 확인합니다.'
                if status == 'ready'
                else 'ChatMock Spark 모델 정보를 찾지 못했습니다.'
            ),
            'action': '생성 실패 시 ChatMock 서비스 실행 상태와 CHATMOCK_BASE_URL 설정을 확인해주세요.',
            'is_default': True,
            'is_selectable': status == 'ready',
            'provider_label': GENERATION_PROVIDER_LABELS[pid],
        }

    if pid == 'zhipuai':
        key_configured = _env_present('ZAI_API_KEY', 'ZHIPUAI_API_KEY')
        status = 'ready' if available and key_configured and has_models else 'missing_key'
        return {
            'status': status,
            'severity': 'ok' if status == 'ready' else 'warning',
            'label': 'GLM 사용 가능' if status == 'ready' else 'GLM 키 필요',
            'message': (
                'GLM API 키가 감지되어 선택 가능한 상태입니다. 권한/한도 오류는 생성 실패 메시지에 별도로 표시됩니다.'
                if status == 'ready'
                else 'GLM을 사용하려면 서버 환경변수에 ZAI_API_KEY 또는 ZHIPUAI_API_KEY를 설정해주세요.'
            ),
            'action': '권한 또는 한도 오류가 계속되면 GLM 콘솔에서 키 권한과 잔액을 확인해주세요.',
            'is_default': False,
            'is_selectable': status == 'ready',
            'provider_label': GENERATION_PROVIDER_LABELS[pid],
        }

    status = 'ready' if available and has_models else 'unavailable'
    return {
        'status': status,
        'severity': 'ok' if status == 'ready' else 'warning',
        'label': '사용 가능' if status == 'ready' else '확인 필요',
        'message': '모델 목록이 준비되었습니다.' if status == 'ready' else '사용 가능한 모델이 없습니다.',
        'action': '서버 환경변수와 provider 설정을 확인해주세요.',
        'is_default': False,
        'is_selectable': status == 'ready',
        'base_configured': base_configured,
    }


def _provider_diagnostics(pid: str, pdata: dict, *, available: bool) -> dict:
    models = pdata.get('models') or []
    default_model = models[0]['id'] if models else None
    api_key_configured = True
    key_names = []
    if pid == 'zhipuai':
        key_names = ['ZAI_API_KEY', 'ZHIPUAI_API_KEY']
        api_key_configured = _env_present('ZAI_API_KEY', 'ZHIPUAI_API_KEY')
    elif pid not in ('chatmock', 'ollama'):
        api_key_configured = available

    health = _provider_health(pid, pdata, available=available)
    return {
        'provider_id': pid,
        'provider_name': pdata.get('name') or GENERATION_PROVIDER_LABELS.get(pid, pid),
        'provider_label': GENERATION_PROVIDER_LABELS.get(pid, pdata.get('name') or pid),
        'available': available,
        'generation_visible': pid in GENERATION_PROVIDER_IDS,
        'api_key_configured': api_key_configured,
        'base_url_configured': bool(pdata.get('api_base')),
        'model_count': len(models),
        'default_model': default_model,
        'health_status': health['status'],
        'health_label': health['label'],
        'safe_summary': health['message'],
        'next_step': health.get('action'),
        'required_env': key_names,
    }


@blog_bp.route('/health')
def health():
    """헬스체크 엔드포인트 (Railway/Docker용)"""
    increment_request_count()
    flask_env = (os.environ.get('FLASK_ENV') or '').strip().lower()
    env = 'production' if flask_env != 'development' and not current_app.debug else 'development'
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
    payload = {
        'status': 'healthy', 'environment': env, 'api_version': 'v2.0',
        'release': release_metadata(),
    }
    if flask_env != 'production' or _metrics_authorized():
        payload.update({
            'request_count': get_request_count(),
            'error_count': get_error_count(),
            'error_rate': get_error_rate(),
            'memory_usage_mb': mem_mb,
        })
    return jsonify(payload), 200


@blog_bp.route('/ready')
def ready():
    """Runtime readiness endpoint for deploy/load-balancer checks."""
    report = runtime_readiness_report()
    status_code = 200 if report['status'] == 'ready' else 503

    flask_env = (os.environ.get('FLASK_ENV') or '').strip().lower()
    if flask_env == 'production' and not _metrics_authorized():
        response = jsonify({'status': report['status']})
    else:
        response = jsonify(report)
    response.headers['Cache-Control'] = 'no-store'
    return response, status_code


@blog_bp.route('/metrics')
def metrics():
    """Prometheus-compatible operational metrics protected by a bearer token."""
    configured_token = (os.getenv('METRICS_AUTH_TOKEN') or '').strip()
    if (os.getenv('FLASK_ENV') or '').strip().lower() == 'production' and not configured_token:
        return Response('metrics token is not configured\n', status=503, mimetype='text/plain')
    if not _metrics_authorized():
        if not _metrics_token_from_request():
            return Response(
                'metrics authentication required\n',
                status=401,
                headers={'WWW-Authenticate': 'Bearer realm="metrics"'},
                mimetype='text/plain',
            )
        return Response('metrics authentication failed\n', status=403, mimetype='text/plain')
    return Response(
        _metrics_payload(),
        content_type='text/plain; version=0.0.4; charset=utf-8',
    )


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


@blog_bp.route('/api/close', methods=['POST'])
def api_close():
    """클라이언트 연결 종료를 처리합니다."""
    client_id = _extract_client_id(request)
    if not client_id:
        return jsonify({'ok': False, 'error': 'clientId required'}), 400
    _CLIENT_TRACKER.pop(client_id, None)
    return jsonify({'ok': True})


@blog_bp.route('/api/providers', methods=['GET'])
def api_providers():
    """API 키가 설정된 AI 서비스 및 모델 목록을 반환합니다.
    환경변수에 API 키가 설정된 프로바이더만 반환됩니다.
    """
    from config import get_available_providers, SUPADATA_API_KEY, SUPPORTED_PROVIDERS

    providers = get_available_providers()
    styles = current_app.config.get('STYLE_OPTIONS', [])

    # 각 프로바이더에 model_count/default_model 및 안전한 진단 필드 추가
    enriched = {}
    for pid, pdata in providers.items():
        models = pdata.get('models', [])
        available = True
        enriched[pid] = {
            **pdata,
            'model_count': len(models),
            'default_model': models[0]['id'] if models else None,
            'health': _provider_health(pid, pdata, available=available),
            'diagnostics': _provider_diagnostics(pid, pdata, available=available),
        }

    generation_diagnostics = {}
    for pid in GENERATION_PROVIDER_IDS:
        pdata = providers.get(pid) or SUPPORTED_PROVIDERS.get(pid) or {}
        available = pid in providers
        generation_diagnostics[pid] = {
            'health': _provider_health(pid, pdata, available=available),
            'diagnostics': _provider_diagnostics(pid, pdata, available=available),
        }

    return jsonify({
        'providers': enriched,
        'providerDiagnostics': generation_diagnostics,
        'style_options': styles,
        'styles': [{'id': s[0], 'name': s[1]} for s in styles],
        'supadataConfigured': bool(SUPADATA_API_KEY),
        'hasAutoFallback': True
    })


@blog_bp.route('/api/ollama/health', methods=['GET'])
def api_ollama_health():
    """Ollama 서버 연결 상태를 확인합니다."""
    import requests as http_requests

    base_url = os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434')
    try:
        resp = http_requests.get(f'{base_url}/api/tags', timeout=5)
        resp.raise_for_status()
        data = resp.json()
        models = [m.get('name', '') for m in data.get('models', [])]
        return jsonify({'ok': True, 'models': models, 'base_url': base_url})
    except Exception as e:
        return jsonify({'ok': False, 'error': sanitize_error_for_client(str(e)), 'base_url': base_url}), 503


@blog_bp.route('/api/providers/validate', methods=['POST'])
@require_auth
def api_validate_provider():
    """API 키를 소량 토큰 호출로 유효성 테스트합니다."""
    data = request.get_json(silent=True) or {}
    provider_id = data.get('provider_id', '')
    api_key = data.get('api_key', '')

    if not provider_id:
        return jsonify({'valid': False, 'error': 'provider_id가 필요합니다.'}), 400

    from config import SUPPORTED_PROVIDERS

    if provider_id not in SUPPORTED_PROVIDERS:
        return jsonify({'valid': False, 'error': f'지원하지 않는 프로바이더: {provider_id}'}), 400

    provider = SUPPORTED_PROVIDERS[provider_id]
    models = provider.get('models', [])
    if not models:
        return jsonify({'valid': False, 'error': '사용 가능한 모델이 없습니다.'}), 400

    test_model = models[0]['id']

    # Ollama는 API 키 대신 base URL로 연결 테스트
    if provider_id == 'ollama':
        import requests as http_requests
        base_url = api_key or provider.get('api_base', 'http://localhost:11434')
        try:
            t0 = time.time()
            resp = http_requests.get(f'{base_url}/api/tags', timeout=5)
            latency_ms = round((time.time() - t0) * 1000)
            resp.raise_for_status()
            return jsonify({'valid': True, 'model_tested': test_model, 'latency_ms': latency_ms})
        except Exception as e:
            return jsonify({'valid': False, 'model_tested': test_model, 'error': sanitize_error_for_client(str(e))})

    if not api_key:
        return jsonify({'valid': False, 'error': 'API 키가 필요합니다.'}), 400

    # LiteLLM으로 소량 토큰 호출 테스트
    try:
        import litellm

        kwargs = {
            'model': test_model,
            'messages': [{'role': 'user', 'content': 'Hi'}],
            'max_tokens': 5,
            'api_key': api_key,
        }
        # api_base가 있는 프로바이더 (zhipuai, openrouter 등)
        if provider.get('api_base'):
            kwargs['api_base'] = provider['api_base']

        t0 = time.time()
        litellm.completion(**kwargs)
        latency_ms = round((time.time() - t0) * 1000)
        return jsonify({'valid': True, 'model_tested': test_model, 'latency_ms': latency_ms})
    except Exception as e:
        return jsonify({'valid': False, 'model_tested': test_model, 'error': sanitize_error_for_client(str(e))})


@blog_bp.route('/api/providers/campaign-packs', methods=['GET'])
def api_campaign_packs():
    """사용 가능한 캠페인 팩 목록을 반환합니다."""
    from config import CAMPAIGN_PACKS
    packs = {
        pack_id: {**pack, 'id': pack_id}
        for pack_id, pack in CAMPAIGN_PACKS.items()
    }
    return jsonify({'packs': packs})
