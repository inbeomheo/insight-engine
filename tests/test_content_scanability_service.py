"""Content Scanability Score 서비스 테스트."""
import unittest
from services.analysis.content_scanability_service import score_content_scanability


class TestContentScanability(unittest.TestCase):

    def test_empty_content(self):
        result = score_content_scanability('')
        self.assertEqual(result['score'], 0.0)

    def test_none_content(self):
        result = score_content_scanability(None)
        self.assertEqual(result['score'], 0.0)

    def test_plain_text(self):
        content = ' '.join(['일반적인 텍스트'] * 50)
        result = score_content_scanability(content)
        self.assertEqual(result['summary']['level'], 'poor')

    def test_with_headings(self):
        body = ' '.join(['내용입니다'] * 30)
        content = f'# 제목\n{body}\n## 섹션1\n{body}\n## 섹션2\n{body}'
        result = score_content_scanability(content)
        self.assertGreater(result['elements']['headings'], 0)
        self.assertGreater(result['score'], 20.0)

    def test_with_lists(self):
        content = ('# 가이드\n내용입니다.\n\n'
                   '- 항목 1\n- 항목 2\n- 항목 3\n\n'
                   '추가 설명입니다.')
        result = score_content_scanability(content)
        self.assertGreater(result['elements']['list_items'], 0)

    def test_with_bold(self):
        content = '이것은 **중요한** 포인트입니다. **핵심** 내용을 강조합니다. 추가 설명이 여기에 포함됩니다. 더 많은 단어가 필요합니다.'
        result = score_content_scanability(content)
        self.assertGreater(result['elements']['bold_texts'], 0)

    def test_with_code_blocks(self):
        content = '코드 예시를 보여드리겠습니다. 아래 파이썬 코드를 확인하세요.\n```python\nprint("hello")\n```\n위 코드는 간단한 출력 예시입니다.'
        result = score_content_scanability(content)
        self.assertGreater(result['elements']['code_blocks'], 0)

    def test_with_images(self):
        content = '본문 내용이 여기에 있습니다. 다양한 시각적 요소를 포함합니다.\n![이미지](image.png)\n위 이미지는 주요 내용을 설명합니다.'
        result = score_content_scanability(content)
        self.assertGreater(result['elements']['images'], 0)

    def test_with_blockquote(self):
        content = '본문 내용이 여기에 작성되어 있습니다. 아래는 중요한 인용문입니다.\n\n> 인용문 내용이 여기에 포함됩니다.\n\n추가 설명과 내용이 이어집니다.'
        result = score_content_scanability(content)
        self.assertGreater(result['elements']['blockquotes'], 0)

    def test_excellent_scanability(self):
        body = ' '.join(['내용'] * 20)
        content = (f'# 메인 제목\n{body}\n\n'
                   f'## 섹션 1\n{body}\n\n'
                   f'- 항목 1\n- 항목 2\n- 항목 3\n\n'
                   f'**핵심 포인트**를 강조합니다.\n\n'
                   f'## 섹션 2\n{body}\n\n'
                   f'> 중요한 인용문입니다.\n\n'
                   f'![차트](chart.png)')
        result = score_content_scanability(content)
        self.assertIn(result['summary']['level'], ('excellent', 'good'))

    def test_score_range(self):
        content = '일반적인 콘텐츠입니다.'
        result = score_content_scanability(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_return_structure(self):
        content = '구조 확인입니다.'
        result = score_content_scanability(content)
        self.assertIn('elements', result)
        self.assertIn('summary', result)
        self.assertIn('score', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_elements', result['summary'])
        self.assertIn('scanability_score', result['summary'])
        self.assertIn('level', result['summary'])

    def test_suggestions_for_poor(self):
        content = ' '.join(['단순한 텍스트만 있습니다'] * 50)
        result = score_content_scanability(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_paragraph_count(self):
        content = '첫 번째 단락의 내용이 여기에 있습니다.\n\n두 번째 단락의 내용이 이어집니다.\n\n세 번째 단락의 내용도 포함됩니다.'
        result = score_content_scanability(content)
        self.assertGreater(result['elements']['total_paragraphs'], 0)


if __name__ == '__main__':
    unittest.main()
