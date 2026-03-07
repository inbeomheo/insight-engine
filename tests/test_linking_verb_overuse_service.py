"""Linking Verb Overuse Detector 서비스 테스트."""
import unittest
from services.linking_verb_overuse_service import detect_linking_verb_overuse


class TestLinkingVerbOveruseDetector(unittest.TestCase):

    def test_empty_content(self):
        result = detect_linking_verb_overuse('')
        self.assertEqual(result['score'], 100.0)
        self.assertEqual(result['summary']['total_linking_verbs'], 0)

    def test_none_content(self):
        result = detect_linking_verb_overuse(None)
        self.assertEqual(result['score'], 100.0)

    def test_no_linking_verbs(self):
        content = '프로젝트를 완성했습니다. 코드를 배포합니다. 결과를 확인합니다.'
        result = detect_linking_verb_overuse(content)
        self.assertEqual(result['summary']['total_linking_verbs'], 0)

    def test_korean_linking_verbs(self):
        content = '이것은 테스트입니다. 그것은 중요합니다. 저것도 필요합니다.'
        result = detect_linking_verb_overuse(content)
        self.assertGreater(result['summary']['total_linking_verbs'], 0)

    def test_english_linking_verbs(self):
        content = 'This is important. That is good. It was great.'
        result = detect_linking_verb_overuse(content)
        self.assertGreater(result['summary']['total_linking_verbs'], 0)

    def test_high_ratio(self):
        content = '이것은 A입니다. 저것은 B입니다. 그것은 C입니다. 우리는 D입니다.'
        result = detect_linking_verb_overuse(content)
        self.assertGreater(result['summary']['linking_verb_ratio'], 50.0)

    def test_low_ratio(self):
        content = '프로젝트를 시작합니다. 코드를 작성합니다. 테스트를 실행합니다. 이것은 완료입니다.'
        result = detect_linking_verb_overuse(content)
        self.assertLess(result['summary']['linking_verb_ratio'], 50.0)

    def test_there_is_pattern(self):
        content = 'There is a problem. There are many solutions.'
        result = detect_linking_verb_overuse(content)
        self.assertGreater(result['summary']['total_linking_verbs'], 0)

    def test_score_high_with_active_verbs(self):
        content = '프로젝트를 만듭니다. 코드를 검증합니다. 결과를 분석합니다.'
        result = detect_linking_verb_overuse(content)
        self.assertGreaterEqual(result['score'], 80.0)

    def test_score_low_with_many_linking(self):
        content = '이것은 A입니다. 저것은 B입니다. 그것은 C입니다. 우리는 D입니다. 그들은 E입니다.'
        result = detect_linking_verb_overuse(content)
        self.assertLess(result['score'], 80.0)

    def test_sentences_only_linking(self):
        content = '이것은 테스트입니다. 프로젝트를 완성합니다.'
        result = detect_linking_verb_overuse(content)
        linking_sents = result['sentences']
        self.assertTrue(all(s['linking_count'] > 0 for s in linking_sents))

    def test_suggestions_high_ratio(self):
        content = '이것은 A입니다. 저것은 B입니다. 그것은 C입니다. 우리는 D입니다. 그들은 E입니다.'
        result = detect_linking_verb_overuse(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_return_structure(self):
        content = '이것은 테스트입니다.'
        result = detect_linking_verb_overuse(content)
        self.assertIn('sentences', result)
        self.assertIn('summary', result)
        self.assertIn('score', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_linking_verbs', result['summary'])
        self.assertIn('linking_verb_ratio', result['summary'])
        self.assertIn('density', result['summary'])


if __name__ == '__main__':
    unittest.main()
