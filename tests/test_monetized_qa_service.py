"""수익형 Q&A 서비스 테스트"""

import unittest
from services.monetized_qa_service import (
    QAItem, QACatalog,
    create_qa, filter_by_tier, calculate_revenue, get_popular, preview_answer,
)


class TestMonetizedQAService(unittest.TestCase):
    """수익형 Q&A 서비스 테스트"""

    def _make_catalog(self, items=None):
        return QACatalog(catalog_id="cat1", items=items or [])

    def test_create_qa_free(self):
        """무료 Q&A 생성"""
        qa = create_qa("질문?", "답변입니다.", "free")
        self.assertEqual(qa.tier, "free")
        self.assertEqual(qa.price, 0.0)

    def test_create_qa_premium(self):
        """프리미엄 Q&A 생성"""
        qa = create_qa("질문?", "답변", "premium", 5000.0)
        self.assertEqual(qa.tier, "premium")
        self.assertEqual(qa.price, 5000.0)

    def test_create_qa_free_forces_zero_price(self):
        """무료 티어는 가격 0으로 강제"""
        qa = create_qa("질문?", "답변", "free", 100.0)
        self.assertEqual(qa.price, 0.0)

    def test_create_qa_invalid_tier(self):
        """유효하지 않은 티어 거부"""
        with self.assertRaises(ValueError):
            create_qa("질문?", "답변", "gold")

    def test_create_qa_negative_price(self):
        """음수 가격 거부"""
        with self.assertRaises(ValueError):
            create_qa("질문?", "답변", "premium", -100)

    def test_create_qa_empty_question(self):
        """빈 질문 거부"""
        with self.assertRaises(ValueError):
            create_qa("  ", "답변")

    def test_filter_by_tier(self):
        """티어별 필터링"""
        items = [
            create_qa("Q1", "A1", "free"),
            create_qa("Q2", "A2", "premium", 100),
            create_qa("Q3", "A3", "free"),
        ]
        catalog = self._make_catalog(items)
        free_items = filter_by_tier(catalog, "free")
        self.assertEqual(len(free_items), 2)

    def test_calculate_revenue(self):
        """총 매출 계산"""
        qa1 = create_qa("Q1", "A1", "premium", 100)
        qa1.purchases = 5
        qa2 = create_qa("Q2", "A2", "exclusive", 200)
        qa2.purchases = 3
        catalog = self._make_catalog([qa1, qa2])
        revenue = calculate_revenue(catalog)
        self.assertEqual(revenue, 1100.0)  # 500 + 600

    def test_calculate_revenue_empty(self):
        """빈 카탈로그 매출"""
        catalog = self._make_catalog()
        self.assertEqual(calculate_revenue(catalog), 0.0)

    def test_get_popular(self):
        """조회수 기반 인기 Q&A"""
        qa1 = create_qa("Q1", "A1", "free")
        qa1.views = 100
        qa2 = create_qa("Q2", "A2", "free")
        qa2.views = 500
        qa3 = create_qa("Q3", "A3", "free")
        qa3.views = 300
        catalog = self._make_catalog([qa1, qa2, qa3])
        popular = get_popular(catalog, 2)
        self.assertEqual(len(popular), 2)
        self.assertEqual(popular[0].views, 500)

    def test_preview_answer_free(self):
        """무료 티어는 전체 답변"""
        qa = create_qa("Q", "이것은 전체 답변입니다", "free")
        self.assertEqual(preview_answer(qa), "이것은 전체 답변입니다")

    def test_preview_answer_premium_short(self):
        """프리미엄 짧은 답변은 전체"""
        qa = create_qa("Q", "짧은 답", "premium", 100)
        self.assertEqual(preview_answer(qa, 50), "짧은 답")

    def test_preview_answer_premium_long(self):
        """프리미엄 긴 답변은 미리보기"""
        qa = create_qa("Q", "A" * 100, "premium", 100)
        preview = preview_answer(qa, 20)
        self.assertEqual(len(preview), 23)  # 20 + "..."
        self.assertTrue(preview.endswith("..."))

    def test_get_popular_top_k_exceeds(self):
        """top_k가 전체보다 크면 전체 반환"""
        qa = create_qa("Q1", "A1", "free")
        catalog = self._make_catalog([qa])
        popular = get_popular(catalog, 10)
        self.assertEqual(len(popular), 1)


if __name__ == "__main__":
    unittest.main()
