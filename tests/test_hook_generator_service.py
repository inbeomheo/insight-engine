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


class TestGenerateHooksEdgeCases(unittest.TestCase):
    """generate_hooks 엣지 케이스 테스트"""

    def test_whitespace_only_topic(self):
        """공백만 있는 주제는 빈 결과"""
        result = generate_hooks('   ')
        self.assertEqual(result['total'], 0)

    def test_count_zero_returns_at_least_one(self):
        """count=0은 max(1, 0)=1로 최소 1개 반환"""
        result = generate_hooks('AI', count=0)
        self.assertGreaterEqual(result['total'], 1)

    def test_count_negative_returns_at_least_one(self):
        """음수 count는 max(1, ...)로 최소 1개 반환"""
        result = generate_hooks('AI', count=-5)
        self.assertGreaterEqual(result['total'], 1)

    def test_topic_stripped(self):
        """주제 앞뒤 공백 제거"""
        result = generate_hooks('  인공지능  ')
        self.assertEqual(result['topic'], '인공지능')

    def test_content_without_stats(self):
        """통계 없는 콘텐츠에서도 정상 동작"""
        result = generate_hooks('테스트', content='일반 텍스트 설명입니다')
        self.assertGreater(result['total'], 0)

    def test_empty_recommendation_when_no_hooks(self):
        """빈 결과일 때 recommendation은 빈 문자열"""
        result = generate_hooks('')
        self.assertEqual(result['recommendation'], '')


class TestExtractStatsEdgeCases(unittest.TestCase):
    """_extract_stats 엣지 케이스 테스트"""

    def test_korean_unit_pattern(self):
        """한국어 단위 패턴 (만/억 + 명/원/건/개)"""
        stats = _extract_stats('참여자가 100만명을 돌파했습니다')
        self.assertGreater(len(stats), 0)

    def test_short_match_filtered(self):
        """5자 미만 매칭은 제외"""
        stats = _extract_stats('5%')
        self.assertEqual(len(stats), 0)

    def test_long_match_filtered(self):
        """50자 초과 매칭은 제외"""
        long_text = 'a' * 45 + ' 50%' + 'b' * 10
        stats = _extract_stats(long_text)
        # 50자 초과인 매칭은 필터링됨
        for s in stats:
            self.assertLessEqual(len(s), 50)


if __name__ == '__main__':
    unittest.main()
