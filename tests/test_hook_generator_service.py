"""hook_generator_service 단위 테스트"""
import unittest

from services.content.hook_generator_service import (
    generate_hooks,
    _extract_stats,
    _rate_effectiveness,
)


class TestGenerateHooks(unittest.TestCase):

    def test_empty_topic(self):
        result = generate_hooks('')
        self.assertEqual(result['total'], 0)
        self.assertEqual(result['hooks'], [])

    def test_none_topic(self):
        result = generate_hooks(None)
        self.assertEqual(result['total'], 0)

    def test_basic_hooks(self):
        result = generate_hooks('인공지능')
        self.assertGreater(result['total'], 0)
        self.assertEqual(result['topic'], '인공지능')
        for hook in result['hooks']:
            self.assertIn('type', hook)
            self.assertIn('text', hook)
            self.assertIn('effectiveness', hook)
            self.assertIn('인공지능', hook['text'])

    def test_count_limit(self):
        result = generate_hooks('테스트 주제', count=3)
        self.assertLessEqual(result['total'], 3)

    def test_max_count_cap(self):
        result = generate_hooks('테스트', count=20)
        self.assertLessEqual(result['total'], 12)

    def test_with_content_stats(self):
        content = '사용자의 75% 이상이 만족했습니다. 매출이 3배 증가했습니다.'
        result = generate_hooks('서비스 개선', content=content)
        # 통계가 있으면 statistic 패턴의 훅이 포함될 수 있음
        self.assertGreater(result['total'], 0)

    def test_recommendation_exists(self):
        result = generate_hooks('블록체인')
        self.assertIsInstance(result['recommendation'], str)
        self.assertGreater(len(result['recommendation']), 0)

    def test_hook_types_diverse(self):
        result = generate_hooks('데이터 분석', count=6)
        types = {h['type'] for h in result['hooks']}
        # 최소 2가지 이상의 패턴 유형
        self.assertGreaterEqual(len(types), 2)


class TestExtractStats(unittest.TestCase):

    def test_extracts_percentage(self):
        stats = _extract_stats('사용자의 75%가 만족했습니다')
        self.assertGreater(len(stats), 0)

    def test_extracts_multiplier(self):
        stats = _extract_stats('매출이 3배 증가했습니다')
        self.assertGreater(len(stats), 0)

    def test_empty_content(self):
        self.assertEqual(_extract_stats(''), [])
        self.assertEqual(_extract_stats(None), [])

    def test_max_stats(self):
        content = '10% 증가, 20% 감소, 30% 유지, 40% 상승, 50% 변동, 60% 확인' * 3
        stats = _extract_stats(content)
        self.assertLessEqual(len(stats), 5)


class TestRateEffectiveness(unittest.TestCase):

    def test_high_patterns(self):
        self.assertEqual(_rate_effectiveness('question'), 'high')
        self.assertEqual(_rate_effectiveness('statistic'), 'high')
        self.assertEqual(_rate_effectiveness('pain_point'), 'high')

    def test_medium_patterns(self):
        self.assertEqual(_rate_effectiveness('story'), 'medium')
        self.assertEqual(_rate_effectiveness('promise'), 'medium')
        self.assertEqual(_rate_effectiveness('contrarian'), 'medium')


if __name__ == '__main__':
    unittest.main()
