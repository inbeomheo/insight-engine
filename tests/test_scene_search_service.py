"""
자연어 장면 검색 서비스 테스트

services/scene_search_service.py의 search_scenes 및
내부 헬퍼 함수들을 검증합니다.
"""
import unittest

from services.scene_search_service import (
    SceneResult,
    DEFAULT_SCENE_DURATION,
    search_scenes,
    _format_timestamp,
    _split_sentences,
    _extract_query_keywords,
    _calculate_relevance,
    _estimate_duration,
)


class TestFormatTimestamp(unittest.TestCase):
    """_format_timestamp 함수 테스트."""

    def test_zero(self):
        self.assertEqual(_format_timestamp(0), "00:00")

    def test_mixed(self):
        self.assertEqual(_format_timestamp(75), "01:15")


class TestSplitSentences(unittest.TestCase):
    """_split_sentences 함수 테스트."""

    def test_empty(self):
        self.assertEqual(_split_sentences(""), [])

    def test_exclamation_split(self):
        result = _split_sentences("놀라운 발견!정말 신기하죠!끝")
        self.assertEqual(len(result), 3)


class TestExtractQueryKeywords(unittest.TestCase):
    """_extract_query_keywords 함수 테스트."""

    def test_removes_stopwords(self):
        """불용어가 제거됩니다."""
        keywords = _extract_query_keywords("파이썬 코드 보여 주세요")
        self.assertIn("파이썬", keywords)
        self.assertIn("코드", keywords)
        self.assertNotIn("보여", keywords)
        self.assertNotIn("주세요", keywords)

    def test_removes_short_words(self):
        """1글자 단어가 제거됩니다."""
        keywords = _extract_query_keywords("a 파이썬 b")
        self.assertNotIn("a", keywords)
        self.assertNotIn("b", keywords)

    def test_empty_query(self):
        self.assertEqual(_extract_query_keywords(""), [])


class TestCalculateRelevance(unittest.TestCase):
    """_calculate_relevance 함수 테스트."""

    def test_full_match(self):
        score = _calculate_relevance("파이썬 코딩", ["파이썬", "코딩"])
        self.assertEqual(score, 1.0)

    def test_no_match(self):
        score = _calculate_relevance("날씨 정보", ["파이썬"])
        self.assertEqual(score, 0.0)

    def test_empty_keywords(self):
        self.assertEqual(_calculate_relevance("문장", []), 0.0)


class TestEstimateDuration(unittest.TestCase):
    """_estimate_duration 함수 테스트."""

    def test_short_sentence(self):
        """짧은 문장은 10초입니다."""
        duration = _estimate_duration("짧은 문장")
        self.assertEqual(duration, 10)

    def test_medium_sentence(self):
        """중간 길이 문장은 기본 장면 길이입니다."""
        sentence = "이것은 적당한 길이의 중간 문장입니다 여러 단어 포함"
        duration = _estimate_duration(sentence)
        self.assertEqual(duration, DEFAULT_SCENE_DURATION)

    def test_long_sentence_capped(self):
        """긴 문장은 최대 30초로 제한됩니다."""
        sentence = "매우 긴 문장 " * 30
        duration = _estimate_duration(sentence)
        self.assertLessEqual(duration, 30)


class TestSearchScenes(unittest.TestCase):
    """search_scenes 함수 테스트."""

    def test_empty_transcript_returns_empty(self):
        """빈 자막이면 빈 리스트를 반환합니다."""
        result = search_scenes("vid1", "파이썬", transcript="")
        self.assertEqual(result, [])

    def test_none_transcript_returns_empty(self):
        """None 자막이면 빈 리스트를 반환합니다."""
        result = search_scenes("vid1", "파이썬")
        self.assertEqual(result, [])

    def test_empty_query_returns_empty(self):
        """빈 쿼리이면 빈 리스트를 반환합니다."""
        result = search_scenes("vid1", "", transcript="파이썬 강의")
        self.assertEqual(result, [])

    def test_matching_scenes_returned(self):
        """매칭되는 장면이 반환됩니다."""
        transcript = "파이썬 설치 방법\n자바 환경 설정\n파이썬 코딩 시작"
        result = search_scenes("vid1", "파이썬 코딩", transcript=transcript)
        self.assertTrue(len(result) >= 1)

    def test_result_type(self):
        """반환값이 SceneResult 인스턴스입니다."""
        transcript = "파이썬 프로그래밍"
        result = search_scenes("vid1", "파이썬", transcript=transcript)
        self.assertTrue(all(isinstance(s, SceneResult) for s in result))

    def test_results_sorted_by_relevance(self):
        """결과가 관련도 내림차순으로 정렬됩니다."""
        transcript = "파이썬 기초\n자바 입문\n파이썬 자바 비교"
        result = search_scenes("vid1", "파이썬 자바", transcript=transcript)
        if len(result) >= 2:
            for i in range(len(result) - 1):
                self.assertGreaterEqual(
                    result[i].relevance_score,
                    result[i + 1].relevance_score,
                )

    def test_low_relevance_filtered(self):
        """관련도 0.3 미만인 장면은 제외됩니다."""
        transcript = "파이썬 튜토리얼"
        result = search_scenes(
            "vid1", "파이썬 자바 루비 고랭", transcript=transcript
        )
        for scene in result:
            self.assertGreaterEqual(scene.relevance_score, 0.3)

    def test_video_id_propagated(self):
        """video_id가 결과에 정확히 전달됩니다."""
        transcript = "파이썬 강의"
        result = search_scenes("my_video", "파이썬", transcript=transcript)
        for scene in result:
            self.assertEqual(scene.video_id, "my_video")

    def test_scene_id_unique(self):
        """각 장면의 scene_id가 고유합니다."""
        transcript = "파이썬 기초\n파이썬 중급\n파이썬 고급"
        result = search_scenes("vid1", "파이썬", transcript=transcript)
        ids = [s.scene_id for s in result]
        self.assertEqual(len(ids), len(set(ids)))

    def test_timestamp_format(self):
        """타임스탬프가 MM:SS 형식입니다."""
        import re
        transcript = "파이썬 튜토리얼"
        result = search_scenes("vid1", "파이썬", transcript=transcript)
        for scene in result:
            self.assertRegex(scene.timestamp, r'^\d{2}:\d{2}$')

    def test_duration_positive(self):
        """장면 길이가 양수입니다."""
        transcript = "파이썬 프로그래밍 시작"
        result = search_scenes("vid1", "파이썬", transcript=transcript)
        for scene in result:
            self.assertGreater(scene.duration_seconds, 0)

    def test_no_match_returns_empty(self):
        """매칭 키워드 없으면 빈 리스트를 반환합니다."""
        transcript = "오늘 날씨가 좋습니다\n내일도 맑겠습니다"
        result = search_scenes("vid1", "파이썬 자바", transcript=transcript)
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
