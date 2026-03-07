"""faq_generator_service 단위 테스트"""
import unittest
import json

from services.faq_generator_service import (
    generate_faq,
    _extract_topics,
)


class TestGenerateFaq(unittest.TestCase):

    def test_empty_content(self):
        result = generate_faq('')
        self.assertEqual(result['faqs'], [])

    def test_none_content(self):
        result = generate_faq(None)
        self.assertEqual(result['topics'], [])

    def test_basic_faq_generation(self):
        content = """파이썬은 프로그래밍 언어입니다. 파이썬은 간결한 문법을 제공합니다.
        파이썬은 데이터 과학에 널리 사용됩니다. 파이썬을 배우려면 기초부터 시작하세요.
        파이썬의 장점은 다양한 라이브러리입니다. 파이썬은 초보자에게 적합합니다."""
        result = generate_faq(content)
        self.assertGreater(len(result['faqs']), 0)
        self.assertGreater(len(result['topics']), 0)

    def test_faq_structure(self):
        content = '머신러닝은 AI의 한 분야입니다. 머신러닝은 데이터에서 패턴을 학습합니다. 머신러닝의 방법론은 다양합니다.'
        result = generate_faq(content)
        if result['faqs']:
            faq = result['faqs'][0]
            self.assertIn('question', faq)
            self.assertIn('answer', faq)
            self.assertIn('type', faq)
            self.assertIn('topic', faq)

    def test_max_questions_limit(self):
        content = '파이썬은 좋습니다. 파이썬은 쉽습니다. ' * 20
        result = generate_faq(content, max_questions=3)
        self.assertLessEqual(len(result['faqs']), 3)

    def test_schema_json_valid(self):
        content = '파이썬은 프로그래밍 언어입니다. 파이썬은 인기가 높습니다. 파이썬을 배우세요.'
        result = generate_faq(content)
        if result['schema_json']:
            schema = json.loads(result['schema_json'])
            self.assertEqual(schema['@type'], 'FAQPage')
            self.assertIn('mainEntity', schema)

    def test_markdown_output(self):
        content = '자바스크립트는 웹 언어입니다. 자바스크립트는 프론트엔드 개발에 필수입니다. 자바스크립트를 배우세요.'
        result = generate_faq(content)
        self.assertIn('## 자주 묻는 질문', result['markdown'])

    def test_suggestions_exist(self):
        content = '테스트 콘텐츠입니다. 테스트를 진행합니다.'
        result = generate_faq(content)
        self.assertIsInstance(result['suggestions'], list)
        self.assertGreater(len(result['suggestions']), 0)

    def test_short_content(self):
        result = generate_faq('짧은 글.')
        # 주제를 추출할 수 없을 수 있음
        self.assertIsInstance(result['faqs'], list)


class TestExtractTopics(unittest.TestCase):

    def test_extracts_frequent_words(self):
        content = '파이썬 프로그래밍은 좋습니다. 파이썬을 배우세요. 프로그래밍은 재미있습니다.'
        topics = _extract_topics(content)
        self.assertIn('파이썬', topics)

    def test_excludes_stopwords(self):
        topics = _extract_topics('있습니다 합니다 됩니다 위해 통해')
        # 불용어만 있으면 빈 결과
        self.assertEqual(len(topics), 0)

    def test_returns_max_10(self):
        content = ' '.join(f'주제{i}는 좋습니다. 주제{i}를 배우세요.' for i in range(20))
        topics = _extract_topics(content)
        self.assertLessEqual(len(topics), 10)


if __name__ == '__main__':
    unittest.main()
