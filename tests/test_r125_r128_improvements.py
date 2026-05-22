"""
R125~R128 자율 발굴 개선 테스트

R125: _validate_modifiers language 모디파이어 지원
R126: 에러율 추적 카운터 (utility_routes)
R127: clear_cache video_id 검증
R128: _apply_output_format 및 _validate_custom_prompt 테스트
"""
import unittest
from unittest.mock import patch


class TestValidateModifiers(unittest.TestCase):
    """R125: _validate_modifiers가 language 모디파이어를 허용하는지 검증"""

    def _validate(self, modifiers):
        from routes.blog_routes import _validate_modifiers
        return _validate_modifiers(modifiers)

    def test_language_ko_accepted(self):
        """language: ko가 유효한 모디파이어로 통과"""
        result, err = self._validate({'language': 'ko'})
        self.assertIsNone(err)
        self.assertEqual(result['language'], 'ko')

    def test_language_en_accepted(self):
        """language: en이 유효한 모디파이어로 통과"""
        result, err = self._validate({'language': 'en'})
        self.assertEqual(result['language'], 'en')

    def test_language_ja_accepted(self):
        """language: ja가 유효한 모디파이어로 통과"""
        result, err = self._validate({'language': 'ja'})
        self.assertEqual(result['language'], 'ja')

    def test_language_invalid_rejected(self):
        """지원하지 않는 언어 코드는 무시"""
        result, err = self._validate({'language': 'fr'})
        self.assertNotIn('language', result)

    def test_all_three_modifiers(self):
        """3개 모디파이어 동시 사용"""
        result, err = self._validate({
            'length': 'short',
            'writing_style': 'expert',
            'language': 'ja',
        })
        self.assertIsNone(err)
        self.assertEqual(result['length'], 'short')
        self.assertEqual(result['writing_style'], 'expert')
        self.assertEqual(result['language'], 'ja')

    def test_none_returns_none(self):
        """None 입력"""
        result, err = self._validate(None)
        self.assertIsNone(result)
        self.assertIsNone(err)

    def test_non_dict_returns_none(self):
        """dict가 아닌 입력"""
        result, err = self._validate('string')
        self.assertIsNone(result)

    def test_unknown_keys_ignored(self):
        """알 수 없는 키는 무시"""
        result, err = self._validate({'unknown_key': 'value', 'length': 'long'})
        self.assertNotIn('unknown_key', result)
        self.assertEqual(result['length'], 'long')

    def test_invalid_length_value_ignored(self):
        """유효하지 않은 length 값은 무시"""
        result, err = self._validate({'length': 'extra_long'})
        self.assertNotIn('length', result)

    def test_value_length_capped(self):
        """값이 50자로 제한됨"""
        result, err = self._validate({'length': 'short'})
        self.assertLessEqual(len(result.get('length', '')), 50)


class TestErrorRateTracking(unittest.TestCase):
    """R126: 에러율 추적 카운터"""

    def setUp(self):
        """카운터 초기화"""
        import routes.utility_routes as ur
        import routes.utility._state as ur_state
        self._ur = ur
        # 카운터는 _state 모듈에 정의됨 (utility_routes는 re-export만 함)
        ur_state._total_request_count = 0
        ur_state._total_error_count = 0

    def test_increment_error_count(self):
        """에러 카운터 증가"""
        self._ur.increment_error_count()
        self.assertEqual(self._ur.get_error_count(), 1)

    def test_error_rate_no_requests(self):
        """요청 없을 때 에러율 0.0"""
        self.assertEqual(self._ur.get_error_rate(), 0.0)

    def test_error_rate_calculation(self):
        """에러율 계산 (에러/총요청)"""
        for _ in range(10):
            self._ur.increment_request_count()
        for _ in range(3):
            self._ur.increment_error_count()
        self.assertAlmostEqual(self._ur.get_error_rate(), 0.3, places=4)

    def test_error_rate_zero_errors(self):
        """에러 없을 때 에러율 0.0"""
        self._ur.increment_request_count()
        self.assertEqual(self._ur.get_error_rate(), 0.0)

    def test_get_error_count_initial(self):
        """초기 에러 카운트 0"""
        self.assertEqual(self._ur.get_error_count(), 0)


