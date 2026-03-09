"""개인화 콘텐츠 룸 서비스 테스트"""

import unittest
from services.personalized_room_service import (
    UserProfile, ContentRoom,
    create_profile, curate_room, score_relevance, update_interests,
    VALID_LEVELS,
)


class TestCreateProfile(unittest.TestCase):
    """create_profile 테스트"""

    def test_create_basic(self):
        """기본 프로필 생성"""
        profile = create_profile("user1", ["AI", "개발"], ["blog", "video"], "intermediate")
        self.assertEqual(profile.user_id, "user1")
        self.assertEqual(profile.interests, ["ai", "개발"])
        self.assertEqual(profile.reading_level, "intermediate")

    def test_invalid_level_raises(self):
        """유효하지 않은 레벨은 ValueError"""
        with self.assertRaises(ValueError):
            create_profile("u1", [], [], "expert")

    def test_interests_normalized(self):
        """관심사 소문자 + 공백 제거"""
        profile = create_profile("u1", ["  AI  ", " Python "], [], "beginner")
        self.assertEqual(profile.interests, ["ai", "python"])

    def test_empty_interests_filtered(self):
        """빈 관심사 필터링"""
        profile = create_profile("u1", ["AI", "", "  "], [], "beginner")
        self.assertEqual(profile.interests, ["ai"])

    def test_default_language(self):
        """기본 언어 ko"""
        profile = create_profile("u1", [], [], "intermediate")
        self.assertEqual(profile.language, "ko")


class TestScoreRelevance(unittest.TestCase):
    """score_relevance 테스트"""

    def setUp(self):
        self.profile = create_profile(
            "u1", ["ai", "python"], ["blog"], "intermediate", "ko"
        )

    def test_perfect_match(self):
        """완벽한 매칭 — 높은 점수"""
        content = {
            "tags": ["ai", "python"],
            "format": "blog",
            "level": "intermediate",
            "language": "ko",
        }
        score = score_relevance(content, self.profile)
        self.assertGreater(score, 0.8)

    def test_no_match(self):
        """매칭 없음 — 낮은 점수"""
        content = {
            "tags": ["요리", "여행"],
            "format": "podcast",
            "level": "advanced",
            "language": "en",
        }
        score = score_relevance(content, self.profile)
        self.assertLess(score, 0.4)

    def test_partial_match(self):
        """부분 매칭"""
        content = {
            "tags": ["ai", "요리"],
            "format": "video",
            "level": "intermediate",
            "language": "ko",
        }
        score = score_relevance(content, self.profile)
        self.assertGreater(score, 0.3)
        self.assertLess(score, 1.0)

    def test_score_range(self):
        """점수 범위 0~1"""
        content = {"tags": ["anything"], "format": "any", "level": "beginner", "language": "ja"}
        score = score_relevance(content, self.profile)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_empty_content_low_score(self):
        """빈 콘텐츠는 낮은 점수"""
        score = score_relevance({}, self.profile)
        self.assertLessEqual(score, 0.5)


class TestCurateRoom(unittest.TestCase):
    """curate_room 테스트"""

    def setUp(self):
        self.profile = create_profile("u1", ["ai"], ["blog"], "intermediate", "ko")
        self.pool = [
            {"id": "c1", "tags": ["ai"], "format": "blog", "level": "intermediate", "language": "ko"},
            {"id": "c2", "tags": ["요리"], "format": "video", "level": "beginner", "language": "ko"},
            {"id": "c3", "tags": ["ai"], "format": "blog", "level": "advanced", "language": "ko"},
        ]

    def test_curate_returns_room(self):
        """ContentRoom 반환"""
        room = curate_room(self.profile, self.pool)
        self.assertIsInstance(room, ContentRoom)
        self.assertEqual(room.user_id, "u1")

    def test_curate_sorted_by_relevance(self):
        """관련성 순 정렬"""
        room = curate_room(self.profile, self.pool)
        if len(room.recommended) >= 2:
            scores = [r["relevance_score"] for r in room.recommended]
            self.assertEqual(scores, sorted(scores, reverse=True))

    def test_curate_level_filter(self):
        """레벨 필터 적용 (1단계 이내만)"""
        # beginner 프로필에서 advanced는 2단계 차이 → 제외
        beginner_profile = create_profile("u2", ["ai"], [], "beginner", "ko")
        pool = [
            {"id": "c1", "tags": ["ai"], "level": "beginner", "language": "ko"},
            {"id": "c2", "tags": ["ai"], "level": "advanced", "language": "ko"},
        ]
        room = curate_room(beginner_profile, pool)
        ids = [r["id"] for r in room.recommended]
        self.assertIn("c1", ids)
        self.assertNotIn("c2", ids)

    def test_curate_empty_pool(self):
        """빈 풀"""
        room = curate_room(self.profile, [])
        self.assertEqual(len(room.recommended), 0)

    def test_filters_applied_recorded(self):
        """적용된 필터 기록"""
        room = curate_room(self.profile, self.pool)
        self.assertGreater(len(room.filters_applied), 0)


class TestUpdateInterests(unittest.TestCase):
    """update_interests 테스트"""

    def test_add_new_interests(self):
        """새 관심사 추가"""
        profile = create_profile("u1", ["ai"], [], "intermediate")
        updated = update_interests(profile, ["python", "rust"])
        self.assertIn("python", updated.interests)
        self.assertIn("rust", updated.interests)
        self.assertIn("ai", updated.interests)

    def test_no_duplicates(self):
        """중복 제거"""
        profile = create_profile("u1", ["ai", "python"], [], "intermediate")
        updated = update_interests(profile, ["ai", "python", "rust"])
        self.assertEqual(len(set(updated.interests)), len(updated.interests))

    def test_preserves_order(self):
        """기존 순서 유지"""
        profile = create_profile("u1", ["ai", "python"], [], "intermediate")
        updated = update_interests(profile, ["rust"])
        self.assertEqual(updated.interests[:2], ["ai", "python"])

    def test_preserves_other_fields(self):
        """다른 필드 보존"""
        profile = create_profile("u1", ["ai"], ["blog"], "advanced", "en")
        updated = update_interests(profile, ["python"])
        self.assertEqual(updated.reading_level, "advanced")
        self.assertEqual(updated.language, "en")
        self.assertEqual(updated.preferred_formats, ["blog"])


if __name__ == "__main__":
    unittest.main()
