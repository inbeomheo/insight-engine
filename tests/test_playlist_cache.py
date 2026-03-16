"""R16: /api/playlist-videos 결과 캐싱 테스트"""
import time
import unittest
from unittest.mock import patch, MagicMock

from app import create_app


class TestPlaylistCache(unittest.TestCase):
    """재생목록 조회 캐시 동작 검증"""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

        # 캐시 초기화
        import routes.utility_routes as ut
        ut._PLAYLIST_CACHE.clear()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.core.content_service.is_playlist_url', return_value=True)
    @patch('services.core.content_service.get_playlist_videos')
    def test_first_request_not_cached(self, mock_get, mock_is_pl, mock_supa):
        """첫 요청은 캐시가 아닌 실제 호출"""
        mock_get.return_value = {'videos': [{'videoId': 'abc', 'title': 'T1'}], 'total': 1}

        resp = self.client.post('/api/playlist-videos',
                                json={'url': 'https://youtube.com/playlist?list=PLtest123'},
                                headers={'Origin': 'http://localhost:3000'})

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertNotIn('cached', data)
        mock_get.assert_called_once()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.core.content_service.is_playlist_url', return_value=True)
    @patch('services.core.content_service.get_playlist_videos')
    def test_second_request_cached(self, mock_get, mock_is_pl, mock_supa):
        """두 번째 요청은 캐시에서 반환"""
        mock_get.return_value = {'videos': [{'videoId': 'abc', 'title': 'T1'}], 'total': 1}

        url = 'https://youtube.com/playlist?list=PLtest456'

        # 첫 번째 요청
        self.client.post('/api/playlist-videos',
                         json={'url': url},
                         headers={'Origin': 'http://localhost:3000'})
        self.assertEqual(mock_get.call_count, 1)

        # 두 번째 요청 — 캐시 히트
        resp2 = self.client.post('/api/playlist-videos',
                                 json={'url': url},
                                 headers={'Origin': 'http://localhost:3000'})
        data2 = resp2.get_json()
        self.assertTrue(data2.get('cached'))
        # get_playlist_videos는 1번만 호출되어야 함
        self.assertEqual(mock_get.call_count, 1)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.core.content_service.is_playlist_url', return_value=True)
    @patch('services.core.content_service.get_playlist_videos')
    def test_cache_expires_after_ttl(self, mock_get, mock_is_pl, mock_supa):
        """TTL 만료 후 캐시 미스"""
        mock_get.return_value = {'videos': [], 'total': 0}

        url = 'https://youtube.com/playlist?list=PLexpired'

        # 첫 번째 요청
        self.client.post('/api/playlist-videos',
                         json={'url': url},
                         headers={'Origin': 'http://localhost:3000'})

        # 캐시 타임스탬프를 강제로 과거로 설정
        import routes.utility_routes as ut
        cache_key = f"{url}|10"
        ut._PLAYLIST_CACHE[cache_key]['ts'] = time.time() - 400  # 5분 초과

        # 두 번째 요청 — 캐시 만료, 재호출
        self.client.post('/api/playlist-videos',
                         json={'url': url},
                         headers={'Origin': 'http://localhost:3000'})
        self.assertEqual(mock_get.call_count, 2)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.core.content_service.is_playlist_url', return_value=True)
    @patch('services.core.content_service.get_playlist_videos')
    def test_error_result_not_cached(self, mock_get, mock_is_pl, mock_supa):
        """에러 결과는 캐시하지 않음"""
        mock_get.return_value = {'error': '재생목록 조회 실패'}

        url = 'https://youtube.com/playlist?list=PLerror'

        resp = self.client.post('/api/playlist-videos',
                                json={'url': url},
                                headers={'Origin': 'http://localhost:3000'})
        self.assertEqual(resp.status_code, 400)

        import routes.utility_routes as ut
        cache_key = f"{url}|10"
        self.assertNotIn(cache_key, ut._PLAYLIST_CACHE)


if __name__ == '__main__':
    unittest.main()
