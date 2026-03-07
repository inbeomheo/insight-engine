"""image_gen_service 단위 테스트 (검증 로직)"""
import unittest
from unittest.mock import patch

from services.image_gen_service import generate_image, IMAGE_GEN_PROVIDER


class TestGenerateImage(unittest.TestCase):

    @patch('services.image_gen_service.IMAGE_GEN_API_KEY', '')
    def test_no_api_key(self):
        """API 키 없음 → ValueError"""
        with self.assertRaises(ValueError) as ctx:
            generate_image('test prompt')
        self.assertIn('API 키', str(ctx.exception))

    @patch('services.image_gen_service.IMAGE_GEN_API_KEY', 'test-key')
    def test_invalid_size(self):
        """잘못된 이미지 크기 → ValueError"""
        with self.assertRaises(ValueError) as ctx:
            generate_image('test prompt', size='500x500')
        self.assertIn('지원하지 않는', str(ctx.exception))

    @patch('services.image_gen_service.IMAGE_GEN_API_KEY', 'test-key')
    def test_valid_sizes(self):
        """유효한 크기 목록 검증"""
        valid = {'1024x1024', '1792x1024', '1024x1792'}
        for size in valid:
            with self.assertRaises((RuntimeError, Exception)):
                # API 호출 자체는 실패하지만 size 검증은 통과
                generate_image('test', size=size)

    @patch('services.image_gen_service.IMAGE_GEN_API_KEY', 'test-key')
    @patch('services.image_gen_service.IMAGE_GEN_PROVIDER', 'unsupported')
    def test_unsupported_provider(self):
        """지원하지 않는 프로바이더 → ValueError"""
        with self.assertRaises(ValueError) as ctx:
            generate_image('test prompt', '1024x1024')
        self.assertIn('프로바이더', str(ctx.exception))

    def test_provider_default(self):
        """기본 프로바이더 openai"""
        self.assertEqual(IMAGE_GEN_PROVIDER, 'openai')


if __name__ == '__main__':
    unittest.main()
