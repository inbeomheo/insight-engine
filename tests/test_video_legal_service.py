"""비디오-리걸 서비스 테스트."""

import unittest
from services.video_legal_service import (
    LegalRisk,
    LegalReview,
    scan_for_risks,
    classify_severity,
    recommend_clearance,
    generate_legal_summary,
)


class TestVideoLegalService(unittest.TestCase):
    """VideoLegalService 단위 테스트."""

    def test_scan_clean_transcript(self):
        """깨끗한 자막은 리스크 없음."""
        review = scan_for_risks("오늘은 날씨가 좋습니다. 산책을 해봅시다.")
        self.assertEqual(len(review.risks), 0)
        self.assertEqual(review.overall_risk, "low")
        self.assertEqual(review.clearance_status, "cleared")

    def test_scan_copyright_keywords(self):
        """저작권 키워드가 탐지된다."""
        review = scan_for_risks("이 프로그램을 무단 복제하면 안됩니다. 저작권 문제가 발생합니다.")
        risk_types = [r.risk_type for r in review.risks]
        self.assertIn("copyright", risk_types)

    def test_scan_defamation_keywords(self):
        """명예훼손 키워드가 탐지된다."""
        review = scan_for_risks("그 사람은 사기꾼이고 명예훼손에 해당합니다")
        risk_types = [r.risk_type for r in review.risks]
        self.assertIn("defamation", risk_types)

    def test_scan_privacy_keywords(self):
        """개인정보 키워드가 탐지된다."""
        review = scan_for_risks("이 사이트에서 개인정보를 수집합니다")
        risk_types = [r.risk_type for r in review.risks]
        self.assertIn("privacy", risk_types)

    def test_scan_medical_claim(self):
        """의료 주장 키워드가 탐지된다."""
        review = scan_for_risks("이 약은 부작용 없이 완치가 가능합니다")
        risk_types = [r.risk_type for r in review.risks]
        self.assertIn("medical_claim", risk_types)

    def test_scan_metadata_title(self):
        """메타데이터 제목도 스캔한다."""
        review = scan_for_risks("일반 내용", {"title": "저작권 무시 가이드", "video_id": "v1"})
        self.assertTrue(len(review.risks) > 0)

    def test_scan_uses_video_id(self):
        """메타데이터의 video_id를 사용한다."""
        review = scan_for_risks("test", {"video_id": "vid_123"})
        self.assertEqual(review.video_id, "vid_123")

    def test_scan_auto_generates_video_id(self):
        """video_id 없으면 자동 생성."""
        review = scan_for_risks("test")
        self.assertTrue(review.video_id.startswith("vid_"))

    def test_classify_severity_copyright(self):
        """저작권 리스크는 high."""
        self.assertEqual(classify_severity("copyright"), "high")

    def test_classify_severity_privacy(self):
        """개인정보 리스크는 medium."""
        self.assertEqual(classify_severity("privacy"), "medium")

    def test_classify_severity_unknown(self):
        """알 수 없는 유형은 low."""
        self.assertEqual(classify_severity("unknown_type"), "low")

    def test_recommend_clearance_no_risks(self):
        """리스크 없으면 cleared."""
        review = LegalReview("v1", [], "low", "")
        self.assertEqual(recommend_clearance(review), "cleared")

    def test_recommend_clearance_high_risk(self):
        """high 리스크 있으면 blocked."""
        risks = [LegalRisk("copyright", "high", "test", "01:00")]
        review = LegalReview("v1", risks, "high", "")
        self.assertEqual(recommend_clearance(review), "blocked")

    def test_recommend_clearance_medium_risk(self):
        """medium 리스크만 있으면 review_needed."""
        risks = [LegalRisk("privacy", "medium", "test", "02:00")]
        review = LegalReview("v1", risks, "medium", "")
        self.assertEqual(recommend_clearance(review), "review_needed")

    def test_recommend_clearance_low_risk(self):
        """low 리스크만 있으면 cleared."""
        risks = [LegalRisk("other", "low", "test", "03:00")]
        review = LegalReview("v1", risks, "low", "")
        self.assertEqual(recommend_clearance(review), "cleared")

    def test_generate_legal_summary_format(self):
        """법적 요약 보고서 형식 검증."""
        risks = [LegalRisk("copyright", "high", "무단 복제 키워드", "01:30")]
        review = LegalReview("v1", risks, "high", "blocked")
        summary = generate_legal_summary(review)
        self.assertIn("법적 검토 보고서", summary)
        self.assertIn("v1", summary)
        self.assertIn("blocked", summary)
        self.assertIn("copyright", summary)

    def test_generate_legal_summary_no_risks(self):
        """리스크 없는 보고서."""
        review = LegalReview("v1", [], "low", "cleared")
        summary = generate_legal_summary(review)
        self.assertIn("탐지되지 않았습니다", summary)

    def test_scan_multiple_risk_types(self):
        """여러 유형의 리스크가 동시 탐지된다."""
        text = "무단 복제 금지이며 개인정보 보호법 위반이고 완치를 보장합니다"
        review = scan_for_risks(text)
        risk_types = set(r.risk_type for r in review.risks)
        self.assertTrue(len(risk_types) >= 2)

    def test_scan_overall_risk_multiple_risks(self):
        """리스크가 많으면 전체 리스크가 높아진다."""
        text = "저작권 무단 복제 명예훼손 사기꾼 개인정보 전화번호 상표 완치 부작용 없"
        review = scan_for_risks(text)
        self.assertIn(review.overall_risk, ["medium", "high"])

    def test_risk_has_timestamp(self):
        """탐지된 리스크에 타임스탬프가 있다."""
        review = scan_for_risks("저작권 침해 내용입니다")
        if review.risks:
            self.assertIsNotNone(review.risks[0].timestamp)


if __name__ == "__main__":
    unittest.main()
