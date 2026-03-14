"""acronym_extractor_service 단위 테스트"""
import unittest

from services.analysis.acronym_extractor_service import (
    extract_acronyms,
)


class TestExtractAcronyms(unittest.TestCase):

    def test_empty_content(self):
        result = extract_acronyms('')
        self.assertEqual(result['acronyms'], [])
        self.assertEqual(result['summary']['total'], 0)

    def test_none_content(self):
        result = extract_acronyms(None)
        self.assertEqual(result['summary']['total'], 0)

    def test_known_acronym(self):
        result = extract_acronyms('AI와 ML은 현대 기술의 핵심입니다.')
        self.assertGreater(result['summary']['known'], 0)
        ai_found = [a for a in result['acronyms'] if a['term'] == 'AI']
        self.assertEqual(len(ai_found), 1)
        self.assertTrue(ai_found[0]['known'])

    def test_unknown_acronym(self):
        result = extract_acronyms('XYZQ 기술을 활용합니다. XYZQ는 새로운 프레임워크입니다.')
        unknown = [a for a in result['acronyms'] if not a['known']]
        self.assertGreater(len(unknown), 0)

    def test_multiple_acronyms(self):
        content = 'API를 통해 JSON 데이터를 전송합니다. SEO 최적화와 CTA를 고려하세요.'
        result = extract_acronyms(content)
        self.assertGreaterEqual(result['summary']['total'], 3)

    def test_glossary_markdown(self):
        result = extract_acronyms('AI와 ML 기술을 소개합니다.')
        self.assertIn('## 용어집', result['glossary_markdown'])

    def test_count_tracking(self):
        content = 'AI는 좋습니다. AI를 배우세요. AI가 미래입니다.'
        result = extract_acronyms(content)
        ai_item = [a for a in result['acronyms'] if a['term'] == 'AI']
        if ai_item:
            self.assertGreaterEqual(ai_item[0]['count'], 2)

    def test_no_acronyms(self):
        result = extract_acronyms('한국어로만 작성된 일반적인 문장입니다.')
        self.assertEqual(result['summary']['total'], 0)

    def test_suggestions_for_unknown(self):
        result = extract_acronyms('XYZQ 프레임워크를 활용합니다. XYZQ는 효과적입니다.')
        if result['summary']['unknown'] > 0:
            suggestions_text = ' '.join(result['suggestions'])
            self.assertIn('정의', suggestions_text)

    def test_known_definitions(self):
        result = extract_acronyms('SEO 최적화를 진행합니다.')
        seo = [a for a in result['acronyms'] if a['term'] == 'SEO']
        if seo:
            self.assertIn('검색엔진', seo[0]['definition'])


if __name__ == '__main__':
    unittest.main()
