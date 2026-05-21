"""payment 서브 라우트 공용 에러 응답 헬퍼."""
import logging

from utils.responses import error_response, sanitize_error_for_client

logger = logging.getLogger(__name__)


def safe_payment_error_response(message, fallback_message, status_code=500):
    safe_message = sanitize_error_for_client(str(message or ''))
    if safe_message.startswith('[서버 오류]'):
        safe_message = fallback_message
    return error_response(safe_message, status_code)


def payment_exception_response(log_context, error, fallback_message, status_code=500):
    logger.error('%s: %s', log_context, error, exc_info=True)
    return error_response(fallback_message, status_code)
