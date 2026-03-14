"""팟캐스트 URL 감지 + 콘텐츠 수집 테스트"""
import unittest
from unittest.mock import patch, MagicMock

from services.content.multi_source_collector import (
    detect_source_type,
    SOURCE_PODCAST,
    SOURCE_YOUTUBE,
    SOURCE_WEBPAGE,
)


class TestPodcastDetection(unittest.TestCase):
    """팟캐스트 URL 자동 감지 테스트"""

    def test_spotify_episode_url(self):
        url = "https://open.spotify.com/episode/4rOoJ6Egrf8K2IrywzwOMk"
        self.assertEqual(detect_source_type(url), SOURCE_PODCAST)

    def test_apple_podcast_url(self):
        url = "https://podcasts.apple.com/us/podcast/example-show/id123456?i=1000"
        self.assertEqual(detect_source_type(url), SOURCE_PODCAST)

    def test_anchor_fm_url(self):
        url = "https://anchor.fm/my-podcast/episodes/ep-1"
        self.assertEqual(detect_source_type(url), SOURCE_PODCAST)

    def test_podbean_url(self):
        url = "https://podbean.com/ew/pb-abcde-123456"
        self.assertEqual(detect_source_type(url), SOURCE_PODCAST)

    def test_soundcloud_url(self):
        url = "https://soundcloud.com/user/podcast-episode"
        self.assertEqual(detect_source_type(url), SOURCE_PODCAST)

    def test_audio_file_url_mp3(self):
        url = "https://example.com/podcast/episode1.mp3"
        self.assertEqual(detect_source_type(url), SOURCE_PODCAST)

    def test_audio_file_url_m4a(self):
        url = "https://cdn.example.com/audio/talk.m4a"
        self.assertEqual(detect_source_type(url), SOURCE_PODCAST)

    def test_audio_file_url_ogg(self):
        url = "https://example.com/audio.ogg"
        self.assertEqual(detect_source_type(url), SOURCE_PODCAST)

    def test_youtube_not_podcast(self):
        """YouTube URL은 팟캐스트가 아닌 YouTube로 감지"""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        self.assertEqual(detect_source_type(url), SOURCE_YOUTUBE)

    def test_regular_webpage_not_podcast(self):
        """일반 웹페이지는 podcast가 아님"""
        url = "https://example.com/blog/article"
        self.assertEqual(detect_source_type(url), SOURCE_WEBPAGE)

    def test_spotify_non_episode_not_podcast(self):
        """Spotify 플레이리스트는 podcast가 아님 (에피소드만)"""
        url = "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"
        # playlist는 podcast 도메인이므로 podcast로 감지됨
        self.assertEqual(detect_source_type(url), SOURCE_PODCAST)


class TestPodcastCollector(unittest.TestCase):
    """팟캐스트 콘텐츠 수집 테스트"""

    @patch('services.spotify_service.is_spotify_episode_url', return_value=True)
    @patch('services.spotify_service.get_episode_info')
    def test_collect_spotify_episode(self, mock_info, mock_is_spotify):
        """Spotify 에피소드 수집 — oEmbed 메타데이터 사용"""
        mock_info.return_value = {
            'title': '테스트 팟캐스트 에피소드',
            'description': '이 에피소드에서는 AI 기술의 최신 동향에 대해 이야기합니다. ' * 5,
            'thumbnail_url': 'https://example.com/thumb.jpg',
            'provider': 'spotify',
        }

        from services.content.multi_source_collector import _collect_podcast
        result = _collect_podcast("https://open.spotify.com/episode/abc123")

        self.assertEqual(result['title'], '테스트 팟캐스트 에피소드')
        self.assertEqual(result['source_type'], SOURCE_PODCAST)
        self.assertEqual(result['provider'], 'spotify')
        self.assertIn('AI 기술', result['content'])

    @patch('services.whisper_service._cleanup_file')
    @patch('services.whisper_service.transcribe_audio', return_value='전사된 텍스트입니다.')
    @patch('services.whisper_service.download_audio', return_value='/tmp/audio.wav')
    @patch.dict('os.environ', {'WHISPER_ENABLED': 'true', 'WHISPER_MODEL_SIZE': 'base'})
    @patch('services.spotify_service.is_spotify_episode_url', return_value=False)
    def test_collect_audio_url_whisper(self, mock_is_spotify, mock_download, mock_transcribe, mock_cleanup):
        """일반 오디오 URL → Whisper 전사"""
        from services.content.multi_source_collector import _collect_podcast
        result = _collect_podcast("https://example.com/podcast.mp3")

        mock_download.assert_called_once_with("https://example.com/podcast.mp3")
        mock_transcribe.assert_called_once_with('/tmp/audio.wav', 'base')
        self.assertEqual(result['content'], '전사된 텍스트입니다.')
        self.assertEqual(result['provider'], 'whisper')
        mock_cleanup.assert_called_once()

    @patch.dict('os.environ', {'WHISPER_ENABLED': 'false'})
    @patch('services.spotify_service.is_spotify_episode_url', return_value=False)
    def test_collect_audio_whisper_disabled(self, mock_is_spotify):
        """Whisper 비활성화 시 에러"""
        from services.content.multi_source_collector import _collect_podcast
        with self.assertRaises(ValueError) as ctx:
            _collect_podcast("https://example.com/podcast.mp3")
        self.assertIn('WHISPER_ENABLED', str(ctx.exception))


if __name__ == '__main__':
    unittest.main()
