"""utils/responses 단위 테스트 — HTTP 응답 헬퍼 + 입력 검증/마스킹"""
import os
import tempfile
import unittest

from flask import Flask

from utils.responses import (
    success_response,
    error_response,
    sanitize_error_for_client,
    handle_error,
    api_error,
    api_error_from_exception,
    sanitize_path,
    validate_content_length,
    safe_int,
    safe_float,
    clamp_query_int,
    truncate_string,
    mask_sensitive,
    MAX_CONTENT_CHARS,
)


class _AppCtx:
    @classmethod
    def setUpClass(cls):
        cls._app = Flask(__name__)

    def _ctx(self):
        return self._app.app_context()


class TestSuccessResponse(_AppCtx, unittest.TestCase):

    def test_empty(self):
        with self._ctx():
            resp = success_response()
        self.assertEqual(resp.get_json(), {'success': True})

    def test_with_message(self):
        with self._ctx():
            resp = success_response(message='완료')
        self.assertEqual(resp.get_json()['message'], '완료')

    def test_with_data_merges(self):
        with self._ctx():
            resp = success_response(data={'count': 5, 'id': 'abc'})
        data = resp.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['count'], 5)
        self.assertEqual(data['id'], 'abc')


class TestErrorResponse(_AppCtx, unittest.TestCase):

    def test_default_status(self):
        with self._ctx():
            body, status = error_response('msg')
        self.assertEqual(status, 400)
        self.assertEqual(body.get_json()['error'], 'msg')

    def test_custom_status(self):
        with self._ctx():
            body, status = error_response('not found', status_code=404)
        self.assertEqual(status, 404)


class TestSanitizeErrorForClient(_AppCtx, unittest.TestCase):

    def test_safe_prefix_passes_through(self):
        with self._ctx():
            result = sanitize_error_for_client('[인증 실패] 유효하지 않은 토큰')
        self.assertEqual(result, '[인증 실패] 유효하지 않은 토큰')

    def test_internal_info_masked(self):
        """traceback, file path 등이 포함되면 일반 메시지로 대체"""
        with self._ctx():
            result = sanitize_error_for_client('Traceback at /home/user/app.py')
        self.assertIn('[서버 오류]', result)

    def test_supabase_keyword_masked(self):
        with self._ctx():
            result = sanitize_error_for_client('Supabase connection failed')
        self.assertIn('[서버 오류]', result)


class TestHandleError(_AppCtx, unittest.TestCase):

    def test_exception_returns_500(self):
        with self._ctx():
            body, status = handle_error(RuntimeError('내부 오류'))
        self.assertEqual(status, 500)
        self.assertIn('[서버 오류]', body.get_json()['error'])

    def test_exception_with_log_detail(self):
        with self._ctx():
            body, status = handle_error(RuntimeError('x'), log_detail='발행')
        self.assertIn('발행', body.get_json()['error'])

    def test_auth_failure_returns_401(self):
        with self._ctx():
            body, status = handle_error('[인증 실패] 토큰 만료')
        self.assertEqual(status, 401)

    def test_usage_limit_returns_429(self):
        with self._ctx():
            body, status = handle_error('[사용량 초과] 일일 한도 초과')
        self.assertEqual(status, 429)

    def test_known_prefix_returns_503(self):
        with self._ctx():
            body, status = handle_error('[모델 오류] 응답 실패')
        self.assertEqual(status, 503)

    def test_api_key_keyword_returns_401(self):
        with self._ctx():
            body, status = handle_error('API 키가 잘못되었습니다')
        self.assertEqual(status, 401)

    def test_unknown_error_returns_500(self):
        with self._ctx():
            body, status = handle_error('알 수 없는 오류')
        self.assertEqual(status, 500)


class TestApiError(_AppCtx, unittest.TestCase):

    def test_basic(self):
        with self._ctx():
            body, status = api_error('잘못된 요청')
        self.assertEqual(status, 400)
        self.assertEqual(body.get_json()['error'], '잘못된 요청')

    def test_with_code(self):
        with self._ctx():
            body, status = api_error('msg', status_code=403, error_code='FORBIDDEN')
        self.assertEqual(status, 403)
        self.assertEqual(body.get_json()['code'], 'FORBIDDEN')


class TestApiErrorFromException(_AppCtx, unittest.TestCase):

    def test_hides_exception_details(self):
        with self._ctx():
            body, status = api_error_from_exception(
                RuntimeError('connection to db host=secret-host failed'),
                fallback_message='서버 오류'
            )
        self.assertEqual(status, 500)
        # 내부 정보가 노출되지 않음
        data = body.get_json()
        self.assertEqual(data['error'], '서버 오류')
        self.assertNotIn('secret-host', data['error'])


