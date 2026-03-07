"""gdocs_export_service 단위 테스트 (마크다운 변환 위주)"""
import unittest

from services.gdocs_export_service import _markdown_to_docs_requests, DOCS_API_URL


class TestMarkdownToDocsRequests(unittest.TestCase):

    def test_plain_text(self):
        """일반 텍스트 → insertText"""
        reqs = _markdown_to_docs_requests('안녕하세요')
        self.assertGreater(len(reqs), 0)
        self.assertIn('insertText', reqs[0])
        self.assertIn('안녕하세요', reqs[0]['insertText']['text'])

    def test_heading_1(self):
        """# 헤딩 → HEADING_1 스타일"""
        reqs = _markdown_to_docs_requests('# 제목')
        insert_reqs = [r for r in reqs if 'insertText' in r]
        style_reqs = [r for r in reqs if 'updateParagraphStyle' in r]
        self.assertGreater(len(insert_reqs), 0)
        self.assertEqual(len(style_reqs), 1)
        self.assertEqual(
            style_reqs[0]['updateParagraphStyle']['paragraphStyle']['namedStyleType'],
            'HEADING_1'
        )

    def test_heading_2(self):
        """## 헤딩 → HEADING_2 스타일"""
        reqs = _markdown_to_docs_requests('## 소제목')
        style_reqs = [r for r in reqs if 'updateParagraphStyle' in r]
        self.assertEqual(
            style_reqs[0]['updateParagraphStyle']['paragraphStyle']['namedStyleType'],
            'HEADING_2'
        )

    def test_heading_3(self):
        """### 헤딩 → HEADING_3 스타일"""
        reqs = _markdown_to_docs_requests('### 하위 제목')
        style_reqs = [r for r in reqs if 'updateParagraphStyle' in r]
        self.assertEqual(
            style_reqs[0]['updateParagraphStyle']['paragraphStyle']['namedStyleType'],
            'HEADING_3'
        )

    def test_bullet_list(self):
        """- 항목 → 불릿 기호"""
        reqs = _markdown_to_docs_requests('- 항목1')
        insert_reqs = [r for r in reqs if 'insertText' in r]
        self.assertIn('•', insert_reqs[0]['insertText']['text'])

    def test_code_block_skipped(self):
        """코드 블록 구분자 건너뜀"""
        md = '```python\nprint("hi")\n```'
        reqs = _markdown_to_docs_requests(md)
        insert_texts = [r['insertText']['text'] for r in reqs if 'insertText' in r]
        # 코드 내용은 포함, ``` 구분자는 건너뜀
        full = ''.join(insert_texts)
        self.assertIn('print("hi")', full)

    def test_bold_stripped(self):
        """**볼드** 인라인 서식 제거"""
        reqs = _markdown_to_docs_requests('**굵은 글씨**입니다')
        text = reqs[0]['insertText']['text']
        self.assertNotIn('**', text)
        self.assertIn('굵은 글씨', text)

    def test_index_starts_at_1(self):
        """인덱스 1부터 시작"""
        reqs = _markdown_to_docs_requests('텍스트')
        self.assertEqual(reqs[0]['insertText']['location']['index'], 1)

    def test_empty_input(self):
        """빈 입력 → 줄바꿈만 포함"""
        reqs = _markdown_to_docs_requests('')
        # 빈 입력이어도 trailing newline 하나 삽입
        self.assertEqual(len(reqs), 1)
        self.assertEqual(reqs[0]['insertText']['text'], '\n')

    def test_api_url_constant(self):
        """API URL 상수"""
        self.assertIn('docs.googleapis.com', DOCS_API_URL)


if __name__ == '__main__':
    unittest.main()
