"""trash_service 단위 테스트"""
import unittest
from unittest.mock import patch

from services import trash_service
from services import content_library_service


class TestTrashService(unittest.TestCase):
    """휴지통 서비스 테스트"""

    def setUp(self):
        """content_library_service 내부 저장소 초기화"""
        with content_library_service._lock:
            content_library_service._items.clear()

    def _add_item(self, item_id, is_deleted=False, **kwargs):
        """테스트용 아이템 직접 추가"""
        item = {'id': item_id, 'is_deleted': is_deleted, 'workspace_id': '', 'user_id': '', **kwargs}
        with content_library_service._lock:
            content_library_service._items[item_id] = item
        return item

    @patch('services.trash_service.content_library_service.delete_item')
    def test_move_to_trash_success(self, mock_delete):
        """소프트 삭제 성공"""
        mock_delete.return_value = True
        self.assertTrue(trash_service.move_to_trash('item1', user_id='u1'))
        mock_delete.assert_called_once_with('item1', soft=True)

    @patch('services.trash_service.content_library_service.delete_item')
    def test_move_to_trash_failure(self, mock_delete):
        """소프트 삭제 실패"""
        mock_delete.return_value = False
        self.assertFalse(trash_service.move_to_trash('nonexistent'))

    def test_restore_from_trash(self):
        """휴지통 복구"""
        self._add_item('item1', is_deleted=True, deleted_at='2026-01-01T00:00:00Z')
        result = trash_service.restore_from_trash('item1')
        self.assertIsNotNone(result)
        self.assertFalse(result['is_deleted'])

    def test_restore_not_deleted(self):
        """삭제되지 않은 항목 복구 시 None"""
        self._add_item('item1', is_deleted=False)
        self.assertIsNone(trash_service.restore_from_trash('item1'))

    def test_restore_not_found(self):
        """없는 항목 복구 시 None"""
        self.assertIsNone(trash_service.restore_from_trash('nonexistent'))

    @patch('services.trash_service.content_library_service.delete_item')
    def test_permanently_delete(self, mock_delete):
        """영구 삭제"""
        mock_delete.return_value = True
        self.assertTrue(trash_service.permanently_delete('item1'))
        mock_delete.assert_called_once_with('item1', soft=False)

    def test_list_trash(self):
        """휴지통 목록"""
        self._add_item('a', is_deleted=True, deleted_at='2026-01-01')
        self._add_item('b', is_deleted=True, deleted_at='2026-01-02')
        self._add_item('c', is_deleted=False)
        result = trash_service.list_trash()
        self.assertEqual(result['total'], 2)

    def test_list_trash_pagination(self):
        """휴지통 페이지네이션"""
        for i in range(5):
            self._add_item(f'item{i}', is_deleted=True, deleted_at=f'2026-01-0{i+1}')
        result = trash_service.list_trash(per_page=2, page=1)
        self.assertEqual(len(result['items']), 2)
        self.assertEqual(result['total'], 5)


if __name__ == '__main__':
    unittest.main()
