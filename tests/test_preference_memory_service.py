"""
선호 메모리 서비스 테스트
"""

import unittest

from services.preference_memory_service import (
    Preference,
    PreferenceProfile,
    _create_profile,
    record_preference,
    get_preferences,
    apply_preferences,
    decay_preferences,
    export_profile,
)


class TestRecordPreference(unittest.TestCase):
    """선호 기록 테스트"""

    def test_record_new(self):
        """새 선호 기록"""
        profile = _create_profile("user1")
        profile = record_preference(profile, "style", "blog_seo", 0.9)
        self.assertEqual(len(profile.preferences), 1)
        self.assertEqual(profile.preferences[0].category, "style")
        self.assertEqual(profile.preferences[0].value, "blog_seo")
        self.assertEqual(profile.preferences[0].weight, 0.9)

    def test_record_update_existing(self):
        """기존 선호 업데이트"""
        profile = _create_profile("user1")
        profile = record_preference(profile, "style", "blog_seo", 0.5)
        profile = record_preference(profile, "style", "blog_seo", 0.9)
        self.assertEqual(len(profile.preferences), 1)
        self.assertEqual(profile.preferences[0].weight, 0.9)

    def test_record_different_categories(self):
        """다른 카테고리 기록"""
        profile = _create_profile("user1")
        profile = record_preference(profile, "style", "blog_seo", 0.8)
        profile = record_preference(profile, "language", "ko", 1.0)
        self.assertEqual(len(profile.preferences), 2)

    def test_record_weight_clamped(self):
        """가중치 클램핑 (0.0 ~ 1.0)"""
        profile = _create_profile("user1")
        profile = record_preference(profile, "style", "test", 1.5)
        self.assertEqual(profile.preferences[0].weight, 1.0)
        profile = record_preference(profile, "style", "test", -0.5)
        self.assertEqual(profile.preferences[0].weight, 0.0)

    def test_record_history_added(self):
        """히스토리 기록"""
        profile = _create_profile("user1")
        profile = record_preference(profile, "style", "blog_seo", 0.8)
        self.assertEqual(len(profile.history), 1)
        self.assertEqual(profile.history[0]["action"], "added")

    def test_record_update_history(self):
        """업데이트 히스토리"""
        profile = _create_profile("user1")
        profile = record_preference(profile, "style", "blog_seo", 0.5)
        profile = record_preference(profile, "style", "blog_seo", 0.9)
        self.assertEqual(len(profile.history), 2)
        self.assertEqual(profile.history[1]["action"], "updated")
        self.assertEqual(profile.history[1]["old_weight"], 0.5)

    def test_record_updated_at(self):
        """updated_at 필드 갱신"""
        profile = _create_profile("user1")
        profile = record_preference(profile, "style", "test", 0.5)
        self.assertNotEqual(profile.preferences[0].updated_at, "")


class TestGetPreferences(unittest.TestCase):
    """선호 조회 테스트"""

    def setUp(self):
        self.profile = _create_profile("user1")
        self.profile = record_preference(self.profile, "style", "blog_seo", 0.9)
        self.profile = record_preference(self.profile, "style", "summary", 0.5)
        self.profile = record_preference(self.profile, "language", "ko", 1.0)

    def test_get_by_category(self):
        """카테고리별 조회"""
        prefs = get_preferences(self.profile, "style")
        self.assertEqual(len(prefs), 2)

    def test_get_all(self):
        """전체 조회"""
        prefs = get_preferences(self.profile, None)
        self.assertEqual(len(prefs), 3)

    def test_get_sorted_by_weight(self):
        """가중치 내림차순 정렬"""
        prefs = get_preferences(self.profile, "style")
        self.assertGreaterEqual(prefs[0].weight, prefs[1].weight)

    def test_get_empty_category(self):
        """빈 카테고리"""
        prefs = get_preferences(self.profile, "nonexistent")
        self.assertEqual(prefs, [])


