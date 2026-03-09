"""
증거 패널 서비스 테스트
"""

import unittest

from services.evidence_panel_service import (
    EvidenceItem,
    EvidencePanel,
    create_panel,
    add_evidence,
    score_panel,
    identify_gaps,
    rank_by_strength,
    VALID_EVIDENCE_TYPES,
)


class TestCreatePanel(unittest.TestCase):
    """패널 생성 테스트"""

    def test_create_basic(self):
        """기본 패널 생성"""
        panel = create_panel("AI의 미래")
        self.assertEqual(panel.topic, "AI의 미래")
        self.assertEqual(panel.items, [])
        self.assertEqual(panel.overall_score, 0.0)
        self.assertNotEqual(panel.panel_id, "")

    def test_create_unique_ids(self):
        """고유 ID 생성"""
        p1 = create_panel("주제1")
        p2 = create_panel("주제2")
        self.assertNotEqual(p1.panel_id, p2.panel_id)


class TestAddEvidence(unittest.TestCase):
    """증거 추가 테스트"""

    def test_add_data_evidence(self):
        """데이터 증거 추가"""
        panel = create_panel("테스트")
        panel = add_evidence(panel, "주장1", "근거 텍스트", "data", 4, "출처")
        self.assertEqual(len(panel.items), 1)
        self.assertEqual(panel.items[0].evidence_type, "data")
        self.assertEqual(panel.items[0].strength, 4)

    def test_add_all_types(self):
        """모든 증거 유형 추가"""
        panel = create_panel("테스트")
        for t in VALID_EVIDENCE_TYPES:
            panel = add_evidence(panel, f"주장-{t}", f"근거-{t}", t, 3)
        self.assertEqual(len(panel.items), 4)

    def test_invalid_type(self):
        """잘못된 증거 유형"""
        panel = create_panel("테스트")
        with self.assertRaises(ValueError) as ctx:
            add_evidence(panel, "주장", "근거", "invalid_type", 3)
        self.assertIn("잘못된 증거 유형", str(ctx.exception))

    def test_invalid_strength_low(self):
        """강도 범위 초과 (하한)"""
        panel = create_panel("테스트")
        with self.assertRaises(ValueError):
            add_evidence(panel, "주장", "근거", "data", 0)

    def test_invalid_strength_high(self):
        """강도 범위 초과 (상한)"""
        panel = create_panel("테스트")
        with self.assertRaises(ValueError):
            add_evidence(panel, "주장", "근거", "data", 6)

    def test_auto_score_update(self):
        """추가 시 자동 점수 업데이트"""
        panel = create_panel("테스트")
        panel = add_evidence(panel, "주장", "근거", "data", 5)
        self.assertGreater(panel.overall_score, 0.0)


class TestScorePanel(unittest.TestCase):
    """패널 점수 테스트"""

    def test_score_empty(self):
        """빈 패널 점수"""
        panel = create_panel("테스트")
        self.assertEqual(score_panel(panel), 0.0)

    def test_score_single_data(self):
        """data 유형 단일 증거"""
        panel = create_panel("테스트")
        panel = add_evidence(panel, "주장", "근거", "data", 5)
        score = score_panel(panel)
        # data 가중치 1.5, strength 5 → 5 * 1.5 / 1.5 = 5.0
        self.assertEqual(score, 5.0)

    def test_data_weighted_higher(self):
        """data/expert가 높은 가중치"""
        # data(strength=3)와 example(strength=3)
        panel1 = create_panel("테스트")
        panel1 = add_evidence(panel1, "주장", "근거", "data", 3)

        panel2 = create_panel("테스트")
        panel2 = add_evidence(panel2, "주장", "근거", "example", 3)

        # 단일 항목이면 같은 결과 (가중 평균이므로)
        # 복합 비교
        panel3 = create_panel("테스트")
        panel3 = add_evidence(panel3, "주장1", "근거1", "data", 5)
        panel3 = add_evidence(panel3, "주장2", "근거2", "example", 1)
        score = score_panel(panel3)
        # (5*1.5 + 1*0.8) / (1.5+0.8) = 8.3/2.3 ≈ 3.61
        self.assertGreater(score, 3.0)

    def test_score_bounds(self):
        """점수 범위 (0.0 ~ 5.0)"""
        panel = create_panel("테스트")
        panel = add_evidence(panel, "주장1", "근거1", "data", 5)
        panel = add_evidence(panel, "주장2", "근거2", "expert", 5)
        score = score_panel(panel)
        self.assertLessEqual(score, 5.0)
        self.assertGreaterEqual(score, 0.0)


class TestIdentifyGaps(unittest.TestCase):
    """증거 공백 식별 테스트"""

    def test_all_covered(self):
        """모든 유형 커버"""
        panel = create_panel("테스트")
        for t in VALID_EVIDENCE_TYPES:
            panel = add_evidence(panel, f"주장-{t}", f"근거-{t}", t, 3)
        gaps = identify_gaps(panel)
        self.assertEqual(gaps, [])

    def test_partial_coverage(self):
        """일부만 커버"""
        panel = create_panel("테스트")
        panel = add_evidence(panel, "주장", "근거", "data", 3)
        gaps = identify_gaps(panel)
        self.assertIn("expert", gaps)
        self.assertIn("testimony", gaps)
        self.assertIn("example", gaps)
        self.assertNotIn("data", gaps)

    def test_empty_panel(self):
        """빈 패널 — 모든 유형 공백"""
        panel = create_panel("테스트")
        gaps = identify_gaps(panel)
        self.assertEqual(len(gaps), 4)

    def test_gaps_sorted(self):
        """공백 목록 정렬"""
        panel = create_panel("테스트")
        panel = add_evidence(panel, "주장", "근거", "testimony", 3)
        gaps = identify_gaps(panel)
        self.assertEqual(gaps, sorted(gaps))


class TestRankByStrength(unittest.TestCase):
    """강도순 정렬 테스트"""

    def test_rank_basic(self):
        """기본 정렬"""
        panel = create_panel("테스트")
        panel = add_evidence(panel, "주장1", "근거1", "data", 2)
        panel = add_evidence(panel, "주장2", "근거2", "expert", 5)
        panel = add_evidence(panel, "주장3", "근거3", "testimony", 3)
        ranked = rank_by_strength(panel)
        self.assertEqual(ranked[0].strength, 5)
        self.assertEqual(ranked[-1].strength, 2)

    def test_rank_empty(self):
        """빈 패널"""
        panel = create_panel("테스트")
        ranked = rank_by_strength(panel)
        self.assertEqual(ranked, [])

    def test_rank_same_strength(self):
        """동일 강도"""
        panel = create_panel("테스트")
        panel = add_evidence(panel, "주장1", "근거1", "data", 3)
        panel = add_evidence(panel, "주장2", "근거2", "expert", 3)
        ranked = rank_by_strength(panel)
        self.assertEqual(len(ranked), 2)
        self.assertEqual(ranked[0].strength, 3)


if __name__ == "__main__":
    unittest.main()
