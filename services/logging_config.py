"""
Insight Engine 통합 로깅 설정
Flask 컨텍스트 유무와 관계없이 동작하는 로거 제공
"""
import logging
import sys
from functools import wraps
from typing import Optional

# 로그 포맷
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    통합 로거 생성/조회
    Flask 컨텍스트 외부에서도 동작하는 로거 반환

    Args:
        name: 로거 이름 (보통 모듈 이름)
        level: 로깅 레벨 (기본: INFO)

    Returns:
        logging.Logger 인스턴스
    """
    logger = logging.getLogger(name)

    # 이미 핸들러가 설정된 경우 중복 방지
    if not logger.handlers:
        logger.setLevel(level)

        # 콘솔 핸들러
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))

        logger.addHandler(console_handler)

    return logger


def with_flask_context(func):
    """
    Flask 컨텍스트에서 current_app.logger 사용, 그 외에는 기본 로거 사용
    서비스 함수에서 사용 가능
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            from flask import current_app
            if current_app:
                kwargs['_logger'] = current_app.logger
        except RuntimeError:
            # Flask 컨텍스트 외부
            kwargs['_logger'] = get_logger(func.__module__)
        return func(*args, **kwargs)
    return wrapper


class ServiceLogger:
    """
    서비스용 로거 클래스
    Flask 컨텍스트 자동 감지
    """

    def __init__(self, name: str):
        self.name = name
        self._fallback_logger: Optional[logging.Logger] = None

    @property
    def _logger(self) -> logging.Logger:
        """현재 컨텍스트에 맞는 로거 반환"""
        try:
            from flask import current_app
            if current_app:
                return current_app.logger
        except RuntimeError:
            pass

        # Flask 컨텍스트 외부 - 폴백 로거 사용
        if self._fallback_logger is None:
            self._fallback_logger = get_logger(self.name)
        return self._fallback_logger

    def debug(self, message: str, *args, **kwargs):
        """DEBUG 레벨 로그"""
        self._logger.debug(f"[{self.name}] {message}", *args, **kwargs)

    def info(self, message: str, *args, **kwargs):
        """INFO 레벨 로그"""
        self._logger.info(f"[{self.name}] {message}", *args, **kwargs)

    def warning(self, message: str, *args, **kwargs):
        """WARNING 레벨 로그"""
        self._logger.warning(f"[{self.name}] {message}", *args, **kwargs)

    def error(self, message: str, *args, **kwargs):
        """ERROR 레벨 로그"""
        self._logger.error(f"[{self.name}] {message}", *args, **kwargs)

    def exception(self, message: str, *args, **kwargs):
        """EXCEPTION 레벨 로그 (스택 트레이스 포함)"""
        self._logger.exception(f"[{self.name}] {message}", *args, **kwargs)


# 사전 정의된 서비스 로거들
content_logger = ServiceLogger('ContentService')
ai_logger = ServiceLogger('AIService')
supabase_logger = ServiceLogger('SupabaseService')
auth_logger = ServiceLogger('AuthService')
cache_logger = ServiceLogger('CacheService')


__all__ = [
    'get_logger',
    'with_flask_context',
    'ServiceLogger',
    'content_logger',
    'ai_logger',
    'supabase_logger',
    'auth_logger',
    'cache_logger',
]
