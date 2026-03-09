"""실험 학습 루프 서비스 테스트"""
import unittest

from services.experiment_learning_service import (
    ExperimentInput,
    LearningRule,
    learn_from_experiment,
    get_learning_history,
    clear_learning_history,
    _compute_confidence,
    _generate_summary,
    _find_matching_pattern,
)


class TestExperimentInput(unittest.TestCase):
    """ExperimentInput 데이터 모델 테스트"""

    def test_dataclass_fields(self):
        """모든 필드가 올바르게 할당됨"""
        inp = ExperimentInput(
            experiment_id="exp-001",
            variant_a="짧은 제목",
            variant_b="긴 설명형 제목",
            winner="a",
            metric="ctr",
            improvement=0.15,
        )
        self.assertEqual(inp.experiment_id, "exp-001")
        self.assertEqual(inp.winner, "a")
        self.assertAlmostEqual(inp.improvement, 0.15)


class TestLearningRule(unittest.TestCase):
    """LearningRule 데이터 모델 테스트"""

    def test_default_fields(self):
        """기본값이 올바르게 설정됨"""
        rule = LearningRule(
            rule_id="rule-test",
            pattern="테스트 패턴",
            recommendation="테스트 권장",
            confidence=0.8,
        )
        self.assertEqual(rule.source_experiments, [])
        self.assertIsInstance(rule.created_at, str)


class TestComputeConfidence(unittest.TestCase):
    """신뢰도 산출 테스트"""

    def test_high_improvement(self):
        """30%+ 개선 → 0.95"""
        self.assertEqual(_compute_confidence(0.35), 0.95)

    def test_medium_improvement(self):
        """15~29% 개선 → 0.80"""
        self.assertEqual(_compute_confidence(0.20), 0.80)

    def test_low_improvement(self):
        """5~14% 개선 → 0.60"""
        self.assertEqual(_compute_confidence(0.08), 0.60)

    def test_minimal_improvement(self):
        """5% 미만 → 0.40"""
        self.assertEqual(_compute_confidence(0.02), 0.40)

    def test_zero_improvement(self):
        """0% 개선 → 0.40"""
        self.assertEqual(_compute_confidence(0.0), 0.40)

    def test_clamp_above_one(self):
        """1 초과 값은 1.0으로 클램프 → 0.95"""
        self.assertEqual(_compute_confidence(1.5), 0.95)

    def test_clamp_below_zero(self):
        """음수 값은 0.0으로 클램프 → 0.40"""
        self.assertEqual(_compute_confidence(-0.1), 0.40)


class TestGenerateSummary(unittest.TestCase):
    """자연어 요약 생성 테스트"""

    def test_winner_a_summary(self):
        """변형 A 승리 시 자연어 요약"""
        exp = ExperimentInput(
            experiment_id="exp-001",
            variant_a="짧은 제목",
            variant_b="긴 제목",
            winner="a",
            metric="ctr",
            improvement=0.15,
        )
        summary = _generate_summary(exp)
        self.assertIn("변형 A", summary)
        self.assertIn("짧은 제목", summary)
        self.assertIn("15.0%", summary)
        self.assertIn("ctr", summary)

    def test_winner_b_summary(self):
        """변형 B 승리 시 자연어 요약"""
        exp = ExperimentInput(
            experiment_id="exp-002",
            variant_a="A 버전",
            variant_b="B 버전",
            winner="b",
            metric="engagement",
            improvement=0.42,
        )
        summary = _generate_summary(exp)
        self.assertIn("변형 B", summary)
        self.assertIn("B 버전", summary)
        self.assertIn("42.0%", summary)


class TestFindMatchingPattern(unittest.TestCase):
    """메트릭별 패턴 매칭 테스트"""

    def test_known_metric_ctr(self):
        """등록된 메트릭 → 패턴 반환"""
        pattern = _find_matching_pattern("ctr")
        self.assertIn("클릭률", pattern["pattern"])

    def test_known_metric_engagement(self):
        """engagement 메트릭 → 참여율 패턴"""
        pattern = _find_matching_pattern("engagement")
        self.assertIn("참여율", pattern["pattern"])

    def test_unknown_metric(self):
        """미등록 메트릭 → 범용 패턴"""
        pattern = _find_matching_pattern("unknown_metric")
        self.assertIn("unknown_metric", pattern["pattern"])


