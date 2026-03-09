"""의미 중복 감시 서비스 테스트."""

import unittest
from services.semantic_dedup_service import (
    DuplicatePair,
    calculate_similarity,
    find_duplicates,
    extract_overlap,
    recommend_action,
)


class TestSemanticDedupService(unittest.TestCase):
    """SemanticDedupService 단위 테스트."""

    def test_calculate_similarity_identical(self):
        """동일 텍스트는 유사도 1.0."""
        sim = calculate_similarity("안녕하세요 반갑습니다", "안녕하세요 반갑습니다")
        self.assertEqual(sim, 1.0)

    def test_calculate_similarity_completely_different(self):
        """완전히 다른 텍스트는 유사도 0.0."""
        sim = calculate_similarity("사과 바나나 포도", "컴퓨터 키보드 마우스")
        self.assertEqual(sim, 0.0)

    def test_calculate_similarity_partial(self):
        """부분 겹침은 0~1 사이."""
        sim = calculate_similarity("사과 바나나 포도 귤", "사과 바나나 수박 멜론")
        self.assertGreater(sim, 0.0)
        self.assertLess(sim, 1.0)

    def test_calculate_similarity_empty_both(self):
        """둘 다 빈 문자열이면 1.0."""
        self.assertEqual(calculate_similarity("", ""), 1.0)

    def test_calculate_similarity_one_empty(self):
        """하나만 빈 문자열이면 0.0."""
        self.assertEqual(calculate_similarity("test", ""), 0.0)
        self.assertEqual(calculate_similarity("", "test"), 0.0)

    def test_extract_overlap_basic(self):
        """겹치는 3-gram을 추출한다."""
        text_a = "오늘 날씨가 매우 좋습니다 산책하기 좋은 날"
        text_b = "오늘 날씨가 매우 좋습니다 운동하기 좋은 날"
        overlaps = extract_overlap(text_a, text_b)
        self.assertTrue(len(overlaps) > 0)

    def test_extract_overlap_no_common(self):
        """공통 3-gram이 없으면 빈 리스트."""
        overlaps = extract_overlap("가 나 다", "라 마 바")
        self.assertEqual(overlaps, [])

    def test_extract_overlap_short_text(self):
        """3단어 미만이면 빈 리스트."""
        overlaps = extract_overlap("가 나", "가 나")
        self.assertEqual(overlaps, [])

    def test_recommend_action_remove(self):
        """>0.9 유사도: remove_one."""
        self.assertEqual(recommend_action(0.95), "remove_one")
        self.assertEqual(recommend_action(0.91), "remove_one")

    def test_recommend_action_merge(self):
        """>0.7 유사도: merge."""
        self.assertEqual(recommend_action(0.75), "merge")
        self.assertEqual(recommend_action(0.8), "merge")

    def test_recommend_action_keep(self):
        """<=0.7 유사도: keep_both."""
        self.assertEqual(recommend_action(0.5), "keep_both")
        self.assertEqual(recommend_action(0.3), "keep_both")
        self.assertEqual(recommend_action(0.7), "keep_both")

    def test_find_duplicates_above_threshold(self):
        """임계값 이상 유사도 쌍을 반환한다."""
        contents = [
            {"id": "a", "text": "사과 바나나 포도 귤 수박"},
            {"id": "b", "text": "사과 바나나 포도 귤 수박"},
            {"id": "c", "text": "컴퓨터 키보드 마우스 모니터 스피커"},
        ]
        pairs = find_duplicates(contents, threshold=0.5)
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0].content_a_id, "a")
        self.assertEqual(pairs[0].content_b_id, "b")

    def test_find_duplicates_no_duplicates(self):
        """중복 없으면 빈 리스트."""
        contents = [
            {"id": "a", "text": "가 나 다"},
            {"id": "b", "text": "라 마 바"},
        ]
        pairs = find_duplicates(contents, threshold=0.5)
        self.assertEqual(pairs, [])

    def test_find_duplicates_empty_list(self):
        """빈 리스트는 빈 결과."""
        self.assertEqual(find_duplicates([], threshold=0.5), [])

    def test_find_duplicates_single_item(self):
        """단일 항목은 쌍 없음."""
        pairs = find_duplicates([{"id": "a", "text": "test"}], threshold=0.5)
        self.assertEqual(pairs, [])

    def test_find_duplicates_returns_duplicate_pair(self):
        """결과가 DuplicatePair 인스턴스다."""
        contents = [
            {"id": "x", "text": "같은 내용 같은 내용"},
            {"id": "y", "text": "같은 내용 같은 내용"},
        ]
        pairs = find_duplicates(contents, threshold=0.1)
        self.assertTrue(len(pairs) > 0)
        self.assertIsInstance(pairs[0], DuplicatePair)

    def test_find_duplicates_includes_recommendation(self):
        """결과에 recommendation이 포함된다."""
        contents = [
            {"id": "a", "text": "동일 텍스트 내용입니다"},
            {"id": "b", "text": "동일 텍스트 내용입니다"},
        ]
        pairs = find_duplicates(contents, threshold=0.5)
        if pairs:
            self.assertIn(pairs[0].recommendation, ["keep_both", "merge", "remove_one"])

    def test_find_duplicates_custom_threshold(self):
        """임계값 조정이 가능하다."""
        contents = [
            {"id": "a", "text": "사과 바나나"},
            {"id": "b", "text": "사과 포도"},
        ]
        # 높은 임계값: 매칭 안 됨
        high = find_duplicates(contents, threshold=0.9)
        self.assertEqual(len(high), 0)

    def test_calculate_similarity_symmetric(self):
        """유사도는 대칭적이다 (A↔B 같은 결과)."""
        sim_ab = calculate_similarity("가 나 다 라", "가 나 마 바")
        sim_ba = calculate_similarity("가 나 마 바", "가 나 다 라")
        self.assertEqual(sim_ab, sim_ba)


if __name__ == "__main__":
    unittest.main()
