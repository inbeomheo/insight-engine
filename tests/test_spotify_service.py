"""Spotify 에피소드 메타데이터 추출 테스트"""
import unittest
from unittest.mock import patch, MagicMock

from services.spotify_service import (
    is_spotify_episode_url,
    get_episode_id,
    get_episode_info,
)


class TestSpotifyUrlParsing(unittest.TestCase):
    """Spotify URL 파싱 테스트"""

    def test_valid_episode_url(self):
        url = "https://open.spotify.com/episode/4rOoJ6Egrf8K2IrywzwOMk"
        self.assertTrue(is_spotify_episode_url(url))

    def test_valid_episode_url_with_params(self):
        url = "https://open.spotify.com/episode/4rOoJ6Egrf8K2IrywzwOMk?si=abc123"
        self.assertTrue(is_spotify_episode_url(url))

    def test_playlist_url_not_episode(self):
        url = "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"
        self.assertFalse(is_spotify_episode_url(url))

    def test_track_url_not_episode(self):
        url = "https://open.spotify.com/track/abc123"
        self.assertFalse(is_spotify_episode_url(url))

    def test_non_spotify_url(self):
        url = "https://example.com/episode/abc"
        self.assertFalse(is_spotify_episode_url(url))

    def test_extract_episode_id(self):
        url = "https://open.spotify.com/episode/4rOoJ6Egrf8K2IrywzwOMk"
        self.assertEqual(get_episode_id(url), "4rOoJ6Egrf8K2IrywzwOMk")

    def test_extract_episode_id_none(self):
        url = "https://example.com"
        self.assertIsNone(get_episode_id(url))


class TestSpotifyEpisodeInfo(unittest.TestCase):
    """Spotify oEmbed 메타데이터 추출 테스트"""

    @patch('services.spotify_service.requests.get')
    def test_get_episode_info_success(self, mock_get):
        """oEmbed 성공 응답"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            'title': 'AI 트렌드 2026',
            'description': '최신 AI 동향을 분석합니다.',
            'thumbnail_url': 'https://i.scdn.co/image/abc123',
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = get_episode_info("https://open.spotify.com/episode/abc123")

        self.assertEqual(result['title'], 'AI 트렌드 2026')
        self.assertEqual(result['provider'], 'spotify')
        self.assertIn('thumbnail_url', result)
        mock_get.assert_called_once()

    @patch('services.spotify_service.requests.get')
    def test_get_episode_info_network_error(self, mock_get):
        """네트워크 오류 시 ValueError"""
        import requests as req_lib
        mock_get.side_effect = req_lib.exceptions.ConnectionError("timeout")

        with self.assertRaises(ValueError) as ctx:
            get_episode_info("https://open.spotify.com/episode/abc123")
        self.assertIn('Spotify', str(ctx.exception))

    def test_get_episode_info_invalid_url(self):
        """유효하지 않은 URL 시 ValueError"""
        with self.assertRaises(ValueError):
            get_episode_info("https://example.com/not-spotify")


if __name__ == '__main__':
    unittest.main()
