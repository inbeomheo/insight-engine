"""cta_optimizer_service 단위 테스트"""
import unittest

from services.seo.cta_optimizer_service import (
    analyze_ctas,
    suggest_ctas,
    _detect_cta_type,
    _calculate_strength,
)


class TestAnalyzeCtas(unittest.TestCase):

    def test_empty_content(self):
        result = analyze_ctas('')
        self.assertEqual(result['ctas'], [])
        self.assertEqual(result['summary']['total'], 0)

    def test_none_content(self):
        result = analyze_ctas(None)
        self.assertEqual(result['summary']['total'], 0)

    def test_no_cta_content(self):
        result = analyze_ctas('파이썬은 프로그래밍 언어입니다. 간결한 문법이 특징입니다.')
        self.assertEqual(result['summary']['total'], 0)
        self.assertIn('CTA가 감지되지 않았습니다', result['suggestions'][0])

    def test_subscribe_cta(self):
        result = analyze_ctas('좋은 글이었습니다. 구독하고 알림 설정 해주세요!')
        self.assertGreater(result['summary']['total'], 0)
        types = result['summary']['types']
        self.assertIn('subscribe', types)

    def test_comment_cta(self):
        result = analyze_ctas('여러분은 어떻게 생각하시나요? 댓글로 의견을 남겨주세요.')
        self.assertGreater(result['summary']['total'], 0)

    def test_multiple_ctas(self):
        content = '구독해 주세요. 중간 내용입니다. 댓글을 남겨주세요. 공유도 부탁드립니다.'
        result = analyze_ctas(content)
        self.assertGreaterEqual(result['summary']['total'], 3)

    def test_position_distribution(self):
        lines = ['구독해주세요.'] + ['일반 내용입니다.'] * 8 + ['댓글을 남겨주세요.']
        content = '\n'.join(lines)
        result = analyze_ctas(content)
        pos = result['position_distribution']
        self.assertGreater(pos['top'] + pos['bottom'], 0)

    def test_suggestions_no_bottom_cta(self):
        content = '구독해 주세요.\n일반 내용.\n일반 내용.\n일반 내용.\n일반 내용.\n일반 마무리.'
        result = analyze_ctas(content)
        suggestions_text = ' '.join(result['suggestions'])
        # CTA가 있지만 하단에 없을 때 제안 확인
        self.assertIsInstance(result['suggestions'], list)


class TestSuggestCtas(unittest.TestCase):

    def test_default_goal(self):
        result = suggest_ctas('파이썬 프로그래밍에 대한 글입니다.')
        self.assertEqual(result['goal'], 'engagement')
        self.assertGreater(len(result['suggestions']), 0)

    def test_awareness_goal(self):
        result = suggest_ctas('테스트 콘텐츠', 'awareness')
        self.assertEqual(result['goal'], 'awareness')
        self.assertEqual(result['goal_label'], '인지도')

    def test_conversion_goal(self):
        result = suggest_ctas('테스트', 'conversion')
        self.assertEqual(result['goal'], 'conversion')
        self.assertGreater(len(result['suggestions']), 0)

    def test_invalid_goal_defaults(self):
        result = suggest_ctas('테스트', 'invalid')
        self.assertEqual(result['goal'], 'engagement')

    def test_placement_tips(self):
        result = suggest_ctas('콘텐츠')
        self.assertGreater(len(result['placement_tips']), 0)

    def test_topic_based_suggestion(self):
        result = suggest_ctas('파이썬 프로그래밍은 초보자에게 좋습니다. 파이썬 문법은 간결합니다.', 'engagement')
        # 주제어 기반 맞춤 제안이 포함되어야 함
        self.assertGreater(len(result['suggestions']), 2)


class TestDetectCtaType(unittest.TestCase):

    def test_subscribe(self):
        self.assertEqual(_detect_cta_type('채널 구독 부탁드립니다'), 'subscribe')

    def test_share(self):
        self.assertEqual(_detect_cta_type('이 글을 공유해 주세요'), 'share')

    def test_no_cta(self):
        self.assertIsNone(_detect_cta_type('파이썬은 프로그래밍 언어입니다'))

    def test_action_verb(self):
        self.assertEqual(_detect_cta_type('지금 경험해보세요'), 'action')


class TestCalculateStrength(unittest.TestCase):

    def test_basic_strength(self):
        score = _calculate_strength('구독하세요')
        self.assertGreaterEqual(score, 1)
        self.assertLessEqual(score, 10)

    def test_urgency_increases_strength(self):
        basic = _calculate_strength('구독하세요')
        urgent = _calculate_strength('지금 바로 구독하세요!')
        self.assertGreater(urgent, basic)


if __name__ == '__main__':
    unittest.main()
