"""fan_angle_service 단위 테스트"""
import unittest

from services.fan_angle_service import (
    suggest_fan_angles,
    rank_angles,
    FanAngle,
    _count_keyword_matches,
    _calculate_relevance_score,
)


class TestCountKeywordMatches(unittest.TestCase):
    """키워드 매칭 수 테스트"""

    def test_single_match(self):
        count, matched = _count_keyword_matches("역사를 알아봅시다", ["역사", "미래"])
        self.assertEqual(count, 1)
        self.assertIn("역사", matched)

    def test_multiple_matches(self):
        count, matched = _count_keyword_matches("역사와 미래의 전망", ["역사", "미래", "전망"])
        self.assertEqual(count, 3)

    def test_no_match(self):
        count, matched = _count_keyword_matches("오늘 날씨가 좋습니다", ["역사", "미래"])
        self.assertEqual(count, 0)
        self.assertEqual(matched, [])

    def test_case_insensitive(self):
        """대소문자 무시 (영문 키워드)"""
        count, matched = _count_keyword_matches("VS 비교", ["vs", "비교"])
        self.assertEqual(count, 2)

    def test_empty_text(self):
        count, matched = _count_keyword_matches("", ["역사"])
        self.assertEqual(count, 0)


class TestCalculateRelevanceScore(unittest.TestCase):
    """관련도 점수 계산 테스트"""

    def test_zero_matches(self):
        score = _calculate_relevance_score(0, 5)
        self.assertEqual(score, 0)

    def test_all_matches(self):
        """전체 매칭 시 높은 점수"""
        score = _calculate_relevance_score(5, 5)
        self.assertEqual(score, 100)

    def test_partial_matches(self):
        """부분 매칭 시 중간 점수"""
        score = _calculate_relevance_score(2, 10)
        self.assertGreater(score, 0)
        self.assertLess(score, 100)

    def test_score_range(self):
        """점수가 0~100 범위"""
        for m in range(0, 15):
            score = _calculate_relevance_score(m, 10)
            self.assertGreaterEqual(score, 0)
            self.assertLessEqual(score, 100)

    def test_zero_total(self):
        score = _calculate_relevance_score(0, 0)
        self.assertEqual(score, 0)


class TestSuggestFanAngles(unittest.TestCase):
    """팬 앵글 제안 테스트"""

    def test_empty_content(self):
        """빈 콘텐츠 → 빈 리스트"""
        result = suggest_fan_angles("")
        self.assertEqual(result, [])

    def test_none_content(self):
        result = suggest_fan_angles(None)
        self.assertEqual(result, [])

    def test_timeline_angle(self):
        """역사 키워드 → timeline 각도"""
        result = suggest_fan_angles("이 게임의 역사와 발전 과정을 살펴봅시다")
        types = [a.angle_type for a in result]
        self.assertIn("timeline", types)

    def test_comparison_angle(self):
        """비교 키워드 → comparison 각도"""
        result = suggest_fan_angles("A vs B 비교 분석을 해봅시다")
        types = [a.angle_type for a in result]
        self.assertIn("comparison", types)

    def test_behind_the_scenes_angle(self):
        """촬영/제작 키워드 → behind_the_scenes"""
        result = suggest_fan_angles("이 영화의 촬영 비하인드와 제작 과정")
        types = [a.angle_type for a in result]
        self.assertIn("behind_the_scenes", types)

    def test_deep_dive_angle(self):
        """분석/심층 키워드 → deep_dive"""
        result = suggest_fan_angles("이 주제에 대해 심층 분석을 진행합니다")
        types = [a.angle_type for a in result]
        self.assertIn("deep_dive", types)

    def test_reaction_angle(self):
        """반응/리뷰 키워드 → reaction"""
        result = suggest_fan_angles("시청자 반응과 리뷰를 분석했습니다")
        types = [a.angle_type for a in result]
        self.assertIn("reaction", types)

    def test_theory_angle(self):
        """이론/떡밥 키워드 → theory"""
        result = suggest_fan_angles("숨겨진 의미와 떡밥을 해석해봅시다")
        types = [a.angle_type for a in result]
        self.assertIn("theory", types)

    def test_no_matching_keywords(self):
        """매칭 키워드 없으면 빈 리스트"""
        result = suggest_fan_angles("오늘 점심 메뉴를 정합시다")
        self.assertEqual(result, [])

    def test_comments_add_angles(self):
        """댓글에서 추가 각도 발견"""
        # 본문에는 매칭 없고 댓글에만 있는 키워드
        result_without = suggest_fan_angles("일반적인 내용입니다")
        result_with = suggest_fan_angles(
            "일반적인 내용입니다",
            comments=["역사적 맥락이 궁금합니다", "비교 분석 부탁합니다"]
        )
        self.assertGreaterEqual(len(result_with), len(result_without))

    def test_comments_none_handled(self):
        """comments=None 처리"""
        result = suggest_fan_angles("역사를 알아봅시다", comments=None)
        self.assertGreater(len(result), 0)

    def test_source_keywords_populated(self):
        """source_keywords가 채워지는지 확인"""
        result = suggest_fan_angles("역사와 발전 과정을 살펴봅시다")
        timeline_angles = [a for a in result if a.angle_type == "timeline"]
        self.assertGreater(len(timeline_angles), 0)
        self.assertGreater(len(timeline_angles[0].source_keywords), 0)

    def test_relevance_score_set(self):
        """relevance_score가 0보다 큰지"""
        result = suggest_fan_angles("비하인드 촬영 현장의 제작 과정을 공개합니다")
        for angle in result:
            self.assertGreater(angle.relevance_score, 0)


class TestRankAngles(unittest.TestCase):
    """앵글 정렬 테스트"""

    def test_empty_list(self):
        result = rank_angles([])
        self.assertEqual(result, [])

    def test_sorted_descending(self):
        """높은 점수 우선 정렬"""
        angles = [
            FanAngle(angle_type="a", relevance_score=30),
            FanAngle(angle_type="b", relevance_score=80),
            FanAngle(angle_type="c", relevance_score=50),
        ]
        result = rank_angles(angles)
        self.assertEqual(result[0].angle_type, "b")
        self.assertEqual(result[1].angle_type, "c")
        self.assertEqual(result[2].angle_type, "a")

    def test_single_item(self):
        angles = [FanAngle(angle_type="a", relevance_score=50)]
        result = rank_angles(angles)
        self.assertEqual(len(result), 1)

    def test_equal_scores(self):
        """동점 시 안정 정렬"""
        angles = [
            FanAngle(angle_type="a", relevance_score=50),
            FanAngle(angle_type="b", relevance_score=50),
        ]
        result = rank_angles(angles)
        self.assertEqual(len(result), 2)


if __name__ == '__main__':
    unittest.main()
