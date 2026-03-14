"""Article Format Template Checker 서비스 테스트."""
import unittest
from services.content.article_format_template_service import check_article_format


class TestArticleFormatTemplate(unittest.TestCase):

    def test_empty_content(self):
        result = check_article_format('')
        self.assertEqual(result['score'], 0.0)

    def test_none_content(self):
        result = check_article_format(None)
        self.assertEqual(result['score'], 0.0)

    def test_listicle_format(self):
        content = """# 5가지 효과적인 방법
1. 첫 번째 방법
2. 두 번째 방법
3. 세 번째 방법
4. 네 번째 방법
5. 다섯 번째 방법"""
        result = check_article_format(content)
        formats = [d['format'] for d in result['detected_formats']]
        self.assertIn('listicle', formats)

    def test_howto_format(self):
        content = """# 가이드: 따라하기
## Step 1: 준비하기
방법을 설명합니다. 튜토리얼 단계입니다.
## Step 2: 실행하기
다음 단계를 진행합니다."""
        result = check_article_format(content)
        formats = [d['format'] for d in result['detected_formats']]
        self.assertIn('how_to', formats)

    def test_comparison_format(self):
        content = """# A vs B 비교
## 장단점 분석
비교 결과입니다. A와 B의 차이점을 분석합니다. Pros and Cons를 정리합니다."""
        result = check_article_format(content)
        formats = [d['format'] for d in result['detected_formats']]
        self.assertIn('comparison', formats)

    def test_qna_format(self):
        content = """# 자주 묻는 질문 FAQ
Q1: 이것은 무엇인가요?
A1: 설명입니다.
Q2: 어떻게 사용하나요?
A2: 가이드입니다."""
        result = check_article_format(content)
        formats = [d['format'] for d in result['detected_formats']]
        self.assertIn('qna', formats)

    def test_unstructured_content(self):
        content = '구조 없는 평문입니다. 헤딩도 없고 특별한 형식도 없습니다.'
        result = check_article_format(content)
        self.assertEqual(result['summary']['primary_format'], 'unstructured')

    def test_structure_elements(self):
        content = """# 소개
도입부입니다.

## 본론
내용입니다.

## 결론
마무리입니다."""
        result = check_article_format(content)
        self.assertTrue(result['structure_elements']['has_intro'])
        self.assertTrue(result['structure_elements']['has_conclusion'])

    def test_no_intro(self):
        content = """## 섹션 1
내용입니다.

## 섹션 2
내용입니다."""
        result = check_article_format(content)
        self.assertFalse(result['summary']['has_intro'])

    def test_heading_count(self):
        content = """# 제목
## 섹션 1
## 섹션 2
### 하위"""
        result = check_article_format(content)
        self.assertEqual(result['structure_elements']['heading_count'], 4)

    def test_score_range(self):
        content = '테스트 콘텐츠입니다.'
        result = check_article_format(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_suggestions_exist(self):
        content = '간단한 글입니다.'
        result = check_article_format(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_return_structure(self):
        content = '테스트입니다.'
        result = check_article_format(content)
        self.assertIn('detected_formats', result)
        self.assertIn('structure_elements', result)
        self.assertIn('summary', result)
        self.assertIn('score', result)
        self.assertIn('suggestions', result)
        self.assertIn('primary_format', result['summary'])
        self.assertIn('has_intro', result['summary'])
        self.assertIn('has_conclusion', result['summary'])


if __name__ == '__main__':
    unittest.main()
