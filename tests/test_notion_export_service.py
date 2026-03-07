"""notion_export_service 단위 테스트 (마크다운→Notion 변환)"""
import unittest

from services.notion_export_service import (
    _markdown_to_notion_blocks,
    _heading_block,
    _rich_text,
    export_to_notion,
    NOTION_API_URL,
    NOTION_VERSION,
)


class TestRichText(unittest.TestCase):

    def test_plain_text(self):
        """일반 텍스트 → 단일 세그먼트"""
        result = _rich_text('안녕하세요')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['text']['content'], '안녕하세요')

    def test_bold(self):
        """**볼드** → bold annotation"""
        result = _rich_text('**굵은 글씨**')
        bold_segs = [s for s in result if s.get('annotations', {}).get('bold')]
        self.assertEqual(len(bold_segs), 1)
        self.assertEqual(bold_segs[0]['text']['content'], '굵은 글씨')

    def test_italic(self):
        """*이탤릭* → italic annotation"""
        result = _rich_text('*기울임*')
        italic_segs = [s for s in result if s.get('annotations', {}).get('italic')]
        self.assertEqual(len(italic_segs), 1)
        self.assertEqual(italic_segs[0]['text']['content'], '기울임')

    def test_inline_code(self):
        """`코드` → code annotation"""
        result = _rich_text('`변수명`')
        code_segs = [s for s in result if s.get('annotations', {}).get('code')]
        self.assertEqual(len(code_segs), 1)
        self.assertEqual(code_segs[0]['text']['content'], '변수명')

    def test_mixed(self):
        """혼합 서식"""
        result = _rich_text('일반 **굵은** 텍스트')
        self.assertGreater(len(result), 1)


class TestHeadingBlock(unittest.TestCase):

    def test_heading_1(self):
        """heading_1 블록"""
        block = _heading_block('제목', 1)
        self.assertEqual(block['type'], 'heading_1')
        self.assertIn('heading_1', block)

    def test_heading_2(self):
        """heading_2 블록"""
        block = _heading_block('소제목', 2)
        self.assertEqual(block['type'], 'heading_2')

    def test_heading_3(self):
        """heading_3 블록"""
        block = _heading_block('하위', 3)
        self.assertEqual(block['type'], 'heading_3')


class TestMarkdownToNotionBlocks(unittest.TestCase):

    def test_paragraph(self):
        """일반 텍스트 → paragraph 블록"""
        blocks = _markdown_to_notion_blocks('일반 텍스트입니다.')
        self.assertEqual(blocks[0]['type'], 'paragraph')

    def test_heading(self):
        """# 헤딩 → heading_1"""
        blocks = _markdown_to_notion_blocks('# 큰 제목')
        self.assertEqual(blocks[0]['type'], 'heading_1')

    def test_bullet_list(self):
        """- 항목 → bulleted_list_item"""
        blocks = _markdown_to_notion_blocks('- 리스트 항목')
        self.assertEqual(blocks[0]['type'], 'bulleted_list_item')

    def test_numbered_list(self):
        """1. 항목 → numbered_list_item"""
        blocks = _markdown_to_notion_blocks('1. 순서 항목')
        self.assertEqual(blocks[0]['type'], 'numbered_list_item')

    def test_quote(self):
        """> 인용 → quote"""
        blocks = _markdown_to_notion_blocks('> 인용문입니다')
        self.assertEqual(blocks[0]['type'], 'quote')

    def test_code_block(self):
        """코드 블록 → code"""
        md = '```python\nprint("hi")\n```'
        blocks = _markdown_to_notion_blocks(md)
        self.assertEqual(blocks[0]['type'], 'code')
        self.assertEqual(blocks[0]['code']['language'], 'python')

    def test_empty_lines_skipped(self):
        """빈 줄 건너뜀"""
        blocks = _markdown_to_notion_blocks('\n\n텍스트\n\n')
        self.assertEqual(len(blocks), 1)

    def test_empty_input(self):
        """빈 입력 → 빈 리스트"""
        self.assertEqual(_markdown_to_notion_blocks(''), [])


class TestExportToNotion(unittest.TestCase):

    def test_no_parent_page_id(self):
        """부모 페이지 ID 없음 → 실패"""
        result = export_to_notion('제목', '내용', 'api-key', parent_page_id='')
        self.assertFalse(result['success'])
        self.assertIn('부모 페이지', result['message'])

    def test_constants(self):
        """상수 확인"""
        self.assertIn('notion.com', NOTION_API_URL)
        self.assertEqual(NOTION_VERSION, '2022-06-28')


if __name__ == '__main__':
    unittest.main()
