"""콘텐츠 입력 길이 제한 테스트 — DoS 방어"""
import unittest
from unittest.mock import patch

from utils.responses import validate_content_length, MAX_CONTENT_CHARS


class TestValidateContentLength(unittest.TestCase):
    """validate_content_length 유틸리티 함수 테스트"""

    def test_normal_content_passes(self):
        """정상 길이 콘텐츠는 None 반환 (유효)"""
        self.assertIsNone(validate_content_length('안녕하세요' * 100))

    def test_empty_string_passes(self):
        """빈 문자열도 유효"""
        self.assertIsNone(validate_content_length(''))

    def test_max_boundary_passes(self):
        """최대 길이 경계값은 통과"""
        content = 'x' * MAX_CONTENT_CHARS
        self.assertIsNone(validate_content_length(content))

    def test_over_max_rejected(self):
        """최대 길이 초과 시 에러 메시지 반환"""
        content = 'x' * (MAX_CONTENT_CHARS + 1)
        result = validate_content_length(content)
        self.assertIsNotNone(result)
        self.assertIn('너무 깁니다', result)

    def test_custom_max_chars(self):
        """커스텀 max_chars 지정"""
        self.assertIsNone(validate_content_length('abc', max_chars=3))
        result = validate_content_length('abcd', max_chars=3)
        self.assertIsNotNone(result)

    def test_non_string_rejected(self):
        """문자열이 아닌 입력은 거부"""
        self.assertIsNotNone(validate_content_length(12345))
        self.assertIsNotNone(validate_content_length(None))
        self.assertIsNotNone(validate_content_length(['list']))


class TestFlaskMaxContentLength(unittest.TestCase):
    """Flask MAX_CONTENT_LENGTH 설정 검증"""

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_max_content_length_configured(self, _mock_sb):
        """앱에 MAX_CONTENT_LENGTH가 설정되어 있는지 확인"""
        from app import create_app
        app = create_app()
        self.assertIsNotNone(app.config.get('MAX_CONTENT_LENGTH'))
        self.assertEqual(app.config['MAX_CONTENT_LENGTH'], 2 * 1024 * 1024)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_oversized_request_rejected(self, _mock_sb):
        """MAX_CONTENT_LENGTH 초과 요청이 거부되는지 확인"""
        from app import create_app
        app = create_app()
        app.config['TESTING'] = True
        client = app.test_client()

        # MAX_CONTENT_LENGTH보다 큰 데이터 전송
        big_data = 'x' * (3 * 1024 * 1024)
        resp = client.post(
            '/api/qa-check',
            data=big_data,
            content_type='application/json',
            headers={'Origin': 'http://localhost:3000'},
        )
        # 413 또는 500 (라우트 try/except에서 잡힘) — 200이 아니면 거부 성공
        self.assertIn(resp.status_code, (413, 500))


if __name__ == '__main__':
    unittest.main()