class TestApplyPreferences(unittest.TestCase):
    """선호 기반 정렬 테스트"""

    def test_apply_basic(self):
        """기본 적용"""
        profile = _create_profile("user1")
        profile = record_preference(profile, "style", "blog_seo", 0.9)
        options = [
            {"style": "summary", "title": "요약"},
            {"style": "blog_seo", "title": "블로그"},
        ]
        sorted_opts = apply_preferences(profile, options)
        self.assertEqual(sorted_opts[0]["style"], "blog_seo")

    def test_apply_multiple_prefs(self):
        """여러 선호 합산"""
        profile = _create_profile("user1")
        profile = record_preference(profile, "style", "blog_seo", 0.5)
        profile = record_preference(profile, "language", "ko", 0.5)
        options = [
            {"style": "summary", "language": "en"},
            {"style": "blog_seo", "language": "ko"},
        ]
        sorted_opts = apply_preferences(profile, options)
        self.assertEqual(sorted_opts[0]["style"], "blog_seo")

    def test_apply_empty_profile(self):
        """빈 프로필"""
        profile = _create_profile("user1")
        options = [{"style": "a"}, {"style": "b"}]
        sorted_opts = apply_preferences(profile, options)
        self.assertEqual(len(sorted_opts), 2)

    def test_apply_empty_options(self):
        """빈 옵션"""
        profile = _create_profile("user1")
        sorted_opts = apply_preferences(profile, [])
        self.assertEqual(sorted_opts, [])


class TestDecayPreferences(unittest.TestCase):
    """가중치 감쇠 테스트"""

    def test_decay_basic(self):
        """기본 감쇠"""
        profile = _create_profile("user1")
        profile = record_preference(profile, "style", "blog_seo", 1.0)
        profile = decay_preferences(profile, 0.5)
        self.assertAlmostEqual(profile.preferences[0].weight, 0.5)

    def test_decay_removes_near_zero(self):
        """거의 0인 선호 제거"""
        profile = _create_profile("user1")
        profile = record_preference(profile, "style", "blog_seo", 0.01)
        profile = decay_preferences(profile, 0.5)
        self.assertEqual(len(profile.preferences), 0)

    def test_decay_rate_clamped(self):
        """감쇠율 클램핑"""
        profile = _create_profile("user1")
        profile = record_preference(profile, "style", "test", 1.0)
        profile = decay_preferences(profile, 2.0)
        # 1.0으로 클램핑 → weight * (1 - 1.0) = 0 → 제거
        self.assertEqual(len(profile.preferences), 0)

    def test_decay_zero_rate(self):
        """감쇠율 0 — 변화 없음"""
        profile = _create_profile("user1")
        profile = record_preference(profile, "style", "test", 0.8)
        profile = decay_preferences(profile, 0.0)
        self.assertAlmostEqual(profile.preferences[0].weight, 0.8)


class TestExportProfile(unittest.TestCase):
    """프로필 내보내기 테스트"""

    def test_export_basic(self):
        """기본 내보내기"""
        profile = _create_profile("user1")
        profile = record_preference(profile, "style", "blog_seo", 0.9)
        profile = record_preference(profile, "language", "ko", 1.0)
        exported = export_profile(profile)
        self.assertEqual(exported["user_id"], "user1")
        self.assertEqual(exported["total_preferences"], 2)
        self.assertIn("style", exported["categories"])
        self.assertIn("language", exported["categories"])

    def test_export_empty(self):
        """빈 프로필 내보내기"""
        profile = _create_profile("user1")
        exported = export_profile(profile)
        self.assertEqual(exported["total_preferences"], 0)
        self.assertEqual(exported["preferences"], [])

    def test_export_includes_history(self):
        """히스토리 포함"""
        profile = _create_profile("user1")
        profile = record_preference(profile, "style", "test", 0.5)
        exported = export_profile(profile)
        self.assertGreater(len(exported["history"]), 0)


if __name__ == "__main__":
    unittest.main()
