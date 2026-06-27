"""Notion 서비스 단위 테스트"""
import unittest
from unittest.mock import patch, MagicMock

from services.export.notion_service import (
    extract_notion_page,
    _extract_page_id,
    _block_to_markdown,
    _rich_text_to_str,
)


class TestExtractPageId(unittest.TestCase):
    """Notion URL에서 page_id 추출 테스트"""

    def test_standard_url(self):
        url = 'https://www.notion.so/workspace/My-Page-abcdef1234567890abcdef1234567890'
        result = _extract_page_id(url)
        self.assertEqual(result, 'abcdef12-3456-7890-abcd-ef1234567890')

    def test_uuid_format_url(self):
        url = 'https://notion.so/page-abcdef12-3456-7890-abcd-ef1234567890'
        result = _extract_page_id(url)
        self.assertEqual(result, 'abcdef12-3456-7890-abcd-ef1234567890')

    def test_invalid_url(self):
        with self.assertRaises(ValueError):
            _extract_page_id('https://google.com/not-notion')


class TestBlockToMarkdown(unittest.TestCase):
    """Notion 블록 → 마크다운 변환 테스트"""

    def _make_block(self, btype, text, **extra):
        return {
            'type': btype,
            btype: {
                'rich_text': [{'plain_text': text}],
                **extra,
            },
        }

    def test_paragraph(self):
        block = self._make_block('paragraph', '본문 텍스트')
        self.assertEqual(_block_to_markdown(block), '본문 텍스트')

    def test_heading_1(self):
        block = self._make_block('heading_1', '제목1')
        self.assertEqual(_block_to_markdown(block), '# 제목1')

    def test_heading_2(self):
        block = self._make_block('heading_2', '제목2')
        self.assertEqual(_block_to_markdown(block), '## 제목2')

    def test_heading_3(self):
        block = self._make_block('heading_3', '제목3')
        self.assertEqual(_block_to_markdown(block), '### 제목3')

    def test_bulleted_list(self):
        block = self._make_block('bulleted_list_item', '항목')
        self.assertEqual(_block_to_markdown(block), '- 항목')

    def test_numbered_list(self):
        block = self._make_block('numbered_list_item', '항목')
        self.assertEqual(_block_to_markdown(block), '1. 항목')

    def test_code_block(self):
        block = self._make_block('code', 'print("hello")', language='python')
        self.assertEqual(_block_to_markdown(block), '```python\nprint("hello")\n```')

    def test_quote(self):
        block = self._make_block('quote', '인용문')
        self.assertEqual(_block_to_markdown(block), '> 인용문')

    def test_to_do_checked(self):
        block = self._make_block('to_do', '완료 항목', checked=True)
        self.assertEqual(_block_to_markdown(block), '☑ 완료 항목')

    def test_to_do_unchecked(self):
        block = self._make_block('to_do', '미완료 항목', checked=False)
        self.assertEqual(_block_to_markdown(block), '☐ 미완료 항목')

    def test_divider(self):
        block = {'type': 'divider', 'divider': {}}
        self.assertEqual(_block_to_markdown(block), '---')

    def test_unsupported_block(self):
        block = {'type': 'image', 'image': {}}
        self.assertIsNone(_block_to_markdown(block))


class TestRichTextToStr(unittest.TestCase):
    def test_multiple_parts(self):
        parts = [{'plain_text': 'Hello '}, {'plain_text': 'World'}]
        self.assertEqual(_rich_text_to_str(parts), 'Hello World')

    def test_empty(self):
        self.assertEqual(_rich_text_to_str([]), '')


class TestExtractNotionPage(unittest.TestCase):
    """Notion 페이지 추출 통합 테스트 (API 모킹)"""

    @patch('services.export.notion_service.requests.get')
    def test_successful_extraction(self, mock_get):
        # 페이지 메타데이터 응답
        page_resp = MagicMock()
        page_resp.status_code = 200
        page_resp.json.return_value = {
            'properties': {
                'title': {
                    'type': 'title',
                    'title': [{'plain_text': '테스트 페이지'}],
                },
            },
        }

        # 블록 조회 응답
        blocks_resp = MagicMock()
        blocks_resp.status_code = 200
        blocks_resp.json.return_value = {
            'results': [
                {
                    'type': 'paragraph',
                    'paragraph': {
                        'rich_text': [{'plain_text': '첫 번째 문단입니다.'}],
                    },
                },
                {
                    'type': 'heading_2',
                    'heading_2': {
                        'rich_text': [{'plain_text': '소제목'}],
                    },
                },
            ],
            'has_more': False,
        }

        mock_get.side_effect = [page_resp, blocks_resp]

        result = extract_notion_page(
            'https://notion.so/test/Page-abcdef1234567890abcdef1234567890',
            'ntn_test_api_key',
        )

        self.assertEqual(result['title'], '테스트 페이지')
        self.assertIn('첫 번째 문단', result['content'])
        self.assertIn('## 소제목', result['content'])
        self.assertEqual(result['source_type'], 'notion')
        self.assertFalse(mock_get.call_args_list[0].kwargs['allow_redirects'])
        self.assertFalse(mock_get.call_args_list[1].kwargs['allow_redirects'])

    def test_missing_api_key(self):
        with self.assertRaises(ValueError) as ctx:
            extract_notion_page('https://notion.so/test/Page-abcdef1234567890abcdef1234567890', '')
        self.assertIn('API 키', str(ctx.exception))

    @patch('services.export.notion_service.requests.get')
    def test_api_error(self, mock_get):
        resp = MagicMock()
        resp.status_code = 401
        resp.text = 'Unauthorized'
        mock_get.return_value = resp

        with self.assertRaises(ValueError) as ctx:
            extract_notion_page(
                'https://notion.so/test/Page-abcdef1234567890abcdef1234567890',
                'bad_key',
            )
        self.assertIn('401', str(ctx.exception))

    @patch('services.export.notion_service.requests.get')
    def test_page_redirect_blocked(self, mock_get):
        mock_get.return_value = MagicMock(status_code=302)

        with self.assertRaises(ValueError) as ctx:
            extract_notion_page(
                'https://notion.so/test/Page-abcdef1234567890abcdef1234567890',
                'ntn_test_api_key',
            )

        self.assertIn('리다이렉트 차단', str(ctx.exception))
        self.assertFalse(mock_get.call_args.kwargs['allow_redirects'])


if __name__ == '__main__':
    unittest.main()
