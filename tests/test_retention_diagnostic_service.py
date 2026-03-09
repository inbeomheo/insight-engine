"""
RetentionDiagnosticService 단위 테스트 (T12.4)
"""
import unittest
from services.retention_diagnostic_service import (
    diagnose_retention,
    RetentionDiagnosis,
    DropPoint,
    _parse_time_to_seconds,
    _calculate_grade,
    _infer_cause,
    DROP_THRESHOLD,
)


class TestParseTimeToSeconds(unittest.TestCase):
    """시간 파싱 테스트"""

    def test_mm_ss(self):
        self.assertEqual(_parse_time_to_seconds("01:30"), 90.0)

    def test_hh_mm_ss(self):
        self.assertEqual(_parse_time_to_seconds("1:02:30"), 3750.0)

    def test_zero(self):
        self.assertEqual(_parse_time_to_seconds("00:00"), 0.0)

    def test_just_minutes(self):
        self.assertEqual(_parse_time_to_seconds("05:00"), 300.0)


class TestCalculateGrade(unittest.TestCase):
    """등급 계산 테스트"""

    def test_grade_s(self):
        self.assertEqual(_calculate_grade(90.0), 'S')

    def test_grade_a(self):
        self.assertEqual(_calculate_grade(70.0), 'A')

    def test_grade_b(self):
        self.assertEqual(_calculate_grade(55.0), 'B')

    def test_grade_c(self):
        self.assertEqual(_calculate_grade(40.0), 'C')

    def test_grade_d(self):
        self.assertEqual(_calculate_grade(20.0), 'D')

    def test_grade_boundary_s(self):
        self.assertEqual(_calculate_grade(80.0), 'S')

    def test_grade_boundary_a(self):
        self.assertEqual(_calculate_grade(65.0), 'A')


class TestInferCause(unittest.TestCase):
    """원인 추정 테스트"""

    def test_intro_too_long(self):
        cause = _infer_cause("00:30", 600.0, 15.0, 1, 10)
        self.assertEqual(cause, 'intro_too_long')

    def test_abrupt_ending(self):
        cause = _infer_cause("09:30", 600.0, 15.0, 9, 10)
        self.assertEqual(cause, 'abrupt_ending')

    def test_content_shift(self):
        """20%+ 급락 → content_shift"""
        cause = _infer_cause("05:00", 600.0, 25.0, 5, 10)
        self.assertEqual(cause, 'content_shift')

    def test_boring_section(self):
        """일반적인 급락 → boring_section"""
        cause = _infer_cause("03:00", 600.0, 12.0, 3, 10)
        self.assertEqual(cause, 'boring_section')


