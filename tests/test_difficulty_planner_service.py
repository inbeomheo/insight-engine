"""
난이도 플래닝 서비스 테스트
"""
import unittest

from services.difficulty_planner_service import (
    DifficultyPlan,
    DifficultyLevel,
    plan_difficulty,
    get_supported_domains,
    get_level_by_name,
    estimate_total_time,
)


class TestPlanDifficultyBasic(unittest.TestCase):
    """기본 플랜 생성 검증."""

    def test_returns_difficulty_plan(self):
        plan = plan_difficulty('Python')
        self.assertIsInstance(plan, DifficultyPlan)
        self.assertEqual(plan.topic, 'Python')

    def test_has_four_levels(self):
        plan = plan_difficulty('JavaScript')
        self.assertEqual(len(plan.levels), 4)

    def test_level_order(self):
        plan = plan_difficulty('React')
        expected = ['beginner', 'intermediate', 'advanced', 'expert']
        actual = [level.level for level in plan.levels]
        self.assertEqual(actual, expected)


class TestPlanDifficultyDomains(unittest.TestCase):
    """도메인별 플랜 생성 검증."""

    def test_programming_domain(self):
        plan = plan_difficulty('Python', domain='programming')
        self.assertEqual(plan.domain, 'programming')
        # 프로그래밍 도메인 특화 설명 확인
        self.assertIn('Python', plan.levels[0].description)

    def test_design_domain(self):
        plan = plan_difficulty('UI/UX', domain='design')
        self.assertEqual(plan.domain, 'design')

    def test_marketing_domain(self):
        plan = plan_difficulty('SNS 마케팅', domain='marketing')
        self.assertEqual(plan.domain, 'marketing')

    def test_general_domain_default(self):
        plan = plan_difficulty('아무 주제')
        self.assertEqual(plan.domain, 'general')

    def test_unknown_domain_fallback(self):
        """알 수 없는 도메인은 general로 폴백."""
        plan = plan_difficulty('주제', domain='nonexistent')
        self.assertEqual(plan.domain, 'general')


class TestPlanDifficultyLevelContent(unittest.TestCase):
    """레벨 내용 검증."""

    def test_level_names_korean(self):
        plan = plan_difficulty('테스트')
        names = [level.name for level in plan.levels]
        self.assertEqual(names, ['입문', '중급', '고급', '전문가'])

    def test_beginner_no_prerequisites(self):
        plan = plan_difficulty('테스트')
        beginner = plan.levels[0]
        self.assertEqual(beginner.prerequisites, [])

    def test_advanced_has_prerequisites(self):
        plan = plan_difficulty('테스트', domain='programming')
        advanced = plan.levels[2]
        self.assertGreater(len(advanced.prerequisites), 0)

    def test_estimated_time_not_empty(self):
        plan = plan_difficulty('테스트')
        for level in plan.levels:
            self.assertTrue(level.estimated_time)
            self.assertIn('주', level.estimated_time)


class TestPlanDifficultyRecommendedStart(unittest.TestCase):
    """권장 시작 레벨 검증."""

    def test_recommended_start_beginner(self):
        plan = plan_difficulty('새로운 주제')
        self.assertEqual(plan.recommended_start, 'beginner')


class TestPlanDifficultyEmptyTopic(unittest.TestCase):
    """빈 주제 처리."""

    def test_empty_topic(self):
        plan = plan_difficulty('')
        self.assertEqual(plan.topic, '미정')

    def test_none_topic(self):
        plan = plan_difficulty(None)
        self.assertEqual(plan.topic, '미정')

    def test_whitespace_topic(self):
        plan = plan_difficulty('   ')
        self.assertEqual(plan.topic, '미정')


class TestPlanDifficultyTopicInDescription(unittest.TestCase):
    """주제명이 설명에 포함되는지 확인."""

    def test_topic_in_all_descriptions(self):
        plan = plan_difficulty('머신러닝')
        for level in plan.levels:
            self.assertIn('머신러닝', level.description)


class TestGetSupportedDomains(unittest.TestCase):
    """지원 도메인 목록."""

    def test_returns_list(self):
        domains = get_supported_domains()
        self.assertIsInstance(domains, list)
        self.assertGreater(len(domains), 0)

    def test_includes_general(self):
        self.assertIn('general', get_supported_domains())

    def test_includes_programming(self):
        self.assertIn('programming', get_supported_domains())


class TestGetLevelByName(unittest.TestCase):
    """특정 레벨 조회."""

    def test_find_beginner(self):
        plan = plan_difficulty('테스트')
        level = get_level_by_name(plan, 'beginner')
        self.assertIsNotNone(level)
        self.assertEqual(level.level, 'beginner')

    def test_find_expert(self):
        plan = plan_difficulty('테스트')
        level = get_level_by_name(plan, 'expert')
        self.assertIsNotNone(level)
        self.assertEqual(level.level, 'expert')

    def test_not_found(self):
        plan = plan_difficulty('테스트')
        level = get_level_by_name(plan, 'nonexistent')
        self.assertIsNone(level)


class TestEstimateTotalTime(unittest.TestCase):
    """총 예상 시간 계산."""

    def test_returns_week_format(self):
        plan = plan_difficulty('테스트')
        total = estimate_total_time(plan)
        self.assertIn('주', total)

    def test_reasonable_range(self):
        """총 시간이 합리적 범위인지."""
        plan = plan_difficulty('테스트')
        total = estimate_total_time(plan)
        # "N-M주" 형식에서 숫자 추출
        import re
        nums = re.findall(r'\d+', total)
        self.assertEqual(len(nums), 2)
        min_weeks = int(nums[0])
        max_weeks = int(nums[1])
        self.assertGreater(min_weeks, 0)
        self.assertGreater(max_weeks, min_weeks)


class TestDifficultyLevelDataclass(unittest.TestCase):
    """dataclass 필드 타입 검증."""

    def test_level_fields(self):
        plan = plan_difficulty('테스트')
        level = plan.levels[0]

        self.assertIsInstance(level, DifficultyLevel)
        self.assertIsInstance(level.level, str)
        self.assertIsInstance(level.name, str)
        self.assertIsInstance(level.description, str)
        self.assertIsInstance(level.prerequisites, list)
        self.assertIsInstance(level.estimated_time, str)


if __name__ == '__main__':
    unittest.main()
