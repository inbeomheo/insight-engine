"""퀘스트 시스템 서비스 테스트"""
import unittest

from services.quest_system_service import (
    Quest,
    QuestProgress,
    Badge,
    Milestone,
    create_quest,
    check_progress,
    award_badge,
    get_quest,
    get_badges_for_quest,
    clear_all,
    VALID_BADGE_TYPES,
    _determine_badge_type,
    _calculate_default_xp,
)


class TestDetermineBasgeType(unittest.TestCase):
    """배지 타입 결정 테스트"""

    def test_few_milestones_bronze(self):
        self.assertEqual(_determine_badge_type(1), "bronze")
        self.assertEqual(_determine_badge_type(3), "bronze")

    def test_medium_milestones_silver(self):
        self.assertEqual(_determine_badge_type(5), "silver")

    def test_many_milestones_gold(self):
        self.assertEqual(_determine_badge_type(10), "gold")

    def test_lots_milestones_platinum(self):
        self.assertEqual(_determine_badge_type(15), "platinum")


class TestCalculateDefaultXp(unittest.TestCase):
    """기본 XP 계산 테스트"""

    def test_first_milestone(self):
        self.assertEqual(_calculate_default_xp(0), 100)

    def test_xp_increases(self):
        """뒤 마일스톤일수록 XP 증가"""
        self.assertGreater(_calculate_default_xp(3), _calculate_default_xp(0))


class TestCreateQuest(unittest.TestCase):
    """퀘스트 생성 테스트"""

    def setUp(self):
        clear_all()

    def test_basic_creation(self):
        milestones = [
            {'name': '에피소드 1 시청', 'xp': 100},
            {'name': '에피소드 2 시청', 'xp': 150},
        ]
        quest = create_quest('series_abc', milestones)
        self.assertIsInstance(quest, Quest)
        self.assertEqual(quest.series_id, 'series_abc')
        self.assertEqual(len(quest.milestones), 2)

    def test_quest_id_unique(self):
        q1 = create_quest('s1', [{'name': 'a'}])
        q2 = create_quest('s2', [{'name': 'b'}])
        self.assertNotEqual(q1.quest_id, q2.quest_id)

    def test_xp_total_sum(self):
        milestones = [{'name': 'a', 'xp': 100}, {'name': 'b', 'xp': 200}]
        quest = create_quest('s1', milestones)
        self.assertEqual(quest.xp_total, 300)

    def test_default_xp_when_omitted(self):
        """xp 미지정 시 기본 XP 할당"""
        quest = create_quest('s1', [{'name': 'a'}, {'name': 'b'}])
        self.assertGreater(quest.milestones[0].xp, 0)
        self.assertGreater(quest.milestones[1].xp, 0)

    def test_milestones_initially_incomplete(self):
        quest = create_quest('s1', [{'name': 'a'}])
        for ms in quest.milestones:
            self.assertFalse(ms.completed)

    def test_badge_type_auto_assigned(self):
        quest = create_quest('s1', [{'name': 'a'}])
        self.assertIn(quest.badge, VALID_BADGE_TYPES)

    def test_quest_stored_in_memory(self):
        quest = create_quest('s1', [{'name': 'a'}])
        retrieved = get_quest(quest.quest_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.quest_id, quest.quest_id)

    def test_title_includes_series_id(self):
        quest = create_quest('my_series', [{'name': 'a'}])
        self.assertIn('my_series', quest.title)


class TestCheckProgress(unittest.TestCase):
    """진행도 체크 테스트"""

    def setUp(self):
        clear_all()
        milestones = [
            {'milestone_id': 'm1', 'name': 'Step 1', 'xp': 100},
            {'milestone_id': 'm2', 'name': 'Step 2', 'xp': 200},
            {'milestone_id': 'm3', 'name': 'Step 3', 'xp': 300},
        ]
        self.quest = create_quest('test_series', milestones)

    def test_no_progress(self):
        progress = check_progress(self.quest.quest_id, [])
        self.assertEqual(progress.completed, 0)
        self.assertEqual(progress.total, 3)
        self.assertAlmostEqual(progress.progress_pct, 0.0)
        self.assertEqual(progress.xp_earned, 0)

    def test_partial_progress(self):
        progress = check_progress(self.quest.quest_id, ['m1'])
        self.assertEqual(progress.completed, 1)
        self.assertAlmostEqual(progress.progress_pct, 33.3)
        self.assertEqual(progress.xp_earned, 100)

    def test_full_progress(self):
        progress = check_progress(self.quest.quest_id, ['m1', 'm2', 'm3'])
        self.assertEqual(progress.completed, 3)
        self.assertAlmostEqual(progress.progress_pct, 100.0)
        self.assertEqual(progress.xp_earned, 600)

    def test_invalid_milestone_ignored(self):
        """존재하지 않는 마일스톤 ID는 무시"""
        progress = check_progress(self.quest.quest_id, ['m1', 'invalid_id'])
        self.assertEqual(progress.completed, 1)

    def test_nonexistent_quest_raises(self):
        with self.assertRaises(KeyError):
            check_progress('nonexistent', ['m1'])

    def test_progress_returns_correct_type(self):
        progress = check_progress(self.quest.quest_id, ['m1'])
        self.assertIsInstance(progress, QuestProgress)


class TestAwardBadge(unittest.TestCase):
    """배지 부여 테스트"""

    def setUp(self):
        clear_all()
        self.quest = create_quest('s1', [{'name': 'a', 'xp': 100}])

    def test_award_bronze(self):
        badge = award_badge(self.quest.quest_id, 'bronze')
        self.assertIsInstance(badge, Badge)
        self.assertEqual(badge.badge_type, 'bronze')
        self.assertEqual(badge.quest_id, self.quest.quest_id)

    def test_award_all_types(self):
        for bt in VALID_BADGE_TYPES:
            badge = award_badge(self.quest.quest_id, bt)
            self.assertEqual(badge.badge_type, bt)

    def test_badge_has_timestamp(self):
        badge = award_badge(self.quest.quest_id, 'gold')
        self.assertTrue(badge.earned_at)
        # ISO 8601 형식 확인
        self.assertIn('T', badge.earned_at)

    def test_badge_id_unique(self):
        b1 = award_badge(self.quest.quest_id, 'bronze')
        b2 = award_badge(self.quest.quest_id, 'silver')
        self.assertNotEqual(b1.badge_id, b2.badge_id)

    def test_invalid_badge_type_raises(self):
        with self.assertRaises(ValueError):
            award_badge(self.quest.quest_id, 'diamond')

    def test_nonexistent_quest_raises(self):
        with self.assertRaises(KeyError):
            award_badge('nonexistent', 'bronze')

    def test_get_badges_for_quest(self):
        award_badge(self.quest.quest_id, 'bronze')
        award_badge(self.quest.quest_id, 'silver')
        badges = get_badges_for_quest(self.quest.quest_id)
        self.assertEqual(len(badges), 2)


class TestClearAll(unittest.TestCase):
    """인메모리 초기화 테스트"""

    def test_clear_removes_quests(self):
        quest = create_quest('s1', [{'name': 'a'}])
        clear_all()
        self.assertIsNone(get_quest(quest.quest_id))

    def test_clear_removes_badges(self):
        quest = create_quest('s1', [{'name': 'a'}])
        award_badge(quest.quest_id, 'bronze')
        clear_all()
        self.assertEqual(len(get_badges_for_quest(quest.quest_id)), 0)


if __name__ == '__main__':
    unittest.main()
