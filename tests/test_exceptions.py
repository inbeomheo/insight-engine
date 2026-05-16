"""services.exceptions 모듈 단위 테스트

14개 예외 클래스의 message/code/status_code/추가 필드 + to_response 구조 검증.
error_response, handle_exception 헬퍼.
"""
import unittest

from flask import Flask

from services.exceptions import (
    InsightEngineError,
    ValidationError,
    AuthenticationError,
    TokenExpiredError,
    TokenInvalidError,
    UsageLimitError,
    TranscriptError,
    TranscriptNotFoundError,
    YouTubeError,
    InvalidURLError,
    AIServiceError,
    APIKeyError,
    RateLimitError,
    EncryptionError,
    ConfigurationError,
    error_response,
    handle_exception,
)


class _FlaskContextMixin:
    """to_response()는 jsonify를 호출하므로 Flask app context 필요"""

    @classmethod
    def setUpClass(cls):
        cls._app = Flask(__name__)

    def _ctx(self):
        return self._app.app_context()


class TestBaseException(_FlaskContextMixin, unittest.TestCase):
    """InsightEngineError 기본 동작"""

    def test_attributes(self):
        e = InsightEngineError('msg', code='C', status_code=418)
        self.assertEqual(e.message, 'msg')
        self.assertEqual(e.code, 'C')
        self.assertEqual(e.status_code, 418)
        self.assertEqual(str(e), 'msg')

    def test_defaults(self):
        e = InsightEngineError('m')
        self.assertEqual(e.code, 'UNKNOWN_ERROR')
        self.assertEqual(e.status_code, 500)

    def test_to_response(self):
        e = InsightEngineError('테스트 메시지', code='TEST', status_code=400)
        with self._ctx():
            body, status = e.to_response()
        self.assertEqual(status, 400)
        data = body.get_json()
        self.assertEqual(data['error'], '테스트 메시지')
        self.assertEqual(data['code'], 'TEST')


class TestValidationError(_FlaskContextMixin, unittest.TestCase):

    def test_without_field(self):
        e = ValidationError('필드 누락')
        self.assertEqual(e.code, 'VALIDATION_ERROR')
        self.assertEqual(e.status_code, 400)
        self.assertIsNone(e.field)

    def test_with_field(self):
        e = ValidationError('이메일 형식 오류', field='email')
        self.assertEqual(e.code, 'VALIDATION_ERROR:email')
        self.assertEqual(e.field, 'email')


class TestAuthExceptions(_FlaskContextMixin, unittest.TestCase):

    def test_authentication_error_default(self):
        e = AuthenticationError()
        self.assertEqual(e.status_code, 401)
        self.assertEqual(e.code, 'AUTH_REQUIRED')
        self.assertIn('인증', e.message)

    def test_token_expired(self):
        e = TokenExpiredError()
        self.assertEqual(e.code, 'TOKEN_EXPIRED')
        self.assertEqual(e.status_code, 401)
        # 상속 확인
        self.assertIsInstance(e, AuthenticationError)
        self.assertIsInstance(e, InsightEngineError)

    def test_token_invalid(self):
        e = TokenInvalidError()
        self.assertEqual(e.code, 'TOKEN_INVALID')
        self.assertEqual(e.status_code, 401)


class TestUsageLimitError(_FlaskContextMixin, unittest.TestCase):

    def test_default(self):
        e = UsageLimitError()
        self.assertEqual(e.status_code, 429)
        self.assertEqual(e.code, 'USAGE_LIMIT_EXCEEDED')
        self.assertEqual(e.usage, {})

    def test_with_usage_dict(self):
        e = UsageLimitError(usage={'used': 10, 'limit': 10})
        self.assertEqual(e.usage, {'used': 10, 'limit': 10})

    def test_to_response_includes_usage(self):
        e = UsageLimitError(usage={'remaining': 0})
        with self._ctx():
            body, status = e.to_response()
        data = body.get_json()
        self.assertEqual(status, 429)
        self.assertEqual(data['usage'], {'remaining': 0})


