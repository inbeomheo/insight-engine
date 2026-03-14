"""video_clip_service 단위 테스트"""
import os
import unittest
from unittest.mock import patch, MagicMock

from services.media.video_clip_service import extract_clips, cleanup_clips, _extract_clip


class TestVideoClipService(unittest.TestCase):

    def test_extract_clips_empty_list_raises(self):
        with self.assertRaises(ValueError):
            extract_clips('https://youtube.com/watch?v=test', [])

    def test_extract_clips_too_many_raises(self):
        clips = [{'start': '0:00', 'end': '0:10'}] * 11
        with self.assertRaises(ValueError):
            extract_clips('https://youtube.com/watch?v=test', clips)

    def test_extract_clips_missing_fields_raises(self):
        with self.assertRaises(ValueError):
            extract_clips('https://youtube.com/watch?v=test', [{'start': '0:00'}])

    @patch('services.video_clip_service._extract_clip')
    @patch('services.video_clip_service._download_video')
    def test_extract_clips_success(self, mock_download, mock_extract):
        mock_download.return_value = '/tmp/source.mp4'
        mock_extract.return_value = '/tmp/clip_0.mp4'

        clips = [{'start': '0:00', 'end': '0:30'}]
        result = extract_clips('https://youtube.com/watch?v=test', clips)

        self.assertEqual(len(result), 1)
        mock_download.assert_called_once()
        mock_extract.assert_called_once()

    def test_cleanup_clips_nonexistent(self):
        # 존재하지 않는 파일도 에러 없이 처리
        cleanup_clips(['/tmp/nonexistent_clip.mp4'])


class TestExtractClip(unittest.TestCase):

    @patch('services.video_clip_service.subprocess.run')
    def test_extract_clip_ffmpeg_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stderr='error')
        with self.assertRaises(RuntimeError):
            _extract_clip('/tmp/source.mp4', '0:00', '0:30', 0)

    @patch('services.video_clip_service.subprocess.run')
    def test_extract_clip_ffmpeg_not_found(self, mock_run):
        mock_run.side_effect = FileNotFoundError()
        with self.assertRaises(RuntimeError) as ctx:
            _extract_clip('/tmp/source.mp4', '0:00', '0:30', 0)
        self.assertIn('ffmpeg', str(ctx.exception))


if __name__ == '__main__':
    unittest.main()