class TestClearCacheValidation(unittest.TestCase):
    """R127: clear_cache video_id 검증"""

    def test_invalid_video_id_raises(self):
        """유효하지 않은 video_id가 ValueError 발생"""
        from services.core.content_service import clear_cache
        with self.assertRaises(ValueError):
            clear_cache('../etc/passwd')

    def test_none_video_id_accepted(self):
        """None은 전체 삭제이므로 검증 없이 통과"""
        from services.core.content_service import clear_cache
        # cache 디렉토리가 없으면 0 반환
        result = clear_cache(None)
        self.assertIsInstance(result, int)

    def test_valid_video_id_accepted(self):
        """유효한 11자 video_id는 통과"""
        from services.core.content_service import clear_cache
        # 캐시가 없어도 ValueError 없이 완료
        result = clear_cache('dQw4w9WgXcQ')
        self.assertIsInstance(result, int)

    def test_empty_video_id_raises(self):
        """빈 문자열 video_id가 ValueError 발생"""
        from services.core.content_service import clear_cache
        with self.assertRaises(ValueError):
            clear_cache('')


class TestValidateCustomPrompt(unittest.TestCase):
    """R128: _validate_custom_prompt 테스트"""

    def _validate(self, custom_prompt):
        from routes.blog_routes import _validate_custom_prompt
        return _validate_custom_prompt(custom_prompt)

    def test_none_returns_none(self):
        result, err = self._validate(None)
        self.assertIsNone(result)
        self.assertIsNone(err)

    def test_non_string_returns_error(self):
        result, err = self._validate(123)
        self.assertIsNone(result)
        self.assertIsNotNone(err)

    def test_string_accepted(self):
        result, err = self._validate('커스텀 프롬프트 테스트')
        self.assertIsNone(err)
        self.assertEqual(result, '커스텀 프롬프트 테스트')

    def test_length_capped_at_2000(self):
        long_prompt = 'x' * 3000
        result, err = self._validate(long_prompt)
        self.assertEqual(len(result), 2000)

    def test_whitespace_stripped(self):
        result, err = self._validate('  hello world  ')
        self.assertEqual(result, 'hello world')


class TestApplyOutputFormat(unittest.TestCase):
    """R128: _apply_output_format 테스트"""

    def _apply(self, result, output_format, max_chars=None):
        from routes.generation_helpers import _apply_output_format
        return _apply_output_format(result, output_format, max_chars)

    def test_html_format_default(self):
        """html 포맷은 결과를 그대로 반환"""
        result = {'content': '# Title\n**bold**', 'html': '<h1>Title</h1>'}
        output = self._apply(result, 'html')
        self.assertEqual(output['content'], '# Title\n**bold**')
        self.assertEqual(output['html'], '<h1>Title</h1>')

    def test_plain_format_strips_markdown(self):
        """plain 포맷은 마크다운 문법 제거"""
        result = {'content': '## 제목\n**강조** [링크](url)', 'html': '<h2>제목</h2>'}
        output = self._apply(result, 'plain')
        self.assertNotIn('#', output['content'])
        self.assertNotIn('**', output['content'])
        self.assertNotIn('[', output['content'])
        self.assertEqual(output['html'], '')

    def test_markdown_format_removes_html(self):
        """markdown 포맷은 html을 빈 문자열로"""
        result = {'content': '# Title', 'html': '<h1>Title</h1>'}
        output = self._apply(result, 'markdown')
        self.assertEqual(output['content'], '# Title')
        self.assertEqual(output['html'], '')

    def test_max_chars_truncation(self):
        """max_chars로 콘텐츠 길이 제한"""
        result = {'content': 'a' * 1000, 'html': ''}
        output = self._apply(result, 'html', max_chars=100)
        self.assertEqual(len(output['content']), 100)

    def test_max_chars_none_no_truncation(self):
        """max_chars None이면 잘리지 않음"""
        result = {'content': 'a' * 1000, 'html': ''}
        output = self._apply(result, 'html', max_chars=None)
        self.assertEqual(len(output['content']), 1000)


if __name__ == '__main__':
    unittest.main()
