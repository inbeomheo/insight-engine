"""
HTTP 응답 헬퍼 — routes 전체에서 공통 사용

표준 에러 응답 패턴:
  - api_error(message, status_code): 명시적 에러 메시지 반환
  - api_error_from_exception(e, fallback): 예외에서 안전한 에러 응답 생성 (내부 정보 로깅만)
  - handle_error(error_msg, log_detail): 에러 접두사 기반 HTTP 상태 코드 자동 결정
"""
import logging

from flask import jsonify, current_app

logger = logging.getLogger(__name__)

# ai_service에서 정의된 에러 접두사 (세분화된 에러)
_ERROR_PREFIXES = [
    '[인증 실패]', '[사용량 초과]', '[모델 오류]', '[타임아웃]',
    '[연결 실패]', '[서비스 불가]', '[서버 오류]', '[잔액 부족]',
    '[컨텐츠 차단]', '[AI 오류]',
]

# 클라이언트에 노출해도 안전한 에러 접두사
_SAFE_ERROR_PREFIXES = [
    '[인증 실패]', '[사용량 초과]', '[입력 오류]', '[자막 없음]',
    '[생성 실패]', '[타임아웃]', '[모델 오류]', '[잔액 부족]',
    '[컨텐츠 차단]', '[AI 오류]',
    '자막을', '댓글을', 'YouTube', 'API', '영상', 'URL',
]

# 내부 정보 키워드 (노출 차단 대상)
_INTERNAL_KEYWORDS = [
    'traceback', 'exception', 'file "', 'line ', 'error:', 'failed:',
    '/home/', '/usr/', 'supabase', 'postgres', 'connection',
    'api_key', 'token', 'secret', 'password', 'authorization', '.env',
    'openai', 'litellm', 'httpx', 'requests.exceptions',
    'httpsconnectionpool', 'connectionpool', 'urllib3', 'ssl:',
    'read timed out', 'connect timeout', 'max retries exceeded',
    'connection aborted', 'connection refused',
    'name or service not known', 'temporary failure in name resolution',
    'c:\\users\\', 'c:/users/', 'd:\\', 'e:\\',
]


def success_response(data=None, message=None):
    """성공 응답 생성 — HTTP 200"""
    response = {'success': True}
    if message:
        response['message'] = message
    if data:
        response.update(data)
    return jsonify(response)


def error_response(message, status_code=400):
    """단순 에러 응답 생성"""
    return jsonify({'error': message}), status_code


def sanitize_error_for_client(error_msg: str) -> str:
    """에러 메시지에서 내부 정보를 제거하여 클라이언트에 안전한 메시지를 반환합니다."""
    is_safe = any(error_msg.startswith(prefix) for prefix in _SAFE_ERROR_PREFIXES)
    has_internal_info = any(kw in error_msg.lower() for kw in _INTERNAL_KEYWORDS)

    if not is_safe or has_internal_info:
        current_app.logger.error(f'Internal error hidden from user: {error_msg}')
        return '[서버 오류] 처리 중 예상치 못한 오류가 발생했습니다. 다시 시도해주세요.'

    return error_msg


def handle_error(error_msg, log_detail=None):
    """에러 메시지에 따른 적절한 HTTP 상태 코드를 결정하고 응답을 반환합니다.

    Args:
        error_msg: 사용자에게 보여줄 에러 메시지
        log_detail: 로깅용 상세 에러 (선택사항)
    """
    is_exception = isinstance(error_msg, Exception)
    error_text = error_msg if isinstance(error_msg, str) else str(error_msg or '')

    if is_exception:
        if log_detail:
            current_app.logger.error('%s: %s', log_detail, error_text, exc_info=True)
        else:
            current_app.logger.error('Unhandled exception: %s', error_text, exc_info=True)
    elif log_detail:
        current_app.logger.error(f'Error: {log_detail}')

    if is_exception:
        safe_msg = '[서버 오류] 요청 처리 중 문제가 발생했습니다.'
        if isinstance(log_detail, str) and log_detail.strip():
            safe_msg = f'[서버 오류] {log_detail.strip()} 처리 중 문제가 발생했습니다.'
        return jsonify({'error': safe_msg}), 500

    is_formatted_error = any(error_text.startswith(prefix) for prefix in _ERROR_PREFIXES)

    if is_formatted_error:
        # 내부 정보가 접두사 뒤에 포함되어 있을 수 있으므로 필터링 적용
        safe_error = sanitize_error_for_client(error_text)
        if error_text.startswith('[인증 실패]'):
            return jsonify({'error': safe_error}), 401
        if error_text.startswith('[사용량 초과]'):
            return jsonify({'error': safe_error}), 429
        return jsonify({'error': safe_error}), 503

    if 'API 키' in error_text or 'authentication' in error_text.lower():
        return jsonify({'error': error_text}), 401

    safe_msg = sanitize_error_for_client(error_text)
    return jsonify({'error': safe_msg}), 500


def api_error(message: str, status_code: int = 400, error_code: str = None) -> tuple:
    """표준 에러 응답을 반환합니다.

    Args:
        message: 사용자에게 보여줄 에러 메시지 (한국어)
        status_code: HTTP 상태 코드 (400, 401, 403, 404, 429, 500)
        error_code: 선택적 에러 코드 (예: 'INVALID_INPUT', 'AUTH_REQUIRED')

    Returns:
        (Response, status_code) 튜플
    """
    body = {'error': message}
    if error_code:
        body['code'] = error_code
    return jsonify(body), status_code


