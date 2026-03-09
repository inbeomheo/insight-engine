"""
AI 코칭 서비스 테스트
"""
import unittest

from services.ai_coach_service import (
    CoachResponse,
    coach_session,
    get_channel_health_score,
)


def _make_channel_data(**overrides):
    """테스트용 채널 데이터 팩토리."""
    defaults = {
        'subscribers': 10000,
        'avg_views': 3000,
        'content_type': 'tutorial',
        'frequency': 'weekly',
    }
    defaults.update(overrides)
    return defaults


class TestCoachSessionBasic(unittest.TestCase):
    """기본 코칭 세션 검증."""

    def test_returns_coach_response(self):
        response = coach_session(_make_channel_data(), '성장 전략이 궁금합니다')
        self.assertIsInstance(response, CoachResponse)

    def test_question_preserved(self):
        question = '구독자를 늘리려면?'
        response = coach_session(_make_channel_data(), question)
        self.assertEqual(response.question, question)

    def test_has_analysis(self):
        response = coach_session(_make_channel_data(), '분석해주세요')
        self.assertTrue(len(response.analysis) > 0)

    def test_has_recommendations(self):
        response = coach_session(_make_channel_data(), '추천해주세요')
        self.assertIsInstance(response.recommendations, list)
        self.assertGreater(len(response.recommendations), 0)

    def test_has_action_plan(self):
        response = coach_session(_make_channel_data(), '계획 세워주세요')
        self.assertIsInstance(response.action_plan, list)
        self.assertGreater(len(response.action_plan), 0)


class TestCoachSessionEngagement(unittest.TestCase):
    """구독자/조회수 비율 분석 검증."""

    def test_high_engagement(self):
        """30% 이상 = excellent."""
        data = _make_channel_data(subscribers=1000, avg_views=500)
        response = coach_session(data, '참여도 분석')
        self.assertIn('우수', response.analysis)

    def test_low_engagement(self):
        """3% 미만 = low."""
        data = _make_channel_data(subscribers=100000, avg_views=100)
        response = coach_session(data, '참여도 분석')
        self.assertIn('낮습니다', response.analysis)

    def test_zero_subscribers(self):
        """구독자 0 = unknown."""
        data = _make_channel_data(subscribers=0)
        response = coach_session(data, '분석')
        self.assertIn('계산할 수 없습니다', response.analysis)


class TestCoachSessionChannelSize(unittest.TestCase):
    """채널 규모별 전략 검증."""

    def test_starter(self):
        data = _make_channel_data(subscribers=500)
        response = coach_session(data, '전략')
        self.assertIn('초기', response.analysis)

    def test_growing(self):
        data = _make_channel_data(subscribers=5000)
        response = coach_session(data, '전략')
        self.assertIn('성장', response.analysis)

    def test_established(self):
        data = _make_channel_data(subscribers=50000)
        response = coach_session(data, '전략')
        self.assertIn('안정', response.analysis)

    def test_major(self):
        data = _make_channel_data(subscribers=200000)
        response = coach_session(data, '전략')
        self.assertIn('대형', response.analysis)


class TestCoachSessionContentType(unittest.TestCase):
    """콘텐츠 유형별 조언 검증."""

    def test_tutorial_advice(self):
        data = _make_channel_data(content_type='tutorial')
        response = coach_session(data, '조언')
        self.assertIn('교육', response.analysis)

    def test_vlog_advice(self):
        data = _make_channel_data(content_type='vlog')
        response = coach_session(data, '조언')
        self.assertIn('친밀감', response.analysis)

    def test_review_advice(self):
        data = _make_channel_data(content_type='review')
        response = coach_session(data, '조언')
        self.assertIn('리뷰', response.analysis)

    def test_unknown_type(self):
        """알 수 없는 유형은 기본 조언."""
        data = _make_channel_data(content_type='unknown')
        response = coach_session(data, '조언')
        # 기본 조언이 반환되어야 함
        self.assertGreater(len(response.recommendations), 0)


