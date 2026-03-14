"""backup_service 단위 테스트"""
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from services.data import backup_service


class TestBackupService(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self._orig_dir = backup_service.BACKUP_DIR
        backup_service.BACKUP_DIR = Path(self.tmpdir)

    def tearDown(self):
        backup_service.BACKUP_DIR = self._orig_dir
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch('services.data.content_library_service.get_all_items_raw', return_value=[
        {'id': '1', 'title': '제목1', 'content': '내용1'},
        {'id': '2', 'title': '제목2', 'content': '내용2'},
    ])
    def test_create_backup(self, mock_items):
        """백업 생성"""
        result = backup_service.create_backup()
        self.assertEqual(result['item_count'], 2)
        self.assertGreater(result['size_bytes'], 0)
        self.assertIn('backup_id', result)

    @patch('services.data.content_library_service.get_all_items_raw', return_value=[])
    def test_create_backup_empty(self, mock_items):
        """빈 라이브러리 백업"""
        result = backup_service.create_backup()
        self.assertEqual(result['item_count'], 0)

    def test_list_backups_empty(self):
        """백업 없을 때 빈 목록"""
        result = backup_service.list_backups()
        self.assertEqual(len(result), 0)

    @patch('services.data.content_library_service.get_all_items_raw', return_value=[{'id': '1', 'title': 'T'}])
    def test_list_backups_after_create(self, mock_items):
        """백업 생성 후 목록 조회"""
        backup_service.create_backup()
        result = backup_service.list_backups()
        self.assertEqual(len(result), 1)

    @patch('services.data.content_library_service.get_item', return_value=None)
    @patch('services.data.content_library_service.create_item')
    def test_restore_backup(self, mock_create, mock_get):
        """백업 복원 (신규 생성)"""
        # 백업 파일 수동 생성
        payload = {
            'backup_id': 'test',
            'items': [{'id': '1', 'title': 'T', 'content': 'C', 'style': '', 'tags': [], 'url': '', 'user_id': '', 'workspace_id': '', 'folder_id': '', 'meta': {}}],
        }
        fname = 'backup_test.json'
        (Path(self.tmpdir) / fname).write_text(json.dumps(payload), encoding='utf-8')

        result = backup_service.restore_backup(fname)
        self.assertEqual(result['restored'], 1)
        mock_create.assert_called_once()

    def test_restore_nonexistent_raises(self):
        """없는 백업 파일 복원 → FileNotFoundError"""
        with self.assertRaises(FileNotFoundError):
            backup_service.restore_backup('nonexistent.json')

    def test_get_backup_info(self):
        """백업 메타데이터 조회"""
        payload = {
            'backup_id': 'info-test',
            'created_at': '2026-01-01T00:00:00Z',
            'workspace_id': 'ws1',
            'item_count': 5,
            'triggered_by': 'manual',
            'items': [],
        }
        fname = 'backup_info_test.json'
        (Path(self.tmpdir) / fname).write_text(json.dumps(payload), encoding='utf-8')

        info = backup_service.get_backup_info(fname)
        self.assertEqual(info['backup_id'], 'info-test')
        self.assertEqual(info['item_count'], 5)

    def test_get_backup_info_nonexistent(self):
        """없는 백업 메타데이터 → None"""
        self.assertIsNone(backup_service.get_backup_info('bad.json'))

    @patch('services.data.content_library_service.get_all_items_raw', return_value=[{'id': '1'}])
    def test_prune_old_backups(self, mock_items):
        """오래된 백업 자동 삭제"""
        orig_max = backup_service.MAX_BACKUPS
        backup_service.MAX_BACKUPS = 2
        try:
            for i in range(4):
                backup_service.create_backup()
            backups = backup_service.list_backups()
            self.assertLessEqual(len(backups), 2)
        finally:
            backup_service.MAX_BACKUPS = orig_max

    @patch('services.data.content_library_service.get_all_items_raw', return_value=[
        {'id': '1', 'workspace_id': 'ws1'},
        {'id': '2', 'workspace_id': 'ws2'},
    ])
    def test_create_backup_filtered_by_workspace(self, mock_items):
        """워크스페이스별 백업"""
        result = backup_service.create_backup(workspace_id='ws1')
        self.assertEqual(result['item_count'], 1)


if __name__ == '__main__':
    unittest.main()
