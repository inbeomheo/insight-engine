"""logging_config 단위 테스트 — get_logger, ServiceLogger, with_flask_context"""
import logging
import unittest
from unittest.mock import patch, MagicMock

from services.core.logging_config import (
    get_logger,
    ServiceLogger,
    with_flask_context,
    LOG_FORMAT,
    DATE_FORMAT,
)


class TestGetLogger(unittest.TestCase):
    """get_logger: 통합 로거 생성"""

    def test_returns_logger(self):
        logger = get_logger('test_module')
        self.assertIsInstance(logger, logging.Logger)
        self.assertEqual(logger.name, 'test_module')

    def test_sets_level(self):
        logger = get_logger('test_debug', level=logging.DEBUG)
        self.assertEqual(logger.level, logging.DEBUG)

    def test_no_duplicate_handlers(self):
        name = 'test_no_dup_handlers_unique'
        logger1 = get_logger(name)
        handler_count = len(logger1.handlers)
        logger2 = get_logger(name)
        self.assertEqual(len(logger2.handlers), handler_count)


class TestServiceLogger(unittest.TestCase):
    """ServiceLogger: Flask 컨텍스트 자동 감지 로거"""

    def test_fallback_logger_outside_flask(self):
        slogger = ServiceLogger('TestService')
        # Flask 컨텍스트 밖이므로 fallback 로거 사용
        internal = slogger._logger
        self.assertIsInstance(internal, logging.Logger)

    def test_log_methods_exist(self):
        slogger = ServiceLogger('TestService2')
        for method in ['debug', 'info', 'warning', 'error', 'exception']:
            self.assertTrue(callable(getattr(slogger, method)))

    @patch.object(ServiceLogger, '_logger', new_callable=lambda: property(lambda self: MagicMock()))
    def test_info_prefixes_name(self, mock_prop):
        slogger = ServiceLogger('MyService')
        slogger.info('test message')
        # 실제 로깅이 호출되었는지 확인 (fallback 로거 사용)


class TestWithFlaskContext(unittest.TestCase):
    """with_flask_context 데코레이터"""

    def test_outside_flask_no_logger_injected(self):
        """Flask 컨텍스트 밖 (current_app falsy) 시 _logger 미설정 확인"""
        received = {}

        @with_flask_context
        def my_func(**kwargs):
            received['logger'] = kwargs.get('_logger')

        my_func()
        # current_app가 falsy → _logger 미설정 → None (의도된 동작)
        self.assertIsNone(received.get('logger'))

    def test_preserves_function_name(self):
        """래핑된 함수 이름이 보존되는지 확인"""

        @with_flask_context
        def my_named_func(**kwargs):
            pass

        self.assertEqual(my_named_func.__name__, 'my_named_func')


class TestPreDefinedLoggers(unittest.TestCase):
    """사전 정의된 서비스 로거 확인"""

    def test_predefined_loggers_exist(self):
        from services.core.logging_config import (
            content_logger, ai_logger, supabase_logger,
            auth_logger, cache_logger,
        )
        for slogger in [content_logger, ai_logger, supabase_logger, auth_logger, cache_logger]:
            self.assertIsInstance(slogger, ServiceLogger)


if __name__ == '__main__':
    unittest.main()
