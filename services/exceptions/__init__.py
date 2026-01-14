"""
Insight Engine 커스텀 예외 모듈
도메인별 예외 클래스 및 에러 응답 헬퍼 제공
"""
from flask import jsonify
from typing import Tuple, Any


class InsightEngineError(Exception):
    """기본 예외 클래스"""

    def __init__(self, message: str, code: str = "UNKNOWN_ERROR", status_code: int = 500):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(self.message)

    def to_response(self) -> Tuple[Any, int]:
        """Flask JSON 응답으로 변환"""
        return jsonify({
            'error': self.message,
            'code': self.code
        }), self.status_code


class ValidationError(InsightEngineError):
    """입력 검증 오류"""

    def __init__(self, message: str, field: str = None):
        code = f"VALIDATION_ERROR:{field}" if field else "VALIDATION_ERROR"
        super().__init__(message, code, 400)
        self.field = field


class AuthenticationError(InsightEngineError):
    """인증 오류"""

    def __init__(self, message: str = "인증이 필요합니다.", code: str = "AUTH_REQUIRED"):
        super().__init__(message, code, 401)


class TokenExpiredError(AuthenticationError):
    """토큰 만료 오류"""

    def __init__(self, message: str = "인증 토큰이 만료되었습니다."):
        super().__init__(message, "TOKEN_EXPIRED")


class TokenInvalidError(AuthenticationError):
    """토큰 무효 오류"""

    def __init__(self, message: str = "유효하지 않은 인증 토큰입니다."):
        super().__init__(message, "TOKEN_INVALID")


class UsageLimitError(InsightEngineError):
    """사용량 제한 오류"""

    def __init__(self, message: str = "오늘 사용 가능 횟수를 모두 소진했습니다.", usage: dict = None):
        super().__init__(message, "USAGE_LIMIT_EXCEEDED", 429)
        self.usage = usage or {}

    def to_response(self) -> Tuple[Any, int]:
        """사용량 정보 포함 응답"""
        return jsonify({
            'error': self.message,
            'code': self.code,
            'usage': self.usage
        }), self.status_code


class TranscriptError(InsightEngineError):
    """자막 추출 오류"""

    def __init__(self, message: str, video_id: str = None):
        code = "TRANSCRIPT_ERROR"
        super().__init__(message, code, 500)
        self.video_id = video_id


class TranscriptNotFoundError(TranscriptError):
    """자막 없음 오류"""

    def __init__(self, video_id: str = None):
        message = "이 영상에는 자막이 없습니다."
        super().__init__(message, video_id)
        self.code = "TRANSCRIPT_NOT_FOUND"
        self.status_code = 404


class YouTubeError(InsightEngineError):
    """YouTube API 관련 오류"""

    def __init__(self, message: str, video_id: str = None):
        super().__init__(message, "YOUTUBE_ERROR", 500)
        self.video_id = video_id


class InvalidURLError(ValidationError):
    """잘못된 URL 오류"""

    def __init__(self, url: str = None):
        message = "유효하지 않은 YouTube URL입니다."
        super().__init__(message, "url")
        self.url = url


class AIServiceError(InsightEngineError):
    """AI 서비스 오류"""

    def __init__(self, message: str, provider: str = None, model: str = None):
        super().__init__(message, "AI_SERVICE_ERROR", 500)
        self.provider = provider
        self.model = model


class APIKeyError(AIServiceError):
    """API 키 오류"""

    def __init__(self, message: str = "API 키가 유효하지 않습니다.", provider: str = None):
        super().__init__(message, provider)
        self.code = "API_KEY_ERROR"
        self.status_code = 401


class RateLimitError(AIServiceError):
    """API 속도 제한 오류"""

    def __init__(self, message: str = "API 요청 제한에 도달했습니다. 잠시 후 다시 시도해주세요.", provider: str = None):
        super().__init__(message, provider)
        self.code = "RATE_LIMIT_ERROR"
        self.status_code = 429


class EncryptionError(InsightEngineError):
    """암호화/복호화 오류"""

    def __init__(self, message: str = "암호화 처리 중 오류가 발생했습니다."):
        super().__init__(message, "ENCRYPTION_ERROR", 500)


class ConfigurationError(InsightEngineError):
    """설정 오류 (환경변수 누락 등)"""

    def __init__(self, message: str, config_key: str = None):
        super().__init__(message, "CONFIGURATION_ERROR", 500)
        self.config_key = config_key


# 에러 응답 헬퍼 함수
def error_response(message: str, code: str = "ERROR", status_code: int = 500) -> Tuple[Any, int]:
    """표준 에러 응답 생성"""
    return jsonify({
        'error': message,
        'code': code
    }), status_code


def handle_exception(e: Exception) -> Tuple[Any, int]:
    """예외를 JSON 응답으로 변환"""
    if isinstance(e, InsightEngineError):
        return e.to_response()

    # 알 수 없는 예외
    return error_response(
        message=str(e) or "알 수 없는 오류가 발생했습니다.",
        code="UNKNOWN_ERROR",
        status_code=500
    )


__all__ = [
    'InsightEngineError',
    'ValidationError',
    'AuthenticationError',
    'TokenExpiredError',
    'TokenInvalidError',
    'UsageLimitError',
    'TranscriptError',
    'TranscriptNotFoundError',
    'YouTubeError',
    'InvalidURLError',
    'AIServiceError',
    'APIKeyError',
    'RateLimitError',
    'EncryptionError',
    'ConfigurationError',
    'error_response',
    'handle_exception',
]
