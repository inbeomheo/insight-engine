"""integrations 라우트 패키지 공용 헬퍼."""
from utils.responses import sanitize_error_for_client


def sanitize_integration_error(message, fallback_message):
    raw_message = str(message or '')
    safe_message = sanitize_error_for_client(raw_message)

    # 외부 서비스가 "사용자 메시지: 내부 상세" 형태로 원문 예외를 포함한 경우 차단합니다.
    if safe_message == raw_message and ': ' in raw_message:
        return fallback_message
    if safe_message.startswith('[서버 오류]'):
        return fallback_message
    return safe_message
