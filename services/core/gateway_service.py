"""CLIProxyAPI의 OpenAI 호환 호출 설정을 한곳에서 관리합니다."""
import os
from urllib.parse import urlsplit


DEFAULT_GATEWAY_MODEL = 'cliproxyapi/gpt-5.5'
DEFAULT_GATEWAY_BASE_URL = 'http://127.0.0.1:8317/v1'


class GatewayConfigurationError(ValueError):
    """유료 작업을 시작하기 전에 알려야 하는 서버 연결 설정 오류."""


def gateway_model_name(model: str) -> str:
    """앱 접두사만 제거하며 게이트웨이에 등록된 실제 모델명은 보존합니다."""
    for prefix in ('cliproxyapi/', 'chatmock/'):
        if model.startswith(prefix):
            return model[len(prefix):]
    return model


def canonical_gateway_model(model: str) -> str:
    return f'cliproxyapi/{gateway_model_name(model)}'


def gateway_connection() -> tuple[str, str]:
    """이전 게이트웨이 환경변수는 새 연결에 사용하지 않습니다."""
    configured_base_url = os.getenv('CLIPROXYAPI_BASE_URL')
    base_url = (
        DEFAULT_GATEWAY_BASE_URL if configured_base_url is None else configured_base_url
    ).strip().rstrip('/')
    api_key = (os.getenv('CLIPROXYAPI_API_KEY') or '').strip()
    return base_url, api_key


def require_gateway_connection() -> tuple[str, str]:
    base_url, api_key = gateway_connection()
    try:
        parsed = urlsplit(base_url)
        valid_url = (
            parsed.scheme in ('http', 'https') and bool(parsed.hostname)
            and parsed.username is None and parsed.password is None
            and not parsed.query and not parsed.fragment
            and not any(character.isspace() for character in base_url)
        )
        parsed.port  # 숫자가 아니거나 범위를 벗어난 포트도 거부합니다.
    except ValueError:
        valid_url = False
    if not valid_url:
        raise GatewayConfigurationError(
            'CLIProxyAPI 주소가 올바르지 않습니다. CLIPROXYAPI_BASE_URL에 '
            '사용자 정보·쿼리·프래그먼트 없는 HTTP(S) 서버 주소를 설정해주세요.'
        )
    if not api_key:
        raise GatewayConfigurationError(
            'CLIProxyAPI 연결 키가 없습니다. CLIPROXYAPI_API_KEY를 설정해주세요.'
        )
    return base_url, api_key


def apply_gateway_kwargs(kwargs: dict, model: str) -> None:
    """모든 모델을 같은 게이트웨이로 보내고 GPT 추론 옵션만 분리합니다."""
    actual_model = gateway_model_name(model)
    base_url, api_key = require_gateway_connection()
    kwargs.update({
        'model': actual_model,
        'custom_llm_provider': 'openai',
        'api_base': base_url,
        'api_key': api_key,
        'drop_params': True,
    })
    if actual_model.startswith(('gpt-5', 'o1', 'o3', 'o4')):
        kwargs['reasoning_effort'] = 'medium'
        kwargs.pop('temperature', None)
    else:
        kwargs.pop('reasoning_effort', None)
