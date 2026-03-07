"""data_migration_service 단위 테스트"""
import json
import unittest
from unittest.mock import patch, MagicMock

from services import data_migration_service


class TestExportJson(unittest.TestCase):

    @patch.object(data_migration_service, 'content_library_service')
    def test_basic(self, mock_cls):
        mock_cls.search_items.return_value = {
            'items': [{'id': '1', 'title': '제목', 'content': '본문'}]
        }
        result = data_migration_service.export_json()
        data = json.loads(result)
        self.assertEqual(data['count'], 1)
        self.assertIn('content', data['items'][0])

    @patch.object(data_migration_service, 'content_library_service')
    def test_exclude_content(self, mock_cls):
        mock_cls.search_items.return_value = {
            'items': [{'id': '1', 'title': '제목', 'content': '본문'}]
        }
        result = data_migration_service.export_json(include_content=False)
        data = json.loads(result)
        self.assertNotIn('content', data['items'][0])


class TestExportCsv(unittest.TestCase):

    @patch.object(data_migration_service, 'content_library_service')
    def test_basic(self, mock_cls):
        mock_cls.search_items.return_value = {
            'items': [{'id': '1', 'title': '제목', 'tags': ['a', 'b']}]
        }
        result = data_migration_service.export_csv()
        self.assertIn('title', result)
        self.assertIn('제목', result)


class TestExportMarkdown(unittest.TestCase):

    @patch.object(data_migration_service, 'content_library_service')
    def test_basic(self, mock_cls):
        mock_cls.search_items.return_value = {
            'items': [{'title': '제목', 'style': 'blog', 'status': 'draft',
                       'created_at': '2026-01-01', 'tags': ['t1'], 'content': '본문'}]
        }
        result = data_migration_service.export_markdown()
        self.assertIn('# 제목', result)
        self.assertIn('본문', result)


class TestImportJson(unittest.TestCase):

    @patch.object(data_migration_service, 'content_library_service')
    def test_success(self, mock_cls):
        mock_cls.create_item.return_value = {'id': 'new'}
        data = json.dumps({'items': [{'title': '제목', 'content': '본문'}]})
        result = data_migration_service.import_json(data)
        self.assertEqual(result['imported'], 1)

    def test_invalid_json(self):
        result = data_migration_service.import_json('not json{')
        self.assertEqual(result['imported'], 0)
        self.assertTrue(len(result['errors']) > 0)

    @patch.object(data_migration_service, 'content_library_service')
    def test_skip_no_title(self, mock_cls):
        data = json.dumps({'items': [{'title': '', 'content': '본문'}]})
        result = data_migration_service.import_json(data)
        self.assertEqual(result['skipped'], 1)

    @patch.object(data_migration_service, 'content_library_service')
    def test_skip_existing(self, mock_cls):
        mock_cls.get_item.return_value = {'id': 'x', 'title': '기존'}
        data = json.dumps({'items': [{'id': 'x', 'title': '제목'}]})
        result = data_migration_service.import_json(data, overwrite=False)
        self.assertEqual(result['skipped'], 1)


class TestImportCsv(unittest.TestCase):

    @patch.object(data_migration_service, 'content_library_service')
    def test_success(self, mock_cls):
        mock_cls.create_item.return_value = {'id': 'new'}
        csv_str = 'title,style,tags\n제목,blog,"a,b"\n'
        result = data_migration_service.import_csv(csv_str)
        self.assertEqual(result['imported'], 1)

    @patch.object(data_migration_service, 'content_library_service')
    def test_skip_empty_title(self, mock_cls):
        csv_str = 'title,style\n,blog\n'
        result = data_migration_service.import_csv(csv_str)
        self.assertEqual(result['skipped'], 1)


if __name__ == '__main__':
    unittest.main()