def api_error_from_exception(e: Exception, fallback_message: str = '서버 오류가 발생했습니다.') -> tuple:
    """예외에서 안전한 에러 응답을 생성합니다. 내부 정보는 로깅만 합니다.

    str(e)를 클라이언트에 직접 노출하지 않고, fallback_message를 반환합니다.

    Args:
        e: 발생한 예외
        fallback_message: 사용자에게 보여줄 기본 메시지

    Returns:
        (Response, 500) 튜플
    """
    logger.error(f"API 오류: {e}", exc_info=True)
    return jsonify({'error': fallback_message}), 500


def sanitize_path(user_path: str, allowed_base: str) -> str:
    """사용자 입력 경로를 허용된 기본 디렉토리 하위로 제한합니다 (Path Traversal 방어).

    '../', 절대 경로, 심볼릭 링크 등을 통한 경로 탈출을 차단합니다.

    Args:
        user_path: 사용자가 입력한 경로 (상대/절대)
        allowed_base: 허용된 기본 디렉토리 (예: './data/finetune')

    Returns:
        allowed_base 하위에 정규화된 안전한 절대 경로

    Raises:
        ValueError: 경로가 허용 범위를 벗어나는 경우
    """
    import os

    # 기본 디렉토리의 절대 경로
    base = os.path.realpath(os.path.abspath(allowed_base))
    # 사용자 경로를 기본 디렉토리 기준으로 결합 후 정규화
    joined = os.path.realpath(os.path.abspath(os.path.join(base, user_path)))

    # 기본 디렉토리 하위인지 검증 (os.sep 추가로 '/data/finetune2' 같은 형제 디렉토리 차단)
    if not (joined == base or joined.startswith(base + os.sep)):
        raise ValueError(f'경로가 허용 범위를 벗어났습니다: {user_path}')

    return joined


# 콘텐츠 입력 최대 길이 (문자 수, ~500KB 상당)
MAX_CONTENT_CHARS = 500_000


def validate_content_length(content: str, max_chars: int = MAX_CONTENT_CHARS) -> str | None:
    """콘텐츠 문자열 길이를 검증합니다.

    Args:
        content: 검증할 콘텐츠 문자열
        max_chars: 최대 허용 문자 수

    Returns:
        None이면 유효, 문자열이면 에러 메시지
    """
    if not isinstance(content, str):
        return '콘텐츠는 문자열이어야 합니다.'
    if len(content) > max_chars:
        return f'콘텐츠가 너무 깁니다. 최대 {max_chars:,}자까지 허용됩니다. (현재: {len(content):,}자)'
    return None


def safe_int(value, default: int = 0) -> int:
    """JSON 요청 파라미터를 안전하게 int로 변환합니다.

    int(), float(), str, None 등 어떤 값이든 ValueError/TypeError 없이 처리.

    Args:
        value: 변환할 값 (data.get()의 반환값)
        default: 변환 실패 시 기본값

    Returns:
        정수 값
    """
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value, default: float = 0.0) -> float:
    """JSON 요청 파라미터를 안전하게 float로 변환합니다.

    Args:
        value: 변환할 값
        default: 변환 실패 시 기본값

    Returns:
        실수 값
    """
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def clamp_query_int(value, default: int = 10, min_val: int = 1, max_val: int = 100) -> int:
    """쿼리 파라미터 정수를 안전 범위로 클램핑.

    Args:
        value: request.args.get()의 결과 (str 또는 None)
        default: 기본값
        min_val: 최소값
        max_val: 최대값 (DB 부하 방지)

    Returns:
        min_val <= result <= max_val 범위의 정수
    """
    try:
        n = int(value) if value is not None else default
    except (ValueError, TypeError):
        n = default
    return max(min_val, min(n, max_val))


def truncate_string(text: str, max_length: int = 200, suffix: str = '...') -> str:
    """긴 문자열을 안전하게 잘라냅니다 (유니코드 서로게이트 깨짐 방지).

    Args:
        text: 원본 문자열
        max_length: 최대 길이 (suffix 포함)
        suffix: 생략 표시 문자열

    Returns:
        max_length 이하로 절단된 문자열
    """
    if not isinstance(text, str) or len(text) <= max_length:
        return text if isinstance(text, str) else ''
    if max_length <= len(suffix):
        return suffix[:max_length]
    return text[:max_length - len(suffix)] + suffix


def mask_sensitive(value: str, visible_chars: int = 4) -> str:
    """API 키/토큰 등 민감 문자열을 마스킹합니다 (로그 안전 출력용).

    Args:
        value: 마스킹할 문자열
        visible_chars: 앞/뒤에 노출할 문자 수

    Returns:
        마스킹된 문자열. 예: 'sk-ab****yz'
    """
    if not isinstance(value, str) or not value:
        return '****'
    if len(value) <= visible_chars * 2:
        return '*' * len(value)
    prefix = value[:visible_chars]
    suffix_part = value[-visible_chars:]
    masked_len = len(value) - visible_chars * 2
    return f'{prefix}{"*" * min(masked_len, 8)}{suffix_part}'