class TestLearnFromExperiment(unittest.TestCase):
    """learn_from_experiment 통합 테스트"""

    def setUp(self):
        """각 테스트 전 저장소 초기화"""
        clear_learning_history()

    def test_valid_experiment_returns_rule(self):
        """유효한 실험 → LearningRule 반환"""
        result = learn_from_experiment({
            "experiment_id": "exp-100",
            "variant_a": "제목 A",
            "variant_b": "제목 B",
            "winner": "a",
            "metric": "ctr",
            "improvement": 0.25,
        })
        self.assertIsInstance(result, LearningRule)
        self.assertIn("exp-100", result.source_experiments)
        self.assertEqual(result.confidence, 0.80)

    def test_missing_field_raises(self):
        """필수 필드 누락 → ValueError"""
        with self.assertRaises(ValueError) as ctx:
            learn_from_experiment({"experiment_id": "exp-1"})
        self.assertIn("필수 필드 누락", str(ctx.exception))

    def test_invalid_winner_raises(self):
        """잘못된 winner 값 → ValueError"""
        with self.assertRaises(ValueError) as ctx:
            learn_from_experiment({
                "experiment_id": "exp-1",
                "variant_a": "A",
                "variant_b": "B",
                "winner": "c",
                "metric": "ctr",
                "improvement": 0.1,
            })
        self.assertIn("'a' 또는 'b'", str(ctx.exception))

    def test_invalid_improvement_range(self):
        """improvement 범위 초과 → ValueError"""
        with self.assertRaises(ValueError):
            learn_from_experiment({
                "experiment_id": "exp-1",
                "variant_a": "A",
                "variant_b": "B",
                "winner": "a",
                "metric": "ctr",
                "improvement": 1.5,
            })

    def test_invalid_improvement_type(self):
        """improvement 타입 오류 → ValueError"""
        with self.assertRaises(ValueError):
            learn_from_experiment({
                "experiment_id": "exp-1",
                "variant_a": "A",
                "variant_b": "B",
                "winner": "a",
                "metric": "ctr",
                "improvement": "high",
            })

    def test_recommendation_contains_summary(self):
        """권장 사항에 자연어 요약이 포함됨"""
        rule = learn_from_experiment({
            "experiment_id": "exp-200",
            "variant_a": "간결한 제목",
            "variant_b": "상세한 설명 제목",
            "winner": "b",
            "metric": "conversion",
            "improvement": 0.30,
        })
        self.assertIn("간결한 제목", rule.recommendation)
        self.assertIn("30.0%", rule.recommendation)

    def test_duplicate_merge(self):
        """동일 메트릭 실험 반복 시 기존 규칙에 병합"""
        learn_from_experiment({
            "experiment_id": "exp-a",
            "variant_a": "A1",
            "variant_b": "B1",
            "winner": "a",
            "metric": "ctr",
            "improvement": 0.10,
        })
        rule = learn_from_experiment({
            "experiment_id": "exp-b",
            "variant_a": "A2",
            "variant_b": "B2",
            "winner": "b",
            "metric": "ctr",
            "improvement": 0.20,
        })
        self.assertIn("exp-a", rule.source_experiments)
        self.assertIn("exp-b", rule.source_experiments)
        # 저장소에 규칙은 1개만
        self.assertEqual(len(get_learning_history()), 1)

    def test_different_metrics_separate_rules(self):
        """다른 메트릭의 실험은 별도 규칙으로 저장"""
        learn_from_experiment({
            "experiment_id": "exp-ctr",
            "variant_a": "A",
            "variant_b": "B",
            "winner": "a",
            "metric": "ctr",
            "improvement": 0.1,
        })
        learn_from_experiment({
            "experiment_id": "exp-eng",
            "variant_a": "A",
            "variant_b": "B",
            "winner": "b",
            "metric": "engagement",
            "improvement": 0.2,
        })
        self.assertEqual(len(get_learning_history()), 2)


class TestGetLearningHistory(unittest.TestCase):
    """학습 히스토리 조회 테스트"""

    def setUp(self):
        clear_learning_history()

    def test_empty_history(self):
        """빈 히스토리 → 빈 리스트"""
        self.assertEqual(get_learning_history(), [])

    def test_sorted_by_confidence_desc(self):
        """신뢰도 내림차순 정렬"""
        learn_from_experiment({
            "experiment_id": "low",
            "variant_a": "A",
            "variant_b": "B",
            "winner": "a",
            "metric": "retention",
            "improvement": 0.02,  # 낮은 신뢰도
        })
        learn_from_experiment({
            "experiment_id": "high",
            "variant_a": "A",
            "variant_b": "B",
            "winner": "a",
            "metric": "ctr",
            "improvement": 0.50,  # 높은 신뢰도
        })
        history = get_learning_history()
        self.assertEqual(len(history), 2)
        self.assertGreaterEqual(history[0].confidence, history[1].confidence)


class TestClearLearningHistory(unittest.TestCase):
    """저장소 초기화 테스트"""

    def test_clear_returns_count(self):
        """삭제된 규칙 수 반환"""
        clear_learning_history()
        learn_from_experiment({
            "experiment_id": "exp-1",
            "variant_a": "A",
            "variant_b": "B",
            "winner": "a",
            "metric": "ctr",
            "improvement": 0.1,
        })
        count = clear_learning_history()
        self.assertEqual(count, 1)
        self.assertEqual(len(get_learning_history()), 0)

    def test_clear_empty_store(self):
        """빈 저장소 초기화 → 0 반환"""
        clear_learning_history()
        self.assertEqual(clear_learning_history(), 0)


if __name__ == "__main__":
    unittest.main()
