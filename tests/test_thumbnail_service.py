"""thumbnail_service 단위 테스트"""
import base64
import unittest
from unittest.mock import patch

from services.thumbnail_service import _build_image_prompt, generate_thumbnail


class TestBuildImagePrompt(unittest.TestCase):

    def test_basic_prompt(self):
        """기본 프롬프트 생성"""
        result = _build_image_prompt('AI 기술 동향', ['인공지능', '머신러닝'])
        self.assertIn('AI 기술 동향', result)
        self.assertIn('인공지능', result)
        self.assertIn('머신러닝', result)

    def test_no_keywords(self):
        """키워드 없이 프롬프트 생성"""
        result = _build_image_prompt('제목만', [])
        self.assertIn('제목만', result)
        self.assertNotIn('Keywords:', result)

    def test_keywords_none(self):
        """키워드 None"""
        result = _build_image_prompt('테스트', None)
        self.assertIn('테스트', result)

    def test_max_5_keywords(self):
        """키워드 최대 5개"""
        kws = ['kw1', 'kw2', 'kw3', 'kw4', 'kw5', 'kw6', 'kw7']
        result = _build_image_prompt('제목', kws)
        self.assertIn('kw5', result)
        self.assertNotIn('kw6', result)

    def test_english_prompt(self):
        """영어 프롬프트 생성"""
        result = _build_image_prompt('Test', ['AI'])
        self.assertIn('Create a modern', result)
        self.assertIn('professional', result)


class TestGenerateThumbnail(unittest.TestCase):

    def test_empty_title(self):
        """빈 제목 → 실패"""
        result = generate_thumbnail('')
        self.assertFalse(result['success'])
        self.assertIn('제목', result['error'])

    def test_whitespace_title(self):
        """공백 제목 → 실패"""
        result = generate_thumbnail('   ')
        self.assertFalse(result['success'])

    @patch('services.thumbnail_service.IMAGE_GEN_API_KEY', '')
    def test_no_api_key(self):
        """API 키 없음 → 실패"""
        result = generate_thumbnail('테스트 제목')
        self.assertFalse(result['success'])
        self.assertIn('API 키', result['error'])

    @patch('services.thumbnail_service.generate_image')
    @patch('services.thumbnail_service.IMAGE_GEN_API_KEY', 'test-key')
    def test_success(self, mock_gen):
        """정상 생성"""
        mock_gen.return_value = b'\x89PNG\r\n\x1a\nfake'
        result = generate_thumbnail('AI 트렌드', ['머신러닝'])
        self.assertTrue(result['success'])
        self.assertIn('image_base64', result)
        self.assertIn('prompt', result)
        # base64 디코딩 가능 확인
        decoded = base64.b64decode(result['image_base64'])
        self.assertEqual(decoded, b'\x89PNG\r\n\x1a\nfake')

    @patch('services.thumbnail_service.generate_image', side_effect=RuntimeError('API 오류'))
    @patch('services.thumbnail_service.IMAGE_GEN_API_KEY', 'test-key')
    def test_api_error(self, mock_gen):
        """API 오류 → 실패"""
        result = generate_thumbnail('테스트')
        self.assertFalse(result['success'])
        self.assertIn('API 오류', result['error'])


if __name__ == '__main__':
    unittest.main()
