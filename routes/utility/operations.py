"""운영/모니터링 라우트 — utility_routes.py에서 분리.

헬스체크, 클라이언트 트래커(heartbeat/close), 프로바이더 조회/검증, Ollama 헬스.
카운터 변수와 헬퍼는 utility_routes.py에서 import하여 사용 (외부 patch 호환성).
"""
import os
import time

from flask import current_app, jsonify, request

from routes.blog_routes import blog_bp, _extract_client_id
from utils.responses import sanitize_error_for_client

# 카운터/트래커는 공용 _state 모듈에서 import (순환 import 방지).
from routes.utility._state import (
    _CLIENT_TRACKER,
    _cleanup_stale_clients,
    get_error_count,
    get_error_rate,
    get_request_count,
    increment_request_count,
)


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


def _fetch_ollama_models(base_url=None):
    """Ollama 서버(/api/tags)에서 실제 설치된 모델을 조회해 동적 모델 목록을 만든다.

    서버에 연결할 수 없으면 None을 반환해 호출측이 정적 config 목록으로 폴백하게 한다.
    """
    import requests as http_requests

    base_url = base_url or os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434')
    try:
        resp = http_requests.get(f'{base_url}/api/tags', timeout=5)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return None

    models = []
    for m in data.get('models', []):
        name = m.get('name', '')
        if not name:
            continue
        ctx = (m.get('details') or {}).get('context_length') or 8192
        models.append({
            'id': f'ollama_chat/{name}',
            'name': name,
            'max_input_tokens': ctx,
            'price_input': 0,
            'price_output': 0,
            'size_bytes': m.get('size'),  # 모델 디스크 크기 (UI에서 대용량 경고용)
        })
    return models


@blog_bp.route('/api/providers', methods=['GET'])
def api_providers():
    """API 키가 설정된 AI 서비스 및 모델 목록을 반환합니다.
    환경변수에 API 키가 설정된 프로바이더만 반환됩니다.
    Ollama는 로컬 서버에 실제 설치된 모델을 동적으로 조회해 반환합니다.
    """
    from config import get_available_providers, SUPADATA_API_KEY

    providers = get_available_providers()
    styles = current_app.config.get('STYLE_OPTIONS', [])

    # 각 프로바이더에 model_count 필드 추가 (원본 dict 변형 금지 — 복사본 사용)
    enriched = {}
    for pid, pdata in providers.items():
        models = pdata.get('models', [])
        if pid == 'ollama':
            # 설치된 모델을 실시간 조회 — 실패 시 정적 config 목록으로 폴백
            live_models = _fetch_ollama_models(pdata.get('api_base'))
            if live_models:
                models = live_models
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
