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
    '[생성 실패]', '[타임아웃]',
    '자막을', '댓글을', 'YouTube', 'API', '영상', 'URL',
]

# 내부 정보 키워드 (노출 차단 대상)
_INTERNAL_KEYWORDS = [
    'traceback', 'exception', 'file "', 'line ', 'error:', 'failed:',
    '/home/', '/usr/', 'supabase', 'postgres', 'connection',
    'api_key', 'token', 'secret', 'password', 'authorization', '.env',
    'openai', 'litellm', 'httpx', 'requests.exceptions',
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
    if log_detail:
        current_app.logger.error(f'Error: {log_detail}')

    is_formatted_error = any(error_msg.startswith(prefix) for prefix in _ERROR_PREFIXES)

    if is_formatted_error:
        if error_msg.startswith('[인증 실패]'):
            return jsonify({'error': error_msg}), 401
        if error_msg.startswith('[사용량 초과]'):
            return jsonify({'error': error_msg}), 429
        return jsonify({'error': error_msg}), 503

    if 'API 키' in error_msg or 'authentication' in error_msg.lower():
        return jsonify({'error': error_msg}), 401

    safe_msg = sanitize_error_for_client(error_msg)
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
