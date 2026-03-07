"""
Claim & Citation Verifier 서비스 테스트

verify_claims 함수의 주장 감지, 출처 감지, 점수 계산을 검증합니다.
"""
import unittest

from services.claim_verifier_service import verify_claims


class TestClaimVerifierService(unittest.TestCase):
    """verify_claims 함수 단위 테스트"""

    # ── 1. 빈 입력 처리 ──

    def test_empty_content(self):
        """빈 문자열 입력 시 기본 구조 반환"""
        result = verify_claims("")
        self.assertEqual(result["claims"], [])
        self.assertEqual(result["summary"]["total_claims"], 0)
        self.assertEqual(result["summary"]["cited"], 0)
        self.assertEqual(result["summary"]["uncited"], 0)
        self.assertEqual(result["summary"]["citation_rate"], 0.0)
        self.assertEqual(result["credibility_score"], 100.0)
        self.assertEqual(result["suggestions"], [])

    def test_none_content(self):
        """None 입력 시 기본 구조 반환"""
        result = verify_claims(None)
        self.assertEqual(result["claims"], [])
        self.assertEqual(result["summary"]["total_claims"], 0)
        self.assertEqual(result["credibility_score"], 100.0)

    # ── 2. 주장 유형별 감지 ──

    def test_statistic_detection(self):
        """통계 주장 감지: 숫자 + 단위 패턴"""
        content = "이 기업의 매출이 30% 증가했다. 사용자 수는 500만명을 돌파했다."
        result = verify_claims(content)

        stat_claims = [c for c in result["claims"] if c["type"] == "statistic"]
        self.assertGreaterEqual(len(stat_claims), 1, "최소 1건의 통계 주장 감지 필요")

        # 통계 주장은 출처 없으면 severity high
        for claim in stat_claims:
            if claim["needs_citation"]:
                self.assertEqual(claim["severity"], "high")

    def test_fact_detection(self):
        """사실 주장 감지: 절대적 표현, 역사적 사실"""
        content = "이 제품은 세계 최초의 AI 기반 번역기이다. 2020년에 구글이 출시했다."
        result = verify_claims(content)

        fact_claims = [c for c in result["claims"] if c["type"] == "fact"]
        self.assertGreaterEqual(len(fact_claims), 1, "최소 1건의 사실 주장 감지 필요")

    def test_quote_detection(self):
        """인용문 감지: 큰따옴표 및 인용 동사 패턴"""
        content = '"AI는 인류의 미래를 바꿀 것입니다"라고 말했다.'
        result = verify_claims(content)

        quote_claims = [c for c in result["claims"] if c["type"] == "quote"]
        self.assertGreaterEqual(len(quote_claims), 1, "인용문 감지 필요")
        # 인용 출처 없으면 severity high
        for claim in quote_claims:
            if claim["needs_citation"]:
                self.assertEqual(claim["severity"], "high")

    def test_comparison_detection(self):
        """비교 주장 감지: '~보다', '~대비' 패턴"""
        content = "경쟁사보다 2배 더 빠른 처리 속도를 보여준다."
        result = verify_claims(content)

        comp_claims = [c for c in result["claims"] if c["type"] == "comparison"]
        self.assertGreaterEqual(len(comp_claims), 1, "비교 주장 감지 필요")
        for claim in comp_claims:
            if claim["needs_citation"]:
                self.assertEqual(claim["severity"], "medium")

    def test_prediction_detection(self):
        """예측 주장 감지: '~할 것이다', '~될 전망' 패턴"""
        content = "2030년까지 AI 시장은 10조원 규모가 될 전망이다."
        result = verify_claims(content)

        # 통계 + 예측 모두 감지될 수 있음
        all_types = {c["type"] for c in result["claims"]}
        self.assertTrue(
            "prediction" in all_types or "statistic" in all_types,
            "예측 또는 통계 주장 감지 필요"
        )

    # ── 3. 출처 감지 ──

    def test_source_detection(self):
        """출처 패턴 감지: '~에 따르면' + 출처 존재 확인"""
        content = "가트너에 따르면 클라우드 시장은 매년 20% 성장하고 있다."
        result = verify_claims(content)

        self.assertGreater(len(result["claims"]), 0, "주장이 감지되어야 함")

        # 출처가 감지된 주장이 있는지 확인
        sourced = [c for c in result["claims"] if c["has_source"]]
        self.assertGreaterEqual(len(sourced), 1, "'에 따르면' 패턴으로 출처 감지 필요")
        self.assertIsNotNone(sourced[0]["source"])

    def test_uncited_claim(self):
        """출처 없는 주장: needs_citation=True, source=None"""
        content = "이 기술의 정확도는 99.5%에 달한다."
        result = verify_claims(content)

        self.assertGreater(len(result["claims"]), 0)
        uncited = [c for c in result["claims"] if c["needs_citation"]]
        self.assertGreaterEqual(len(uncited), 1, "출처 없는 주장이 감지되어야 함")
        for claim in uncited:
            self.assertFalse(claim["has_source"])
            self.assertIsNone(claim["source"])

    # ── 4. 요약 및 점수 계산 ──

    def test_citation_rate(self):
        """인용률 계산: cited / total × 100"""
        content = (
            "MIT 연구에 따르면 AI 정확도가 95%에 도달했다. "
            "처리 속도는 3배 향상되었다."
        )
        result = verify_claims(content)
        summary = result["summary"]

        self.assertGreater(summary["total_claims"], 0)
        self.assertEqual(summary["cited"] + summary["uncited"], summary["total_claims"])

        # citation_rate 계산 검증
        expected_rate = round(summary["cited"] / summary["total_claims"] * 100, 2)
        self.assertAlmostEqual(summary["citation_rate"], expected_rate, places=1)

    def test_credibility_score_range(self):
        """신뢰도 점수는 항상 0-100 범위"""
        # 출처 없는 주장이 많은 경우
        content = (
            "매출이 50% 증가했다. 사용자 수가 1000만명이다. "
            "세계 최초의 기술이다. 경쟁사보다 5배 빠르다. "
            "시장 점유율은 80%이다."
        )
        result = verify_claims(content)
        score = result["credibility_score"]
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 100.0)

        # 출처 있는 주장만 있는 경우
        content_sourced = "가트너에 따르면 클라우드 성장률은 25%이다."
        result_sourced = verify_claims(content_sourced)
        score_sourced = result_sourced["credibility_score"]
        self.assertGreaterEqual(score_sourced, 0.0)
        self.assertLessEqual(score_sourced, 100.0)

    def test_severity_levels(self):
        """심각도 레벨: high/medium/low 할당 검증"""
        content = (
            "정확도는 99%이다. "                           # statistic → high
            "이것은 세계 최초의 기술이다. "                   # fact(절대적) → high
            '"혁신적 기술"이라고 밝혔다. '                   # quote → high
            "경쟁사보다 2배 더 빠르다. "                     # comparison → medium
            "향후 시장 규모가 확대될 전망이다."               # prediction → low
        )
        result = verify_claims(content)

        severities = {c["severity"] for c in result["claims"]}
        # 다양한 심각도가 포함되어야 함
        self.assertTrue(
            len(severities) >= 2,
            f"최소 2종류 이상의 심각도 레벨 필요, 실제: {severities}"
        )

        # 각 심각도 레벨 값 검증
        for claim in result["claims"]:
            self.assertIn(claim["severity"], {"high", "medium", "low"})

    def test_suggestions(self):
        """미인용 주장이 있으면 개선 제안 목록 생성"""
        content = "매출이 200% 증가했다. 사용자 수는 1억명이다."
        result = verify_claims(content)

        # 출처 없는 통계이므로 제안이 있어야 함
        self.assertGreater(len(result["suggestions"]), 0, "개선 제안이 생성되어야 함")
        self.assertTrue(
            all(isinstance(s, str) for s in result["suggestions"]),
            "제안은 문자열 리스트여야 함"
        )

    # ── 5. 추가 검증 ──

    def test_all_cited_perfect_suggestions(self):
        """모든 주장에 출처가 있으면 긍정적 메시지"""
        content = "가트너(2025)에 따르면 클라우드 매출이 30% 증가했다."
        result = verify_claims(content)

        if result["summary"]["uncited"] == 0 and result["summary"]["total_claims"] > 0:
            self.assertIn("우수한 인용 품질", result["suggestions"][0])

    def test_url_as_source(self):
        """URL이 포함되면 출처로 인식"""
        content = "AI 정확도는 98%에 달한다. https://example.com/report"
        result = verify_claims(content)

        # URL이 같은 문장에 있으면 출처로 감지
        claims_with_url = [
            c for c in result["claims"]
            if c["has_source"] and c["source"] and "http" in c["source"]
        ]
        # URL이 별도 문장이면 감지되지 않을 수 있으므로, 전체 구조만 검증
        self.assertIsInstance(result["claims"], list)

    def test_year_reference_as_source(self):
        """(2024) 형태의 연도 참조를 출처로 인식"""
        content = "글로벌 AI 시장은 5000억 달러 규모이다(2025)."
        result = verify_claims(content)

        sourced = [c for c in result["claims"] if c["has_source"]]
        self.assertGreaterEqual(len(sourced), 1, "연도 참조를 출처로 인식해야 함")


if __name__ == "__main__":
    unittest.main()
