"""glossary_extractor_service 단위 테스트"""
import unittest

from services.content.glossary_extractor_service import (
    extract_glossary,
    _clean_definition,
)


class TestExtractGlossary(unittest.TestCase):

    def test_empty_content(self):
        result = extract_glossary('')
        self.assertEqual(result['total'], 0)

    def test_none_content(self):
        result = extract_glossary(None)
        self.assertEqual(result['total'], 0)

    def test_definition_pattern_ran(self):
        text = '머신러닝이란 데이터에서 패턴을 학습하는 인공지능의 한 분야입니다.'
        result = extract_glossary(text)
        self.assertGreater(result['total'], 0)
        terms = [t['term'] for t in result['terms']]
        self.assertTrue(any('머신러닝' in t for t in terms))

    def test_parenthesis_pattern_korean(self):
        text = '인공지능(Artificial Intelligence)은 컴퓨터 과학의 한 분야입니다.'
        result = extract_glossary(text)
        # 괄호 패턴 매칭
        all_items = result['terms'] + [{'term': a['acronym']} for a in result['acronyms']]
        self.assertGreater(len(all_items), 0)

    def test_parenthesis_pattern_english(self):
        text = 'NLP(자연어 처리) 기술이 발전하고 있습니다.'
        result = extract_glossary(text)
        terms = [t['term'] for t in result['terms']]
        self.assertTrue(any('NLP' in t for t in terms))

    def test_bold_definition(self):
        text = '**트랜스포머** — 어텐션 메커니즘을 기반으로 한 딥러닝 아키텍처입니다.'
        result = extract_glossary(text)
        terms = [t['term'] for t in result['terms']]
        self.assertTrue(any('트랜스포머' in t for t in terms))

    def test_list_colon_pattern(self):
        text = '- **컨볼루션**: 이미지에서 특징을 추출하는 연산 과정입니다.\n- **풀링**: 특징 맵의 크기를 줄이는 연산입니다.'
        result = extract_glossary(text)
        self.assertGreaterEqual(len(result['terms']), 1)

    def test_acronym_extraction(self):
        text = 'GPU(Graphics Processing Unit)와 TPU(Tensor Processing Unit)를 사용합니다.'
        result = extract_glossary(text)
        acronyms = [a['acronym'] for a in result['acronyms']]
        self.assertIn('GPU', acronyms)
        self.assertIn('TPU', acronyms)

    def test_no_duplicates(self):
        text = '머신러닝이란 데이터에서 패턴을 학습하는 기술입니다. 머신러닝이란 매우 중요한 분야입니다.'
        result = extract_glossary(text)
        terms = [t['term'] for t in result['terms']]
        # 중복 제거 확인
        term_lower = [t.lower() for t in terms]
        self.assertEqual(len(term_lower), len(set(term_lower)))

    def test_mixed_content(self):
        text = """# AI 용어집

**딥러닝** — 여러 층의 신경망을 사용하여 복잡한 패턴을 학습하는 기술입니다.

GPU(Graphics Processing Unit)는 병렬 처리에 최적화된 프로세서입니다.

강화학습이란 에이전트가 환경과 상호작용하며 보상을 최대화하는 방법을 학습하는 것입니다."""
        result = extract_glossary(text)
        self.assertGreater(result['total'], 1)

    def test_total_count(self):
        text = 'AI(Artificial Intelligence)와 ML(Machine Learning)이 중요합니다.'
        result = extract_glossary(text)
        self.assertEqual(result['total'], len(result['terms']) + len(result['acronyms']))


class TestCleanDefinition(unittest.TestCase):

    def test_strip(self):
        self.assertEqual(_clean_definition('  정의  '), '정의')

    def test_remove_trailing_asterisks(self):
        self.assertEqual(_clean_definition('정의**'), '정의')

    def test_fix_unclosed_paren(self):
        result = _clean_definition('정의(추가 설명')
        self.assertTrue(result.endswith(')'))

    def test_normal_text(self):
        self.assertEqual(_clean_definition('정상 텍스트'), '정상 텍스트')


if __name__ == '__main__':
    unittest.main()
