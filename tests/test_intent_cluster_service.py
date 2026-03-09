"""Intent Cluster Service 테스트 — 15개 이상."""

import unittest
from services.intent_cluster_service import (
    IntentCluster,
    mine_intent_clusters,
    _classify_comment,
    _deduplicate_keywords,
    _empty_clusters,
    _ensure_minimum_clusters,
)


class TestClassifyComment(unittest.TestCase):
    """단일 댓글 의도 분류 테스트."""

    def test_question_intent(self):
        intent, kws = _classify_comment("이거 어떻게 하는 건가요?")
        self.assertEqual(intent, "질문")
        self.assertGreater(len(kws), 0)

    def test_praise_intent(self):
        intent, _ = _classify_comment("정말 감사합니다! 최고에요!")
        self.assertEqual(intent, "칭찬/감사")

    def test_complaint_intent(self):
        intent, _ = _classify_comment("실망입니다 문제가 너무 많아요 ㅠㅠ")
        self.assertEqual(intent, "불만/비판")

    def test_request_intent(self):
        intent, _ = _classify_comment("이 기능 추가해주세요 부탁드립니다")
        self.assertEqual(intent, "요청/제안")

    def test_info_sharing_intent(self):
        intent, _ = _classify_comment("참고로 제가 경험해본 결과 이 방법이 더 나았습니다")
        self.assertEqual(intent, "정보 공유")

    def test_agreement_intent(self):
        intent, _ = _classify_comment("맞아요 동의합니다 정말 공감")
        self.assertEqual(intent, "공감/동의")

    def test_humor_intent(self):
        intent, _ = _classify_comment("ㅋㅋㅋㅋㅋ 이건 진짜 웃겨요 ㅋㅋ")
        self.assertEqual(intent, "유머/밈")

    def test_subscribe_intent(self):
        intent, _ = _classify_comment("구독하고 알림 설정 했습니다!")
        self.assertEqual(intent, "구독/팔로우")

    def test_counter_argument_intent(self):
        intent, _ = _classify_comment("그런데 이건 좀 아닌데 반대 의견입니다")
        self.assertEqual(intent, "반론/의문")

    def test_empty_comment(self):
        intent, kws = _classify_comment("")
        self.assertEqual(intent, "기타")
        self.assertEqual(kws, [])

    def test_unclassifiable_goes_to_other(self):
        intent, _ = _classify_comment("가나다라마바사")
        self.assertEqual(intent, "기타")


class TestDeduplicateKeywords(unittest.TestCase):
    """키워드 중복 제거 테스트."""

    def test_removes_duplicates(self):
        result = _deduplicate_keywords(["감사", "감사", "좋아요", "감사"])
        self.assertEqual(result, ["감사", "좋아요"])

    def test_case_insensitive(self):
        result = _deduplicate_keywords(["AI", "ai", "ML"])
        self.assertEqual(len(result), 2)

    def test_max_count(self):
        result = _deduplicate_keywords([f"kw{i}" for i in range(20)], max_count=5)
        self.assertEqual(len(result), 5)

    def test_empty_list(self):
        result = _deduplicate_keywords([])
        self.assertEqual(result, [])


class TestEnsureMinimumClusters(unittest.TestCase):
    """최소 클러스터 보장 테스트."""

    def test_fills_to_minimum(self):
        clusters = [IntentCluster(intent="질문", size=3, proportion=0.3)]
        result = _ensure_minimum_clusters(clusters, min_count=5)
        self.assertGreaterEqual(len(result), 5)

    def test_no_fill_if_enough(self):
        clusters = [
            IntentCluster(intent=f"의도{i}", size=1, proportion=0.1)
            for i in range(7)
        ]
        result = _ensure_minimum_clusters(clusters, min_count=5)
        self.assertEqual(len(result), 7)

    def test_no_duplicate_intents(self):
        clusters = [IntentCluster(intent="질문", size=3)]
        result = _ensure_minimum_clusters(clusters, min_count=5)
        intents = [c.intent for c in result]
        self.assertEqual(len(intents), len(set(intents)))


class TestEmptyClusters(unittest.TestCase):
    """빈 클러스터 생성 테스트."""

    def test_returns_5_clusters(self):
        result = _empty_clusters()
        self.assertEqual(len(result), 5)

    def test_all_zero_size(self):
        for c in _empty_clusters():
            self.assertEqual(c.size, 0)
            self.assertEqual(c.proportion, 0.0)


