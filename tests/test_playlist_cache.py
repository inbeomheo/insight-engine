"""R16: /api/playlist-videos 결과 캐싱 테스트"""
import time
import threading
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

        # 이 테스트는 프로세스 로컬 TTL만 검증하므로 CI의 Redis 캐시와 격리한다.
        with patch(
            'routes.utility._state._redis_playlist_client',
            return_value=None,
        ):
            # 첫 번째 요청
            self.client.post('/api/playlist-videos',
                             json={'url': url},
                             headers={'Origin': 'http://localhost:3000'})

            # 캐시 타임스탬프를 강제로 과거로 설정
            import routes.utility_routes as ut
            cache_key = "playlist:PLexpired:10"
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
        cache_key = "playlist:PLerror:10"
        self.assertNotIn(cache_key, ut._PLAYLIST_CACHE)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.core.content_service.is_playlist_url', return_value=True)
    @patch('services.core.content_service.get_playlist_videos')
    def test_query_variants_share_normalized_cache_key(self, mock_get, mock_is_pl, mock_supa):
        mock_get.return_value = {'videos': [], 'total': 0}
        base = 'https://youtube.com/playlist?list=PLnormalized'

        self.client.post('/api/playlist-videos', json={'url': base})
        response = self.client.post(
            '/api/playlist-videos',
            json={'url': f'{base}&tracking=unique'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json().get('cached'))
        self.assertEqual(mock_get.call_count, 1)

    def test_playlist_cache_is_bounded(self):
        from routes.utility import _state

        _state._PLAYLIST_CACHE.clear()
        with patch.object(_state, '_PLAYLIST_CACHE_MAX_ITEMS', 2):
            _state.set_playlist_cache('one', {'value': 1}, now=1)
            _state.set_playlist_cache('two', {'value': 2}, now=2)
            _state.set_playlist_cache('three', {'value': 3}, now=3)

        self.assertEqual(list(_state._PLAYLIST_CACHE), ['two', 'three'])

    def test_concurrent_misses_are_singleflight(self):
        from routes.utility import _state

        cache_key = 'playlist:PLsingleflight:10'
        _state._PLAYLIST_CACHE.clear()
        barrier = threading.Barrier(6)
        calls = []
        results = []

        def loader():
            calls.append(1)
            time.sleep(0.05)
            return {'videos': [], 'total': 0}

        def request_cache():
            barrier.wait()
            results.append(_state.get_or_load_playlist_cache(cache_key, loader))

        workers = [threading.Thread(target=request_cache) for _ in range(6)]
        with patch.dict('os.environ', {'REDIS_URL': ''}):
            for worker in workers:
                worker.start()
            for worker in workers:
                worker.join(timeout=2)

        self.assertTrue(all(not worker.is_alive() for worker in workers))
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(results), 6)
        self.assertEqual(sum(1 for _data, cached in results if not cached), 1)

    def test_redis_lock_and_cache_cover_cross_process_workers(self):
        from routes.utility import _state

        _state._PLAYLIST_CACHE.clear()
        redis_client = MagicMock()
        redis_client.get.side_effect = [None, None]
        redis_lock = MagicMock()
        redis_lock.acquire.return_value = True
        redis_client.lock.return_value = redis_lock
        loader = MagicMock(return_value={'videos': [], 'total': 0})

        with patch.object(_state, '_redis_playlist_client', return_value=redis_client):
            result, cached = _state.get_or_load_playlist_cache(
                'playlist:PLredis:10',
                loader,
            )

        self.assertFalse(cached)
        self.assertEqual(result['total'], 0)
        loader.assert_called_once_with()
        redis_lock.acquire.assert_called_once_with(blocking=True)
        redis_lock.release.assert_called_once_with()
        redis_client.setex.assert_called_once()

    def test_redis_path_preserves_usage_lock_loss(self):
        from routes.utility import _state
        from services.usage.usage_lock import UsageLockUnavailable

        _state._PLAYLIST_CACHE.clear()
        redis_client = MagicMock()
        redis_client.get.side_effect = [None, None]
        redis_lock = MagicMock()
        redis_lock.acquire.return_value = True
        redis_client.lock.return_value = redis_lock
        loader = MagicMock(side_effect=UsageLockUnavailable('lease lost'))

        with patch.object(
            _state,
            '_redis_playlist_client',
            return_value=redis_client,
        ), self.assertRaises(UsageLockUnavailable):
            _state.get_or_load_playlist_cache(
                'playlist:PLredislockloss:10',
                loader,
            )

        redis_lock.release.assert_called_once_with()
        redis_client.setex.assert_not_called()


if __name__ == '__main__':
    unittest.main()