class TestSanitizePath(unittest.TestCase):

    def setUp(self):
        self.base = tempfile.mkdtemp(prefix='ie_sanitize_')

    def tearDown(self):
        import shutil
        shutil.rmtree(self.base, ignore_errors=True)

    def test_simple_relative_path(self):
        result = sanitize_path('file.txt', self.base)
        # realpath 정규화된 절대 경로
        self.assertTrue(result.endswith('file.txt'))
        self.assertTrue(os.path.realpath(result).startswith(os.path.realpath(self.base)))

    def test_traversal_blocked(self):
        for bad in (
            '../etc/passwd',
            '../../secret',
            '..\\windows\\system32',
            'C:\\windows\\system32',
            '\\\\server\\share',
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    sanitize_path(bad, self.base)

    def test_sibling_directory_blocked(self):
        """`/data/finetune2`와 `/data/finetune` 혼동 차단"""
        sibling_base = self.base + 'x'  # 다른 디렉토리 같은 prefix
        os.makedirs(sibling_base, exist_ok=True)
        try:
            # base 외부로 가는 경로
            evil_path = os.path.basename(sibling_base) + '/file.txt'
            with self.assertRaises(ValueError):
                sanitize_path('../' + evil_path, self.base)
        finally:
            import shutil
            shutil.rmtree(sibling_base, ignore_errors=True)


class TestValidateContentLength(unittest.TestCase):

    def test_short_valid(self):
        self.assertIsNone(validate_content_length('짧음'))

    def test_at_boundary(self):
        text = 'a' * MAX_CONTENT_CHARS
        self.assertIsNone(validate_content_length(text))

    def test_over_boundary(self):
        text = 'a' * (MAX_CONTENT_CHARS + 1)
        result = validate_content_length(text)
        self.assertIsNotNone(result)
        self.assertIn('너무 깁니다', result)

    def test_custom_max(self):
        self.assertEqual(validate_content_length('hello', max_chars=3),
                         f'콘텐츠가 너무 깁니다. 최대 3자까지 허용됩니다. (현재: 5자)')

    def test_non_string(self):
        for bad in (None, 123, ['list'], {'dict': 1}):
            with self.subTest(bad=bad):
                self.assertIsNotNone(validate_content_length(bad))


class TestSafeIntFloat(unittest.TestCase):

    def test_safe_int_valid(self):
        self.assertEqual(safe_int(5), 5)
        self.assertEqual(safe_int('42'), 42)
        self.assertEqual(safe_int(3.7), 3)

    def test_safe_int_invalid(self):
        self.assertEqual(safe_int(None), 0)
        self.assertEqual(safe_int('abc'), 0)
        self.assertEqual(safe_int([1, 2]), 0)

    def test_safe_int_custom_default(self):
        self.assertEqual(safe_int('abc', default=10), 10)

    def test_safe_float_valid(self):
        self.assertEqual(safe_float(3.14), 3.14)
        self.assertEqual(safe_float('2.5'), 2.5)
        self.assertEqual(safe_float(7), 7.0)

    def test_safe_float_invalid(self):
        self.assertEqual(safe_float(None), 0.0)
        self.assertEqual(safe_float('not a number'), 0.0)


class TestClampQueryInt(unittest.TestCase):

    def test_within_range(self):
        self.assertEqual(clamp_query_int('50'), 50)

    def test_below_min_clamped(self):
        self.assertEqual(clamp_query_int('0', min_val=1), 1)

    def test_above_max_clamped(self):
        self.assertEqual(clamp_query_int('500', max_val=100), 100)

    def test_none_uses_default(self):
        self.assertEqual(clamp_query_int(None, default=20), 20)

    def test_invalid_uses_default(self):
        self.assertEqual(clamp_query_int('abc', default=15), 15)


class TestTruncateString(unittest.TestCase):

    def test_short_unchanged(self):
        self.assertEqual(truncate_string('짧음'), '짧음')

    def test_long_truncated(self):
        text = 'a' * 500
        result = truncate_string(text, max_length=10)
        self.assertEqual(len(result), 10)
        self.assertTrue(result.endswith('...'))

    def test_non_string(self):
        self.assertEqual(truncate_string(None), '')
        self.assertEqual(truncate_string(123), '')

    def test_max_length_smaller_than_suffix(self):
        result = truncate_string('hello world', max_length=2)
        self.assertEqual(len(result), 2)


class TestMaskSensitive(unittest.TestCase):

    def test_long_value(self):
        result = mask_sensitive('sk-1234567890abcdef')
        self.assertTrue(result.startswith('sk-1'))
        self.assertTrue(result.endswith('cdef'))
        self.assertIn('*', result)

    def test_short_value_fully_masked(self):
        result = mask_sensitive('abc')
        self.assertEqual(result, '***')

    def test_empty(self):
        self.assertEqual(mask_sensitive(''), '****')
        self.assertEqual(mask_sensitive(None), '****')

    def test_custom_visible_chars(self):
        result = mask_sensitive('1234567890', visible_chars=2)
        self.assertTrue(result.startswith('12'))
        self.assertTrue(result.endswith('90'))


if __name__ == '__main__':
    unittest.main()
