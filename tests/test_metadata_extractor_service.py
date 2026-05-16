"""metadata_extractor_service 단위 테스트"""
import unittest

from services.content.metadata_extractor_service import (
    extract_metadata,
    _extract_title,
    _detect_language,
    _infer_category,
    _infer_content_type,
    _extract_tags,
)


class TestExtractMetadata(unittest.TestCase):

    def test_empty(self):
        result = extract_metadata('')
        self.assertEqual(result['word_count'], 0)
        self.assertEqual(result['language'], 'unknown')

    def test_none(self):
        result = extract_metadata(None)
        self.assertEqual(result['title'], '')

    def test_korean_content(self):
        text = '# 인공지능 입문 가이드\n\n인공지능 기술에 대한 기초를 배워봅시다.'
        result = extract_metadata(text)
        self.assertEqual(result['language'], 'ko')
        self.assertIn('인공지능', result['title'])
        self.assertGreater(result['word_count'], 0)

    def test_english_content(self):
        text = '# Introduction to Machine Learning\n\nMachine learning is a subset of artificial intelligence that focuses on algorithms.'
        result = extract_metadata(text)
        self.assertEqual(result['language'], 'en')

    def test_category_technology(self):
        text = '인공지능과 머신러닝 프로그래밍 개발 튜토리얼입니다.'
        result = extract_metadata(text)
        self.assertEqual(result['category'], 'technology')

    def test_content_type_tutorial(self):
        text = '# 파이썬 시작하는 방법\n\n따라하기 쉬운 단계별 가이드입니다.'
        result = extract_metadata(text)
        self.assertIn(result['content_type'], ['tutorial', 'guide'])

    def test_dates_extracted(self):
        text = '이 글은 2024-03-15에 작성되었습니다. 업데이트: 2024.06.01'
        result = extract_metadata(text)
        self.assertGreater(len(result['dates']), 0)
        self.assertIn('2024-03-15', result['dates'])

    def test_tags_extracted(self):
        text = '파이썬 프로그래밍과 데이터 분석을 배워봅시다. 파이썬은 강력합니다.'
        result = extract_metadata(text)
        self.assertGreater(len(result['tags']), 0)

    def test_has_code(self):
        text = '코드 예시:\n```python\nprint("hi")\n```'
        result = extract_metadata(text)
        self.assertTrue(result['has_code'])

    def test_has_images(self):
        text = '![이미지](img.png)\n텍스트입니다.'
        result = extract_metadata(text)
        self.assertTrue(result['has_images'])

    def test_has_lists(self):
        text = '- 항목1\n- 항목2\n- 항목3'
        result = extract_metadata(text)
        self.assertTrue(result['has_lists'])

    def test_reading_level(self):
        simple = '짧은 문장. 간단한 글. 쉬운 내용.'
        result = extract_metadata(simple)
        self.assertIn(result['estimated_reading_level'], ['beginner', 'intermediate', 'advanced'])


class TestExtractTitle(unittest.TestCase):

    def test_h1_title(self):
        self.assertEqual(_extract_title('# 메인 제목\n내용'), '메인 제목')

    def test_h2_fallback(self):
        self.assertEqual(_extract_title('## 서브 제목\n내용'), '서브 제목')

    def test_no_heading(self):
        self.assertEqual(_extract_title('일반 텍스트'), '')


class TestDetectLanguage(unittest.TestCase):

    def test_korean(self):
        self.assertEqual(_detect_language('한국어 텍스트입니다'), 'ko')

    def test_english(self):
        self.assertEqual(_detect_language('This is English text only'), 'en')

    def test_empty(self):
        self.assertEqual(_detect_language(''), 'unknown')


class TestInferCategory(unittest.TestCase):

    def test_technology(self):
        self.assertEqual(_infer_category('인공지능 머신러닝 개발'), 'technology')

    def test_business(self):
        self.assertEqual(_infer_category('마케팅 전략 수익 성장'), 'business')

    def test_general(self):
        self.assertEqual(_infer_category('아무런 키워드가 없는 글'), 'general')


class TestInferContentType(unittest.TestCase):

    def test_tutorial(self):
        self.assertEqual(_infer_content_type('파이썬 시작하는 방법 따라하기'), 'tutorial')

    def test_review(self):
        self.assertEqual(_infer_content_type('제품 리뷰 비교 장단점'), 'review')

    def test_default(self):
        self.assertEqual(_infer_content_type('일반적인 글입니다'), 'article')


class TestExtractTags(unittest.TestCase):

    def test_basic(self):
        tags = _extract_tags('파이썬 머신러닝 데이터 분석 파이썬 파이썬')
        self.assertGreater(len(tags), 0)
        self.assertEqual(tags[0], '파이썬')  # 가장 빈도 높음

    def test_max_tags(self):
        text = ' '.join([f'태그{i}' for i in range(20)])
        tags = _extract_tags(text, max_tags=3)
        self.assertLessEqual(len(tags), 3)


if __name__ == '__main__':
    unittest.main()
