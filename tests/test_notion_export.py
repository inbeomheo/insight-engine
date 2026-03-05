"""Notion 내보내기 서비스 단위 테스트"""
import unittest
from unittest.mock import patch, MagicMock

from services.notion_export_service import export_to_notion, _markdown_to_notion_blocks


class TestNotionExport(unittest.TestCase):
    """Notion 내보내기 테스트"""

    def test_missing_parent_page_id(self):
        """부모 페이지 ID 없으면 실패"""
        result = export_to_notion('제목', '내용', 'fake-key')
        self.assertFalse(result['success'])
        self.assertIn('부모 페이지', result['message'])

    @patch('services.notion_export_service.requests.post')
    def test_successful_export(self, mock_post):
        """성공적인 Notion 페이지 생성"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {'url': 'https://notion.so/page-123'}
        mock_post.return_value = mock_resp

        result = export_to_notion('제목', '내용', 'fake-key', parent_page_id='page-id')
        self.assertTrue(result['success'])
        self.assertEqual(result['url'], 'https://notion.so/page-123')

    @patch('services.notion_export_service.requests.post')
    def test_api_error(self, mock_post):
        """API 오류 시 실패 반환"""
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.json.return_value = {'message': 'Invalid request'}
        mock_post.return_value = mock_resp

        result = export_to_notion('제목', '내용', 'fake-key', parent_page_id='page-id')
        self.assertFalse(result['success'])

    @patch('services.notion_export_service.requests.post')
    def test_connection_error(self, mock_post):
        """연결 오류 시 실패 반환"""
        import requests
        mock_post.side_effect = requests.RequestException('Connection refused')

        result = export_to_notion('제목', '내용', 'fake-key', parent_page_id='page-id')
        self.assertFalse(result['success'])
        self.assertIn('연결 실패', result['message'])

    def test_markdown_to_blocks_heading(self):
        """헤딩 변환"""
        blocks = _markdown_to_notion_blocks('# 제목\n## 소제목')
        self.assertEqual(blocks[0]['type'], 'heading_1')
        self.assertEqual(blocks[1]['type'], 'heading_2')

    def test_markdown_to_blocks_list(self):
        """목록 변환"""
        blocks = _markdown_to_notion_blocks('- 항목1\n1. 항목2')
        self.assertEqual(blocks[0]['type'], 'bulleted_list_item')
        self.assertEqual(blocks[1]['type'], 'numbered_list_item')

    def test_markdown_to_blocks_code(self):
        """코드 블록 변환"""
        blocks = _markdown_to_notion_blocks('```python\nprint("hi")\n```')
        self.assertEqual(blocks[0]['type'], 'code')
        self.assertEqual(blocks[0]['code']['language'], 'python')

    def test_markdown_to_blocks_quote(self):
        """인용문 변환"""
        blocks = _markdown_to_notion_blocks('> 인용 텍스트')
        self.assertEqual(blocks[0]['type'], 'quote')

    def test_markdown_to_blocks_paragraph(self):
        """일반 텍스트는 paragraph"""
        blocks = _markdown_to_notion_blocks('일반 텍스트')
        self.assertEqual(blocks[0]['type'], 'paragraph')

    def test_rich_text_bold(self):
        """볼드 인라인 서식"""
        blocks = _markdown_to_notion_blocks('**볼드** 텍스트')
        rich = blocks[0]['paragraph']['rich_text']
        bold_segments = [s for s in rich if s.get('annotations', {}).get('bold')]
        self.assertTrue(len(bold_segments) > 0)


if __name__ == '__main__':
    unittest.main()
