"""Anaphora Repetition Detector 서비스 테스트."""
import unittest
from services.anaphora_repetition_service import detect_anaphora_repetition


class TestAnaphoraRepetition(unittest.TestCase):

    def test_empty_content(self):
        result = detect_anaphora_repetition('')
        self.assertEqual(result['score'], 100.0)
        self.assertEqual(result['summary']['groups_found'], 0)

    def test_none_content(self):
        result = detect_anaphora_repetition(None)
        self.assertEqual(result['score'], 100.0)

    def test_no_repetition(self):
        content = '첫 번째 문장입니다. 두 번째로 설명합니다. 세 번째 결론입니다. 네 번째 마무리합니다.'
        result = detect_anaphora_repetition(content)
        self.assertEqual(result['summary']['groups_found'], 0)

    def test_anaphora_detected(self):
        content = '우리는 꿈을 꿉니다. 우리는 도전합니다. 우리는 성장합니다. 우리는 이깁니다.'
        result = detect_anaphora_repetition(content)
        self.assertGreater(result['summary']['groups_found'], 0)
        self.assertGreater(result['summary']['repeated_sentences'], 0)

    def test_english_anaphora(self):
        content = 'We must fight for justice. We must fight for equality. We must fight for peace. We must fight for freedom.'
        result = detect_anaphora_repetition(content)
        self.assertGreater(result['summary']['groups_found'], 0)

    def test_intentional_detection(self):
        # 길이가 유사한 병렬 구조 → 의도적
        content = '나는 믿습니다 희망을. 나는 믿습니다 용기를. 나는 믿습니다 사랑을. 나는 믿습니다 미래를.'
        result = detect_anaphora_repetition(content)
        if result['anaphora_groups']:
            # 의도적 판별 여부 확인
            self.assertIn('is_intentional', result['anaphora_groups'][0])

    def test_short_content_skip(self):
        content = '짧은 글. 두 문장.'
        result = detect_anaphora_repetition(content)
        self.assertEqual(result['summary']['groups_found'], 0)

    def test_group_structure(self):
        content = '모든 사람은 평등합니다. 모든 사람은 자유롭습니다. 모든 사람은 존엄합니다. 다른 시작 문장입니다.'
        result = detect_anaphora_repetition(content)
        if result['anaphora_groups']:
            group = result['anaphora_groups'][0]
            self.assertIn('prefix', group)
            self.assertIn('count', group)
            self.assertIn('sentences', group)
            self.assertIn('is_intentional', group)

    def test_multiple_groups(self):
        content = ('우리는 배웁니다. 우리는 성장합니다. 우리는 도전합니다. '
                   '그들은 노력합니다. 그들은 달립니다. 그들은 이깁니다.')
        result = detect_anaphora_repetition(content)
        self.assertGreaterEqual(result['summary']['groups_found'], 1)

    def test_score_perfect_no_repeat(self):
        content = '각각 다른 시작. 모두 고유한 표현. 전혀 반복 없음. 완전히 새로운 문장.'
        result = detect_anaphora_repetition(content)
        self.assertEqual(result['score'], 100.0)

    def test_suggestions_with_groups(self):
        content = '항상 노력합니다. 항상 최선입니다. 항상 성장합니다. 항상 발전합니다.'
        result = detect_anaphora_repetition(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_return_structure(self):
        content = '테스트 문장입니다. 확인합니다.'
        result = detect_anaphora_repetition(content)
        self.assertIn('anaphora_groups', result)
        self.assertIn('summary', result)
        self.assertIn('score', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_sentences', result['summary'])
        self.assertIn('groups_found', result['summary'])
        self.assertIn('intentional_count', result['summary'])


if __name__ == '__main__':
    unittest.main()