class TestTranscriptErrors(_FlaskContextMixin, unittest.TestCase):

    def test_transcript_error(self):
        e = TranscriptError('파싱 실패', video_id='abc')
        self.assertEqual(e.code, 'TRANSCRIPT_ERROR')
        self.assertEqual(e.status_code, 500)
        self.assertEqual(e.video_id, 'abc')

    def test_transcript_not_found(self):
        e = TranscriptNotFoundError(video_id='xyz')
        self.assertEqual(e.code, 'TRANSCRIPT_NOT_FOUND')
        self.assertEqual(e.status_code, 404)
        self.assertEqual(e.video_id, 'xyz')
        self.assertIsInstance(e, TranscriptError)


class TestYouTubeErrors(_FlaskContextMixin, unittest.TestCase):

    def test_youtube_error(self):
        e = YouTubeError('할당량 초과', video_id='v1')
        self.assertEqual(e.code, 'YOUTUBE_ERROR')
        self.assertEqual(e.video_id, 'v1')

    def test_invalid_url_error(self):
        e = InvalidURLError(url='https://bad.example/x')
        self.assertEqual(e.code, 'VALIDATION_ERROR:url')
        self.assertEqual(e.status_code, 400)
        self.assertEqual(e.url, 'https://bad.example/x')
        self.assertIsInstance(e, ValidationError)


class TestAIServiceErrors(_FlaskContextMixin, unittest.TestCase):

    def test_ai_service_error(self):
        e = AIServiceError('모델 응답 실패', provider='gemini', model='gemini-3')
        self.assertEqual(e.code, 'AI_SERVICE_ERROR')
        self.assertEqual(e.provider, 'gemini')
        self.assertEqual(e.model, 'gemini-3')

    def test_api_key_error(self):
        e = APIKeyError(provider='openai')
        self.assertEqual(e.code, 'API_KEY_ERROR')
        self.assertEqual(e.status_code, 401)
        self.assertEqual(e.provider, 'openai')

    def test_rate_limit_error(self):
        e = RateLimitError(provider='deepseek')
        self.assertEqual(e.code, 'RATE_LIMIT_ERROR')
        self.assertEqual(e.status_code, 429)


class TestSystemErrors(_FlaskContextMixin, unittest.TestCase):

    def test_encryption_error(self):
        e = EncryptionError()
        self.assertEqual(e.code, 'ENCRYPTION_ERROR')
        self.assertEqual(e.status_code, 500)

    def test_configuration_error(self):
        e = ConfigurationError('REDIS_URL 미설정', config_key='REDIS_URL')
        self.assertEqual(e.code, 'CONFIGURATION_ERROR')
        self.assertEqual(e.config_key, 'REDIS_URL')


class TestHelperFunctions(_FlaskContextMixin, unittest.TestCase):

    def test_error_response_default(self):
        with self._ctx():
            body, status = error_response('일반 오류')
        self.assertEqual(status, 500)
        self.assertEqual(body.get_json()['code'], 'ERROR')

    def test_error_response_custom(self):
        with self._ctx():
            body, status = error_response('잘못된 요청', code='BAD_REQUEST', status_code=400)
        self.assertEqual(status, 400)
        data = body.get_json()
        self.assertEqual(data['error'], '잘못된 요청')
        self.assertEqual(data['code'], 'BAD_REQUEST')

    def test_handle_exception_for_insight_error(self):
        """InsightEngineError 서브클래스는 to_response 사용"""
        e = ValidationError('필드 누락', field='name')
        with self._ctx():
            body, status = handle_exception(e)
        self.assertEqual(status, 400)
        self.assertEqual(body.get_json()['code'], 'VALIDATION_ERROR:name')

    def test_handle_exception_for_generic_exception(self):
        """일반 Exception은 UNKNOWN_ERROR로 500 반환"""
        e = RuntimeError('예상치 못한 오류')
        with self._ctx():
            body, status = handle_exception(e)
        self.assertEqual(status, 500)
        data = body.get_json()
        self.assertEqual(data['code'], 'UNKNOWN_ERROR')
        self.assertEqual(data['error'], '예상치 못한 오류')

    def test_handle_exception_empty_message_uses_default(self):
        """str(e)가 빈 경우 기본 메시지"""
        e = RuntimeError()
        with self._ctx():
            body, status = handle_exception(e)
        self.assertEqual(status, 500)
        self.assertIn('알 수 없는', body.get_json()['error'])


if __name__ == '__main__':
    unittest.main()
