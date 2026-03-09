"""AI 멘토 마켓 서비스 테스트"""
import unittest
from services.ai_mentor_market_service import (
    match_mentors, rate_mentor, get_top_mentors, Mentor, MentorMatch
)


class TestAiMentorMarketService(unittest.TestCase):

    def setUp(self):
        self.mentors = [
            Mentor('m1', '김멘토', ['python', 'ai'], True, 4.5, 10),
            Mentor('m2', '이멘토', ['java', 'backend'], True, 4.8, 20),
            Mentor('m3', '박멘토', ['python', 'web'], False, 4.0, 5),
            Mentor('m4', '최멘토', ['ai', 'data'], True, 3.5, 3),
        ]

    def test_match_by_skill(self):
        matches = match_mentors(['python', 'ai'], self.mentors)
        # m3은 비가용 → 제외
        mentor_ids = [m.mentor_id for m in matches]
        self.assertIn('m1', mentor_ids)
        self.assertNotIn('m3', mentor_ids)

    def test_match_excludes_unavailable(self):
        matches = match_mentors(['python'], self.mentors)
        for m in matches:
            self.assertNotEqual(m.mentor_id, 'm3')

    def test_match_returns_sorted_by_score(self):
        matches = match_mentors(['python', 'ai'], self.mentors)
        if len(matches) > 1:
            self.assertGreaterEqual(matches[0].compatibility_score, matches[1].compatibility_score)

    def test_match_no_overlap(self):
        matches = match_mentors(['rust'], self.mentors)
        self.assertEqual(len(matches), 0)

    def test_match_returns_matched_skills(self):
        matches = match_mentors(['python'], self.mentors)
        for m in matches:
            self.assertIn('python', m.matched_skills)

    def test_rate_mentor_updates(self):
        updated = rate_mentor(self.mentors[0], 5.0)
        self.assertEqual(updated.sessions_completed, 11)
        self.assertAlmostEqual(updated.rating, (4.5 * 10 + 5.0) / 11, places=2)

    def test_rate_mentor_preserves_fields(self):
        updated = rate_mentor(self.mentors[0], 3.0)
        self.assertEqual(updated.mentor_id, 'm1')
        self.assertEqual(updated.name, '김멘토')

    def test_get_top_mentors(self):
        top = get_top_mentors(self.mentors, 2)
        self.assertEqual(len(top), 2)
        self.assertEqual(top[0].mentor_id, 'm2')  # 4.8 최고

    def test_get_top_mentors_exceeds_count(self):
        top = get_top_mentors(self.mentors, 100)
        self.assertEqual(len(top), 4)

    def test_match_case_insensitive(self):
        matches = match_mentors(['Python', 'AI'], self.mentors)
        self.assertGreater(len(matches), 0)


if __name__ == '__main__':
    unittest.main()
