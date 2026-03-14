"""podcast_service 단위 테스트"""
import unittest
from unittest.mock import patch

from services.media.podcast_service import _parse_script


class TestParseScript(unittest.TestCase):

    def test_basic_parsing(self):
        script = "Host: 안녕하세요\nGuest: 반갑습니다\nHost: 오늘은..."
        result = _parse_script(script)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], ('host', '안녕하세요'))
        self.assertEqual(result[1], ('guest', '반갑습니다'))

    def test_empty_lines_ignored(self):
        script = "Host: Hello\n\nGuest: Hi"
        result = _parse_script(script)
        self.assertEqual(len(result), 2)

    def test_non_tagged_lines_ignored(self):
        script = "Host: Hello\nSome random text\nGuest: Hi"
        result = _parse_script(script)
        self.assertEqual(len(result), 2)


class TestGeneratePodcastEpisode(unittest.TestCase):

    def test_empty_content_raises(self):
        from services.media.podcast_service import generate_podcast_episode
        with self.assertRaises(ValueError):
            generate_podcast_episode('', 'test')

    @patch('services.podcast_service._synthesize_podcast')
    @patch('services.podcast_service._generate_script')
    def test_success(self, mock_gen, mock_synth):
        mock_gen.return_value = "Host: Hello\nGuest: Hi\nHost: Bye"
        mock_synth.return_value = b'\x00' * 100

        from services.media.podcast_service import generate_podcast_episode
        result = generate_podcast_episode('test content', 'Test', 'gemini/test')

        self.assertIn('script', result)
        self.assertIn('audio_base64', result)
        self.assertIn('duration_estimate', result)
        self.assertGreater(result['duration_estimate'], 0)


if __name__ == '__main__':
    unittest.main()