class TestDiagnoseRetention(unittest.TestCase):
    """유지율 진단 통합 테스트"""

    def _make_episode(self, curve):
        return {"episode_id": "ep-001", "retention_curve": curve}

    def test_basic_diagnosis(self):
        """기본 진단 생성"""
        curve = [
            {"time": "00:00", "retention": 100},
            {"time": "01:00", "retention": 90},
            {"time": "02:00", "retention": 80},
            {"time": "03:00", "retention": 70},
        ]
        result = diagnose_retention(self._make_episode(curve))
        self.assertIsInstance(result, RetentionDiagnosis)
        self.assertEqual(result.episode_id, "ep-001")
        self.assertGreater(result.avg_retention, 0)

    def test_detects_drop_point(self):
        """10%+ 급락 감지"""
        curve = [
            {"time": "00:00", "retention": 100},
            {"time": "01:00", "retention": 95},
            {"time": "02:00", "retention": 80},  # -15% 급락
            {"time": "03:00", "retention": 75},
        ]
        result = diagnose_retention(self._make_episode(curve))
        self.assertGreaterEqual(len(result.drop_points), 1)
        drop = result.drop_points[0]
        self.assertIsInstance(drop, DropPoint)
        self.assertGreaterEqual(drop.drop_amount, DROP_THRESHOLD)

    def test_no_drop_when_gradual(self):
        """점진적 감소 → 급락 없음"""
        curve = [
            {"time": "00:00", "retention": 100},
            {"time": "01:00", "retention": 95},
            {"time": "02:00", "retention": 90},
            {"time": "03:00", "retention": 85},
        ]
        result = diagnose_retention(self._make_episode(curve))
        self.assertEqual(len(result.drop_points), 0)

    def test_grade_assignment(self):
        """평균 유지율에 따른 등급"""
        # 높은 유지율 → S등급
        curve = [
            {"time": "00:00", "retention": 100},
            {"time": "01:00", "retention": 95},
            {"time": "02:00", "retention": 90},
        ]
        result = diagnose_retention(self._make_episode(curve))
        self.assertEqual(result.grade, 'S')

    def test_low_retention_grade(self):
        """낮은 유지율 → D등급"""
        curve = [
            {"time": "00:00", "retention": 100},
            {"time": "01:00", "retention": 20},
            {"time": "02:00", "retention": 10},
        ]
        result = diagnose_retention(self._make_episode(curve))
        self.assertIn(result.grade, ('C', 'D'))

    def test_recommendations_generated(self):
        """권고사항이 생성됨"""
        curve = [
            {"time": "00:00", "retention": 100},
            {"time": "00:30", "retention": 70},  # 인트로 구간 급락
            {"time": "05:00", "retention": 60},
        ]
        result = diagnose_retention(self._make_episode(curve))
        self.assertGreater(len(result.recommendations), 0)

    def test_empty_data_raises(self):
        """빈 데이터 → ValueError"""
        with self.assertRaises(ValueError):
            diagnose_retention({})

    def test_missing_episode_id_raises(self):
        """episode_id 누락 → ValueError"""
        with self.assertRaises(ValueError):
            diagnose_retention({"retention_curve": [{"time": "00:00", "retention": 100}]})

    def test_insufficient_curve_raises(self):
        """데이터 포인트 1개 → ValueError"""
        with self.assertRaises(ValueError):
            diagnose_retention({
                "episode_id": "ep-001",
                "retention_curve": [{"time": "00:00", "retention": 100}]
            })

    def test_drop_point_fields(self):
        """DropPoint 필드 타입 확인"""
        curve = [
            {"time": "00:00", "retention": 100},
            {"time": "03:00", "retention": 70},  # -30% 급락
        ]
        result = diagnose_retention(self._make_episode(curve))
        self.assertEqual(len(result.drop_points), 1)
        dp = result.drop_points[0]
        self.assertIsInstance(dp.timestamp, str)
        self.assertIsInstance(dp.retention_before, float)
        self.assertIsInstance(dp.retention_after, float)
        self.assertIsInstance(dp.drop_amount, float)
        self.assertIsInstance(dp.likely_cause, str)

    def test_multiple_drops(self):
        """여러 급락 구간 감지"""
        curve = [
            {"time": "00:00", "retention": 100},
            {"time": "01:00", "retention": 85},   # -15%
            {"time": "02:00", "retention": 80},
            {"time": "03:00", "retention": 60},   # -20%
            {"time": "04:00", "retention": 55},
            {"time": "05:00", "retention": 35},   # -20%
        ]
        result = diagnose_retention(self._make_episode(curve))
        self.assertGreaterEqual(len(result.drop_points), 3)

    def test_avg_retention_calculation(self):
        """평균 유지율 계산 검증"""
        curve = [
            {"time": "00:00", "retention": 100},
            {"time": "01:00", "retention": 80},
            {"time": "02:00", "retention": 60},
        ]
        result = diagnose_retention(self._make_episode(curve))
        # (100 + 80 + 60) / 3 = 80.0
        self.assertAlmostEqual(result.avg_retention, 80.0, places=1)


if __name__ == '__main__':
    unittest.main()
