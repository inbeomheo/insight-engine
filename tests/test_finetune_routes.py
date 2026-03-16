"""파인튜닝 데이터 수집 라우트 단위 테스트."""
import unittest
from unittest.mock import patch, MagicMock

from app import create_app

_HEADERS = {'Origin': 'http://localhost:3000'}


class TestFinetuneRoutes(unittest.TestCase):
    """파인튜닝 데이터 수집 API 테스트."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.finetune.data_collector.AutoDataCollector.collect_from_supabase')
    def test_collect_success(self, mock_collect, _mock_sb):
        """Supabase 수집 성공."""
        mock_collect.return_value = {
            'total_records': 100,
            'quality_passed': 30,
            'quality_failed': 70,
            'dataset_stats': {},
            'save_stats': {},
        }
        resp = self.client.post('/api/finetune/collect',
                                json={'days_back': 7, 'limit': 100},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['total_records'], 100)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.finetune.data_collector.AutoDataCollector.collect_from_supabase')
    def test_collect_error(self, mock_collect, _mock_sb):
        """Supabase 미연결 시 에러."""
        mock_collect.return_value = {'error': 'Supabase 미연결'}
        resp = self.client.post('/api/finetune/collect',
                                json={},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 400)
        self.assertIn('error', resp.get_json())

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_collect_local_missing_path(self, _mock_sb):
        """로컬 수집 시 경로 누락 400."""
        resp = self.client.post('/api/finetune/collect-local',
                                json={},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.finetune.data_collector.AutoDataCollector.collect_from_local_cache')
    def test_collect_local_success(self, mock_collect, _mock_sb):
        """로컬 캐시 수집 성공."""
        mock_collect.return_value = {
            'total_records': 50,
            'quality_passed': 10,
            'quality_failed': 40,
            'dataset_stats': {},
            'save_stats': {},
        }
        resp = self.client.post('/api/finetune/collect-local',
                                json={'cache_db_path': 'cache/test.db'},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])


if __name__ == '__main__':
    unittest.main()
