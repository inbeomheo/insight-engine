"""subtitle_overlay_service 단위 테스트"""
import unittest
from unittest.mock import patch, MagicMock

from services.subtitle_overlay_service import add_subtitles, _build_drawtext_filter


class TestBuildDrawtextFilter(unittest.TestCase):

    def test_single_subtitle(self):
        subs = [{'text': 'Hello', 'start': 0.0, 'end': 3.0}]
        result = _build_drawtext_filter(subs)
        self.assertIn("drawtext=text='Hello'", result)
        self.assertIn('between(t,0.0,3.0)', result)

    def test_multiple_subtitles(self):
        subs = [
            {'text': 'First', 'start': 0.0, 'end': 2.0},
            {'text': 'Second', 'start': 2.0, 'end': 4.0},
        ]
        result = _build_drawtext_filter(subs)
        self.assertEqual(result.count('drawtext='), 2)

    def test_special_chars_escaped(self):
        subs = [{'text': "It's a test: here", 'start': 0.0, 'end': 1.0}]
        result = _build_drawtext_filter(subs)
        self.assertIn("\\'", result)
        self.assertIn("\\:", result)


class TestAddSubtitles(unittest.TestCase):

    def test_missing_video_raises(self):
        with self.assertRaises(ValueError):
            add_subtitles('/nonexistent/video.mp4', [{'text': 'a', 'start': 0, 'end': 1}])

    def test_empty_subtitles_raises(self):
        with self.assertRaises(ValueError):
            add_subtitles('/tmp/video.mp4', [])

    def test_missing_fields_raises(self):
        with self.assertRaises(ValueError):
            add_subtitles('/tmp/video.mp4', [{'text': 'a'}])

    @patch('services.subtitle_overlay_service.os.path.exists', return_value=True)
    @patch('services.subtitle_overlay_service.subprocess.run')
    def test_ffmpeg_failure(self, mock_run, mock_exists):
        mock_run.return_value = MagicMock(returncode=1, stderr='error')
        with self.assertRaises(RuntimeError):
            add_subtitles('/tmp/video.mp4', [{'text': 'a', 'start': 0, 'end': 1}])


if __name__ == '__main__':
    unittest.main()