class TestCoachSessionEmptyInput(unittest.TestCase):
    """빈 입력 처리."""

    def test_empty_channel_data(self):
        response = coach_session({}, '질문')
        self.assertIsInstance(response, CoachResponse)
        self.assertGreater(len(response.analysis), 0)

    def test_none_channel_data(self):
        response = coach_session(None, '질문')
        self.assertIsInstance(response, CoachResponse)

    def test_empty_question(self):
        response = coach_session(_make_channel_data(), '')
        self.assertEqual(response.question, '')
        self.assertGreater(len(response.analysis), 0)


class TestCoachSessionConfidence(unittest.TestCase):
    """신뢰도 점수 검증."""

    def test_full_data_high_confidence(self):
        """모든 데이터가 있으면 1.0."""
        data = _make_channel_data()
        response = coach_session(data, '질문')
        self.assertEqual(response.confidence, 1.0)

    def test_partial_data_lower_confidence(self):
        """일부 데이터 누락 시 낮은 신뢰도."""
        data = {'subscribers': 1000}
        response = coach_session(data, '질문')
        self.assertLess(response.confidence, 1.0)
        self.assertGreater(response.confidence, 0.0)

    def test_empty_data_low_confidence(self):
        """데이터 없으면 0.0."""
        response = coach_session({}, '질문')
        self.assertEqual(response.confidence, 0.0)

    def test_confidence_range(self):
        """신뢰도가 0~1 범위."""
        response = coach_session(_make_channel_data(), '질문')
        self.assertGreaterEqual(response.confidence, 0.0)
        self.assertLessEqual(response.confidence, 1.0)


class TestCoachSessionActionPlan(unittest.TestCase):
    """액션 플랜 구조 검증."""

    def test_action_plan_has_steps(self):
        response = coach_session(_make_channel_data(), '계획')
        self.assertGreater(len(response.action_plan), 0)
        # 각 항목이 단계 번호를 포함
        self.assertTrue(any('1단계' in step for step in response.action_plan))

    def test_action_plan_varies_by_tier(self):
        """채널 규모에 따라 액션 플랜이 달라짐."""
        small = coach_session(_make_channel_data(subscribers=500), '계획')
        large = coach_session(_make_channel_data(subscribers=50000), '계획')
        self.assertNotEqual(small.action_plan, large.action_plan)


class TestGetChannelHealthScore(unittest.TestCase):
    """채널 건강 점수 검증."""

    def test_returns_dict(self):
        result = get_channel_health_score(_make_channel_data())
        self.assertIsInstance(result, dict)
        self.assertIn('score', result)
        self.assertIn('grade', result)
        self.assertIn('breakdown', result)

    def test_score_range(self):
        result = get_channel_health_score(_make_channel_data())
        self.assertGreaterEqual(result['score'], 0)
        self.assertLessEqual(result['score'], 100)

    def test_grade_values(self):
        """등급은 A/B/C/D 중 하나."""
        result = get_channel_health_score(_make_channel_data())
        self.assertIn(result['grade'], ['A', 'B', 'C', 'D'])

    def test_high_score_grade_a(self):
        """좋은 데이터 → A 등급."""
        data = _make_channel_data(subscribers=10000, avg_views=5000)
        result = get_channel_health_score(data)
        self.assertIn(result['grade'], ['A', 'B'])  # 최소 B 이상

    def test_low_score_grade_d(self):
        """데이터 없음 → D 등급."""
        result = get_channel_health_score({})
        self.assertEqual(result['grade'], 'D')

    def test_breakdown_keys(self):
        result = get_channel_health_score(_make_channel_data())
        breakdown = result['breakdown']
        self.assertIn('engagement', breakdown)
        self.assertIn('frequency', breakdown)
        self.assertIn('strategy', breakdown)


class TestCoachResponseDataclass(unittest.TestCase):
    """dataclass 필드 타입 검증."""

    def test_fields(self):
        response = coach_session(_make_channel_data(), '테스트')

        self.assertIsInstance(response.question, str)
        self.assertIsInstance(response.analysis, str)
        self.assertIsInstance(response.recommendations, list)
        self.assertIsInstance(response.action_plan, list)
        self.assertIsInstance(response.confidence, float)


if __name__ == '__main__':
    unittest.main()
