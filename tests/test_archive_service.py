"""archive_service 단위 테스트"""
import unittest
from unittest.mock import patch

from services.data import archive_service


class TestArchiveService(unittest.TestCase):
    """아카이브 서비스 테스트"""

    def setUp(self):
        """각 테스트 전 로그 초기화"""
        with archive_service._lock:
            archive_service._archive_log.clear()

    @patch('services.data.archive_service.content_library_service.update_item')
    def test_archive_item_success(self, mock_update):
        """아카이브 성공 시 아이템 반환"""
        mock_update.return_value = {'id': 'item1', 'status': 'archived'}
        result = archive_service.archive_item('item1', user_id='u1', reason='정리')
        self.assertEqual(result['id'], 'item1')
        mock_update.assert_called_once_with('item1', is_archived=True, status='archived')

    @patch('services.data.archive_service.content_library_service.update_item')
    def test_archive_item_not_found(self, mock_update):
        """존재하지 않는 아이템 아카이브 시 None"""
        mock_update.return_value = None
        result = archive_service.archive_item('nonexistent')
        self.assertIsNone(result)

    @patch('services.data.archive_service.content_library_service.update_item')
    def test_restore_item_success(self, mock_update):
        """복구 성공 시 아이템 반환"""
        mock_update.return_value = {'id': 'item1', 'status': 'draft'}
        result = archive_service.restore_item('item1', user_id='u1')
        self.assertEqual(result['status'], 'draft')
        mock_update.assert_called_once_with('item1', is_archived=False, status='draft')

    @patch('services.data.archive_service.content_library_service.update_item')
    def test_restore_item_not_found(self, mock_update):
        """존재하지 않는 아이템 복구 시 None"""
        mock_update.return_value = None
        result = archive_service.restore_item('nonexistent')
        self.assertIsNone(result)

    @patch('services.data.archive_service.content_library_service.update_item')
    def test_archive_log_recorded(self, mock_update):
        """아카이브/복구 시 로그 기록"""
        mock_update.return_value = {'id': 'item1'}
        archive_service.archive_item('item1', user_id='u1', reason='테스트')
        log = archive_service.get_archive_log('item1')
        self.assertEqual(len(log), 1)
        self.assertEqual(log[0]['action'], 'archive')
        self.assertEqual(log[0]['user_id'], 'u1')
        self.assertEqual(log[0]['reason'], '테스트')

    @patch('services.data.archive_service.content_library_service.search_items')
    def test_list_archived(self, mock_search):
        """아카이브 목록 조회"""
        mock_search.return_value = {'items': [], 'total': 0}
        result = archive_service.list_archived(workspace_id='ws1')
        mock_search.assert_called_once_with(
            is_archived=True, workspace_id='ws1', user_id='', page=1, per_page=20
        )

    def test_get_archive_log_empty(self):
        """빈 로그 반환"""
        log = archive_service.get_archive_log()
        self.assertEqual(log, [])

    @patch('services.data.archive_service.content_library_service.update_item')
    def test_get_archive_log_filter_by_item(self, mock_update):
        """아이템 ID로 로그 필터링"""
        mock_update.return_value = {'id': 'a'}
        archive_service.archive_item('a', user_id='u')
        archive_service.archive_item('b', user_id='u')
        log_a = archive_service.get_archive_log('a')
        self.assertEqual(len(log_a), 1)
        log_all = archive_service.get_archive_log()
        self.assertEqual(len(log_all), 2)


if __name__ == '__main__':
    unittest.main()