class TestMineIntentClusters(unittest.TestCase):
    """mine_intent_clusters 통합 테스트."""

    def test_returns_at_least_5(self):
        """최소 5개 클러스터 반환."""
        comments = ["좋아요!", "이거 어떻게 해요?", "실망이에요", "해주세요", "참고로 저는"]
        result = mine_intent_clusters(comments)
        self.assertGreaterEqual(len(result), 5)

    def test_all_clusters_valid(self):
        """모든 클러스터가 유효한 필드를 가진다."""
        comments = ["감사합니다", "질문이요", "별로에요"]
        result = mine_intent_clusters(comments)
        for c in result:
            self.assertIsInstance(c, IntentCluster)
            self.assertTrue(c.intent)
            self.assertIsInstance(c.keywords, list)
            self.assertIsInstance(c.examples, list)
            self.assertGreaterEqual(c.size, 0)
            self.assertGreaterEqual(c.proportion, 0.0)
            self.assertLessEqual(c.proportion, 1.0)

    def test_sorted_by_size_desc(self):
        """size 내림차순 정렬 확인."""
        comments = [
            "감사합니다", "감사해요", "좋아요",  # 칭찬/감사 x3
            "이건 어떻게 하나요?",  # 질문 x1
            "실망이에요",  # 불만 x1
        ]
        result = mine_intent_clusters(comments)
        for i in range(len(result) - 1):
            self.assertGreaterEqual(result[i].size, result[i + 1].size)

    def test_proportion_sums_to_one(self):
        """비율 합이 1.0 (허용 오차 0.01)."""
        comments = ["감사합니다", "질문입니다", "실망이에요", "해주세요", "참고로"]
        result = mine_intent_clusters(comments)
        total_proportion = sum(c.proportion for c in result)
        self.assertAlmostEqual(total_proportion, 1.0, delta=0.01)

    def test_empty_comments(self):
        """빈 목록이면 기본 5개 클러스터 반환."""
        result = mine_intent_clusters([])
        self.assertEqual(len(result), 5)
        for c in result:
            self.assertEqual(c.size, 0)

    def test_none_comments(self):
        """None이면 빈 결과."""
        result = mine_intent_clusters(None)
        self.assertGreaterEqual(len(result), 5)

    def test_whitespace_only_comments(self):
        """공백만 있는 댓글은 무시된다."""
        result = mine_intent_clusters(["   ", "\n", "\t", ""])
        self.assertGreaterEqual(len(result), 5)
        # 모두 size=0이어야 함
        total_size = sum(c.size for c in result)
        self.assertEqual(total_size, 0)

    def test_examples_limited_to_5(self):
        """예시는 최대 5개로 제한된다."""
        comments = [f"감사합니다 {i}번" for i in range(20)]
        result = mine_intent_clusters(comments)
        for c in result:
            self.assertLessEqual(len(c.examples), 5)

    def test_long_comment_truncated_in_example(self):
        """100자 넘는 댓글은 예시에서 잘린다."""
        long_comment = "감사합니다 " * 50  # ~250자
        result = mine_intent_clusters([long_comment])
        for c in result:
            for ex in c.examples:
                self.assertLessEqual(len(ex), 104)  # 100 + "..."

    def test_mixed_languages(self):
        """한국어+영어 혼합 댓글 처리."""
        comments = [
            "Thank you so much! Great video!",
            "How do I do this? Please help.",
            "이거 정말 좋아요 감사합니다",
            "이건 문제가 있네요 실망",
            "참고로 제 경험상 이게 더 낫습니다",
        ]
        result = mine_intent_clusters(comments)
        self.assertGreaterEqual(len(result), 5)
        # 최소 하나의 클러스터에 size > 0
        self.assertTrue(any(c.size > 0 for c in result))

    def test_large_batch(self):
        """100개 댓글도 정상 처리."""
        comments = [f"질문 {i}번: 이거 어떻게 해요?" for i in range(100)]
        result = mine_intent_clusters(comments)
        self.assertGreaterEqual(len(result), 5)
        total_size = sum(c.size for c in result)
        self.assertEqual(total_size, 100)


if __name__ == "__main__":
    unittest.main()
