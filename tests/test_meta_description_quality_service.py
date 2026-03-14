"""Meta Description Quality Checker 서비스 테스트."""
import unittest
from services.seo.meta_description_quality_service import check_meta_description_quality


class TestMetaDescriptionQuality(unittest.TestCase):

    def test_empty_content(self):
        result = check_meta_description_quality('')
        self.assertEqual(result['score'], 0.0)
        self.assertEqual(result['summary']['quality_level'], 'none')

    def test_none_content(self):
        result = check_meta_description_quality(None)
        self.assertEqual(result['score'], 0.0)

    def test_html_meta_description(self):
        content = '<meta name="description" content="이 가이드에서 10가지 방법을 알아보세요. 초보자도 쉽게 따라할 수 있는 완벽한 튜토리얼입니다. 지금 시작하세요.">'
        result = check_meta_description_quality(content)
        self.assertNotEqual(result['description'], '')
        self.assertTrue(result['checks']['has_cta'])

    def test_frontmatter_description(self):
        content = """---
title: 테스트 글
description: "5가지 핵심 전략을 알아보세요. 성공을 위한 실전 가이드입니다."
---

본문 내용입니다."""
        result = check_meta_description_quality(content)
        self.assertNotEqual(result['description'], '')

    def test_first_paragraph_fallback(self):
        content = """# 제목

이것은 첫 번째 문단으로 메타 디스크립션 대체 역할을 합니다."""
        result = check_meta_description_quality(content)
        self.assertNotEqual(result['description'], '')

    def test_optimal_length(self):
        desc = 'A' * 130  # 120-160 사이
        content = f'<meta name="description" content="{desc}">'
        result = check_meta_description_quality(content)
        self.assertTrue(result['checks']['optimal_length'])

    def test_short_length(self):
        content = '<meta name="description" content="짧은 설명입니다.">'
        result = check_meta_description_quality(content)
        self.assertFalse(result['checks']['optimal_length'])

    def test_cta_detection(self):
        content = '새로운 방법을 알아보세요. 지금 시작하면 더 좋은 결과를 얻을 수 있습니다.'
        result = check_meta_description_quality(content)
        self.assertTrue(result['checks']['has_cta'])

    def test_specificity_numbers(self):
        content = '이 가이드에서 10가지 핵심 전략을 배울 수 있습니다. 실전에서 검증된 방법론입니다.'
        result = check_meta_description_quality(content)
        self.assertTrue(result['checks']['has_specificity'])

    def test_proper_ending(self):
        content = '이것은 중요한 내용을 다루는 글입니다.'
        result = check_meta_description_quality(content)
        self.assertTrue(result['checks']['ends_properly'])

    def test_no_repetition(self):
        content = '다양한 주제를 다루는 포괄적인 가이드입니다. 여러 관점에서 분석합니다.'
        result = check_meta_description_quality(content)
        self.assertTrue(result['checks']['no_repetition'])

    def test_score_range(self):
        content = '테스트용 메타 디스크립션 콘텐츠입니다.'
        result = check_meta_description_quality(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_suggestions_exist(self):
        content = '간단한 글입니다. 더 많은 내용이 필요합니다.'
        result = check_meta_description_quality(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_return_structure(self):
        content = '테스트 콘텐츠입니다.'
        result = check_meta_description_quality(content)
        self.assertIn('description', result)
        self.assertIn('checks', result)
        self.assertIn('summary', result)
        self.assertIn('score', result)
        self.assertIn('suggestions', result)
        self.assertIn('length', result['summary'])
        self.assertIn('quality_level', result['summary'])


if __name__ == '__main__':
    unittest.main()
