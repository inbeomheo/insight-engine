"""content_lifespan_service 단위 테스트"""
import unittest

from services.content_lifespan_service import (
    LifespanPrediction,
    predict_lifespan,
    _estimate_base_lifespan,
    _apply_quality_modifiers,
    _calculate_decay_rate,
)


class TestEstimateBaseLifespan(unittest.TestCase):
    """기본 수명 추정 테스트"""

    def test_blog_type(self):
        self.assertEqual(_estimate_base_lifespan({"type": "blog"}), 365)

    def test_sns_type(self):
        self.assertEqual(_estimate_base_lifespan({"type": "sns"}), 3)

    def test_unknown_type_default(self):
        self.assertEqual(_estimate_base_lifespan({"type": "podcast"}), 90)

    def test_case_insensitive(self):
        self.assertEqual(_estimate_base_lifespan({"type": "VIDEO"}), 180)


class TestApplyQualityModifiers(unittest.TestCase):
    """품질 보정 테스트"""

    def test_seo_optimized_increases(self):
        days, factors = _apply_quality_modifiers(100, ["seo_optimized"])
        self.assertEqual(days, 150)  # 100 * 1.5
        self.assertTrue(len(factors) > 0)

    def test_trending_topic_decreases(self):
        days, factors = _apply_quality_modifiers(100, ["trending_topic"])
        self.assertEqual(days, 60)  # 100 * 0.6

    def test_multiple_modifiers(self):
        days, factors = _apply_quality_modifiers(100, ["seo_optimized", "high_engagement"])
        self.assertEqual(days, 195)  # 100 * 1.5 * 1.3 = 195
        self.assertEqual(len(factors), 2)

    def test_unknown_quality_ignored(self):
        days, factors = _apply_quality_modifiers(100, ["unknown_quality"])
        self.assertEqual(days, 100)
        self.assertEqual(len(factors), 0)


class TestCalculateDecayRate(unittest.TestCase):
    """감쇠율 계산 테스트"""

    def test_positive_days(self):
        rate = _calculate_decay_rate(365)
        self.assertGreater(rate, 0)
        self.assertLess(rate, 1)

    def test_zero_days(self):
        self.assertEqual(_calculate_decay_rate(0), 1.0)

    def test_short_lifespan_higher_rate(self):
        short = _calculate_decay_rate(3)
        long = _calculate_decay_rate(365)
        self.assertGreater(short, long)


class TestPredictLifespan(unittest.TestCase):
    """메인 함수 테스트"""

    def test_empty_content(self):
        result = predict_lifespan({})
        self.assertIsInstance(result, LifespanPrediction)

    def test_blog_prediction(self):
        content = {
            "content_id": "blog_1",
            "type": "blog",
            "qualities": ["seo_optimized"],
            "published_date": "2026-01-01",
        }
        result = predict_lifespan(content)
        self.assertEqual(result.content_id, "blog_1")
        self.assertGreater(result.predicted_days, 365)  # SEO 보정으로 증가
        self.assertGreater(result.decay_rate, 0)

    def test_sns_short_lifespan(self):
        content = {"content_id": "sns_1", "type": "sns"}
        result = predict_lifespan(content)
        self.assertLessEqual(result.predicted_days, 10)

    def test_peak_date_format(self):
        content = {
            "content_id": "test",
            "type": "blog",
            "published_date": "2026-03-01",
        }
        result = predict_lifespan(content)
        # YYYY-MM-DD 형식
        self.assertRegex(result.peak_date, r'^\d{4}-\d{2}-\d{2}$')

    def test_factors_include_type(self):
        content = {"content_id": "test", "type": "video"}
        result = predict_lifespan(content)
        self.assertTrue(any("video" in f for f in result.factors))

    def test_evergreen_longest(self):
        content = {"content_id": "eg", "type": "evergreen", "qualities": ["updated_regularly"]}
        result = predict_lifespan(content)
        self.assertGreater(result.predicted_days, 1000)

    def test_default_content_id(self):
        result = predict_lifespan({"type": "blog"})
        self.assertEqual(result.content_id, "unknown")

    def test_dataclass_fields(self):
        pred = LifespanPrediction(
            content_id="test", predicted_days=100,
            decay_rate=0.023, peak_date="2026-01-20",
            factors=["SEO"],
        )
        self.assertEqual(pred.content_id, "test")
        self.assertEqual(len(pred.factors), 1)


if __name__ == '__main__':
    unittest.main()
