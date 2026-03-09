"""review_matrix_service 단위 테스트"""
import unittest

from services.review_matrix_service import (
    ComparisonTable,
    create_comparison_matrix,
    comparison_table_to_dict,
    _group_by_product,
    _extract_criteria,
    _determine_winner,
    _avg_rating,
)


class TestCreateComparisonMatrix(unittest.TestCase):
    """create_comparison_matrix 함수 테스트"""

    def test_empty_reviews_raises(self):
        """빈 리뷰 리스트는 ValueError 발생"""
        with self.assertRaises(ValueError):
            create_comparison_matrix([])

    def test_no_valid_reviews_raises(self):
        """유효한 리뷰가 없으면 ValueError 발생"""
        with self.assertRaises(ValueError):
            create_comparison_matrix([{"product": "", "text": ""}])

    def test_missing_text_raises(self):
        """text 필드 없는 리뷰만 있으면 ValueError"""
        with self.assertRaises(ValueError):
            create_comparison_matrix([{"product": "A제품"}])

    def test_single_product_comparison(self):
        """단일 제품 리뷰 — ComparisonTable 반환"""
        reviews = [
            {"product": "노트북A", "text": "품질이 좋고 가격도 적당합니다", "rating": 4.5},
            {"product": "노트북A", "text": "디자인이 예쁘고 사용하기 편리합니다", "rating": 4.0},
        ]
        result = create_comparison_matrix(reviews)

        self.assertIsInstance(result, ComparisonTable)
        self.assertEqual(result.products, ["노트북A"])
        self.assertEqual(result.winner, "노트북A")
        self.assertIn("노트북A", result.ratings)
        self.assertTrue(len(result.criteria) >= 3)

    def test_multi_product_comparison(self):
        """다수 제품 비교 — 우승자 결정"""
        reviews = [
            {"product": "A", "text": "품질 최고! 가격도 좋고 성능 훌륭합니다", "rating": 4.8},
            {"product": "A", "text": "디자인 우수하고 편리합니다", "rating": 4.5},
            {"product": "B", "text": "품질 별로이고 가격이 비쌉니다", "rating": 2.0},
            {"product": "B", "text": "디자인은 괜찮지만 불편합니다", "rating": 2.5},
        ]
        result = create_comparison_matrix(reviews)

        self.assertEqual(len(result.products), 2)
        self.assertIn("A", result.products)
        self.assertIn("B", result.products)
        # A가 평점이 높으므로 우승
        self.assertEqual(result.winner, "A")

    def test_ratings_in_valid_range(self):
        """모든 점수가 0.0~5.0 범위 내"""
        reviews = [
            {"product": "X", "text": "최고 최고 최고 좋아 좋아 좋아 추천 추천", "rating": 5.0},
            {"product": "Y", "text": "나쁘고 별로 불만 실망 고장 느리다 불편 부족", "rating": 1.0},
        ]
        result = create_comparison_matrix(reviews)

        for product in result.products:
            for criterion, score in result.ratings[product].items():
                self.assertGreaterEqual(score, 0.0, f"{product}/{criterion} 범위 초과")
                self.assertLessEqual(score, 5.0, f"{product}/{criterion} 범위 초과")

    def test_summary_contains_products(self):
        """요약에 제품명이 포함되어야 함"""
        reviews = [
            {"product": "갤럭시", "text": "사용성 좋고 품질 훌륭합니다", "rating": 4.0},
            {"product": "아이폰", "text": "디자인 예쁘고 성능 빠릅니다", "rating": 4.5},
        ]
        result = create_comparison_matrix(reviews)
        self.assertIn("갤럭시", result.summary)
        self.assertIn("아이폰", result.summary)

    def test_rating_without_explicit_score(self):
        """rating 필드 없는 리뷰 — 기본 3.0 사용"""
        reviews = [
            {"product": "제품A", "text": "품질 관련 리뷰입니다. 가격이 적당합니다."},
        ]
        result = create_comparison_matrix(reviews)
        self.assertIsInstance(result, ComparisonTable)
        # 기본 점수 3.0 기반이므로 극단값이 아닌지 확인
        for score in result.ratings["제품A"].values():
            self.assertGreater(score, 0.0)


class TestGroupByProduct(unittest.TestCase):
    """_group_by_product 함수 테스트"""

    def test_grouping(self):
        """제품별 그룹핑 동작 확인"""
        reviews = [
            {"product": "A", "text": "리뷰1"},
            {"product": "B", "text": "리뷰2"},
            {"product": "A", "text": "리뷰3"},
        ]
        groups = _group_by_product(reviews)
        self.assertEqual(len(groups), 2)
        self.assertEqual(len(groups["A"]), 2)
        self.assertEqual(len(groups["B"]), 1)


class TestExtractCriteria(unittest.TestCase):
    """_extract_criteria 함수 테스트"""

    def test_criteria_from_keywords(self):
        """리뷰 텍스트에서 기준 추출"""
        reviews = [
            {"text": "품질이 좋고 가격이 저렴합니다"},
            {"text": "디자인이 예쁘고 사용하기 편리합니다"},
        ]
        criteria = _extract_criteria(reviews)
        self.assertIn("품질", criteria)
        self.assertIn("가격", criteria)
        self.assertIn("디자인", criteria)

    def test_minimum_3_criteria(self):
        """최소 3개 기준 보장"""
        reviews = [{"text": "그냥 괜찮습니다"}]  # 키워드 없음
        criteria = _extract_criteria(reviews)
        self.assertGreaterEqual(len(criteria), 3)


class TestDetermineWinner(unittest.TestCase):
    """_determine_winner 함수 테스트"""

    def test_highest_avg_wins(self):
        """평균 점수 최고 제품이 우승"""
        ratings = {
            "A": {"품질": 4.0, "가격": 3.5},
            "B": {"품질": 5.0, "가격": 4.5},
        }
        winner = _determine_winner(ratings, ["A", "B"])
        self.assertEqual(winner, "B")


class TestAvgRating(unittest.TestCase):
    """_avg_rating 함수 테스트"""

    def test_valid_ratings(self):
        """유효한 평점들의 평균"""
        reviews = [{"rating": 4.0}, {"rating": 5.0}]
        self.assertEqual(_avg_rating(reviews), 4.5)

    def test_no_ratings_returns_default(self):
        """평점 없는 리뷰 — 기본값 3.0"""
        reviews = [{"text": "리뷰"}, {"text": "리뷰2"}]
        self.assertEqual(_avg_rating(reviews), 3.0)

    def test_invalid_ratings_ignored(self):
        """유효하지 않은 평점은 무시"""
        reviews = [{"rating": "invalid"}, {"rating": 4.0}]
        self.assertEqual(_avg_rating(reviews), 4.0)


class TestComparisonTableToDict(unittest.TestCase):
    """직렬화 테스트"""

    def test_to_dict(self):
        """ComparisonTable → dict 변환"""
        table = ComparisonTable(
            products=["A"],
            criteria=["품질"],
            ratings={"A": {"품질": 4.0}},
            winner="A",
            summary="요약",
        )
        result = comparison_table_to_dict(table)
        self.assertIsInstance(result, dict)
        self.assertEqual(result["winner"], "A")
        self.assertEqual(result["products"], ["A"])


if __name__ == '__main__':
    unittest.main()
