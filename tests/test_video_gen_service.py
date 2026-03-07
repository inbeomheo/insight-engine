"""video_gen_service 단위 테스트"""
import unittest
from unittest.mock import patch, MagicMock

from services.video_gen_service import (
    _generate_slideshow_ffmpeg,
    VideoGenService,
    RUNWAY_API_KEY,
    PIKA_API_KEY,
)


class TestConstants(unittest.TestCase):

    def test_runway_key_from_env(self):
        """RUNWAY_API_KEY 환경변수 기본값"""
        self.assertIsInstance(RUNWAY_API_KEY, str)

    def test_pika_key_from_env(self):
        """PIKA_API_KEY 환경변수 기본값"""
        self.assertIsInstance(PIKA_API_KEY, str)


class TestGenerateSlideshowFfmpeg(unittest.TestCase):

    def test_empty_images(self):
        """빈 이미지 목록 → ValueError"""
        with self.assertRaises(ValueError) as ctx:
            _generate_slideshow_ffmpeg([])
        self.assertIn('이미지 목록', str(ctx.exception))

    @patch('services.video_gen_service.subprocess.run')
    def test_no_ffmpeg(self, mock_run):
        """FFmpeg 미설치 → RuntimeError"""
        mock_run.side_effect = FileNotFoundError()
        with self.assertRaises(RuntimeError) as ctx:
            _generate_slideshow_ffmpeg([b'fake_image'])
        self.assertIn('FFmpeg', str(ctx.exception))


class TestVideoGenService(unittest.TestCase):

    @patch('services.video_gen_service.RUNWAY_API_KEY', '')
    def test_no_api_key_no_fallback(self):
        """API 키 없음 + 폴백 비활성 → RuntimeError"""
        svc = VideoGenService()
        with self.assertRaises(RuntimeError) as ctx:
            svc.generate_from_text('테스트 프롬프트', fallback_to_slideshow=False)
        self.assertIn('미설정', str(ctx.exception))

    @patch('services.video_gen_service.RUNWAY_API_KEY', '')
    def test_no_api_key_with_fallback(self):
        """API 키 없음 + 폴백 활성 → 슬라이드쇼 안내 에러"""
        svc = VideoGenService()
        with self.assertRaises(RuntimeError) as ctx:
            svc.generate_from_text('테스트 프롬프트', fallback_to_slideshow=True)
        self.assertIn('이미지 목록', str(ctx.exception))

    @patch('services.video_gen_service._generate_with_runway', return_value=b'video_bytes')
    @patch('services.video_gen_service.RUNWAY_API_KEY', 'test-key')
    def test_runway_success(self, mock_runway):
        """RunwayML 성공"""
        svc = VideoGenService()
        result = svc.generate_from_text('비디오 생성')
        self.assertEqual(result, b'video_bytes')

    @patch('services.video_gen_service._generate_with_runway', side_effect=Exception('API error'))
    @patch('services.video_gen_service.RUNWAY_API_KEY', 'test-key')
    def test_runway_fail_no_fallback(self, mock_runway):
        """RunwayML 실패 + 폴백 비활성 → 예외 전파"""
        svc = VideoGenService()
        with self.assertRaises(Exception):
            svc.generate_from_text('비디오', fallback_to_slideshow=False)

    @patch('services.video_gen_service._generate_slideshow_ffmpeg', return_value=b'slideshow')
    def test_generate_slideshow(self, mock_ffmpeg):
        """슬라이드쇼 생성 메서드"""
        svc = VideoGenService()
        result = svc.generate_slideshow([b'img1', b'img2'])
        self.assertEqual(result, b'slideshow')


class TestGenerateWithRunway(unittest.TestCase):

    @patch('services.video_gen_service.RUNWAY_API_KEY', '')
    def test_no_api_key(self):
        """API 키 없음 → RuntimeError"""
        from services.video_gen_service import _generate_with_runway
        with self.assertRaises(RuntimeError) as ctx:
            _generate_with_runway('prompt')
        self.assertIn('RUNWAY_API_KEY', str(ctx.exception))


if __name__ == '__main__':
    unittest.main()
