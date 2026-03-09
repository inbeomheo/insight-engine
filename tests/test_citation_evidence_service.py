"""citation_evidence_service 단위 테스트"""
import unittest
from services.citation_evidence_service import (
    Claim,
    EvidencePack,
    extract_claims,
    attach_evidence,
    _classify_claim,
    _needs_evidence,
    _calculate_confidence,
)


class TestClaimDataclass(unittest.TestCase):
    """Claim 데이터클래스 테스트"""

    def test_claim_fields(self):
        """Claim 필드가 올바르게 생성된다"""
        claim = Claim(
            text='매출이 50% 증가했다',
            claim_type='statistic',
            evidence_needed=True,
            evidence_url='https://example.com',
            confidence=0.7,
        )
        self.assertEqual(claim.text, '매출이 50% 증가했다')
        self.assertEqual(claim.claim_type, 'statistic')
        self.assertTrue(claim.evidence_needed)
        self.assertEqual(claim.evidence_url, 'https://example.com')
        self.assertAlmostEqual(claim.confidence, 0.7)

    def test_claim_defaults(self):
        """Claim 기본값이 올바르다"""
        claim = Claim(text='테스트', claim_type='fact', evidence_needed=True)
        self.assertIsNone(claim.evidence_url)
        self.assertAlmostEqual(claim.confidence, 0.0)

    def test_claim_none_url(self):
        """evidence_url이 None이어도 유효하다"""
        claim = Claim(
            text='의견', claim_type='opinion',
            evidence_needed=False, evidence_url=None,
        )
        self.assertIsNone(claim.evidence_url)


class TestEvidencePackDataclass(unittest.TestCase):
    """EvidencePack 데이터클래스 테스트"""

    def test_evidence_pack_defaults(self):
        """EvidencePack 기본값이 빈 리스트이다"""
        pack = EvidencePack(content_id='test-id')
        self.assertEqual(pack.claims, [])
        self.assertEqual(pack.bibliography, [])
        self.assertAlmostEqual(pack.coverage_score, 0.0)

    def test_evidence_pack_with_data(self):
        """EvidencePack에 데이터를 담을 수 있다"""
        claims = [Claim(text='t', claim_type='fact', evidence_needed=True)]
        pack = EvidencePack(
            content_id='id-1',
            claims=claims,
            bibliography=['https://a.com'],
            coverage_score=0.5,
        )
        self.assertEqual(len(pack.claims), 1)
        self.assertEqual(len(pack.bibliography), 1)


class TestClassifyClaim(unittest.TestCase):
    """_classify_claim 내부 함수 테스트"""

    def test_statistic_with_percent(self):
        """퍼센트가 포함된 문장은 statistic으로 분류된다"""
        self.assertEqual(_classify_claim('매출이 30% 증가했습니다'), 'statistic')

    def test_statistic_with_number(self):
        """큰 숫자가 포함된 문장은 statistic으로 분류된다"""
        self.assertEqual(_classify_claim('사용자가 100만명을 돌파했다'), 'statistic')

    def test_recommendation_korean(self):
        """한국어 권유 표현은 recommendation으로 분류된다"""
        self.assertEqual(_classify_claim('반드시 확인해야 합니다'), 'recommendation')

    def test_recommendation_should(self):
        """should가 포함된 문장은 recommendation으로 분류된다"""
        self.assertEqual(_classify_claim('You should verify the data'), 'recommendation')

    def test_opinion_korean(self):
        """주관적 표현은 opinion으로 분류된다"""
        self.assertEqual(_classify_claim('개인적으로 이 방법이 좋다'), 'opinion')

    def test_opinion_english(self):
        """I think 등은 opinion으로 분류된다"""
        self.assertEqual(_classify_claim('I think this approach is better'), 'opinion')

    def test_fact_default(self):
        """분류 불가 시 fact로 간주된다"""
        self.assertEqual(_classify_claim('하늘은 파랗다'), 'fact')


class TestNeedsEvidence(unittest.TestCase):
    """_needs_evidence 테스트"""

    def test_statistic_needs_evidence(self):
        """statistic은 근거가 필요하다"""
        self.assertTrue(_needs_evidence('statistic'))

    def test_fact_needs_evidence(self):
        """fact은 근거가 필요하다"""
        self.assertTrue(_needs_evidence('fact'))

    def test_opinion_no_evidence(self):
        """opinion은 근거가 불필요하다"""
        self.assertFalse(_needs_evidence('opinion'))

    def test_recommendation_no_evidence(self):
        """recommendation은 근거가 불필요하다"""
        self.assertFalse(_needs_evidence('recommendation'))


class TestCalculateConfidence(unittest.TestCase):
    """_calculate_confidence 테스트"""

    def test_statistic_no_evidence(self):
        """통계 + 근거 없음 → 낮은 신뢰도"""
        score = _calculate_confidence('statistic', has_evidence=False)
        self.assertAlmostEqual(score, 0.3)

    def test_statistic_with_evidence(self):
        """통계 + 근거 있음 → 신뢰도 상승"""
        score = _calculate_confidence('statistic', has_evidence=True)
        self.assertAlmostEqual(score, 0.7)

    def test_opinion_no_evidence(self):
        """의견은 기본 신뢰도가 높다"""
        score = _calculate_confidence('opinion', has_evidence=False)
        self.assertAlmostEqual(score, 0.7)

    def test_confidence_max_cap(self):
        """신뢰도는 1.0을 초과하지 않는다"""
        score = _calculate_confidence('opinion', has_evidence=True)
        self.assertLessEqual(score, 1.0)


class TestExtractClaims(unittest.TestCase):
    """extract_claims 함수 테스트"""

    def test_basic_extraction(self):
        """기본 주장 추출이 동작한다"""
        content = '매출이 50% 증가했다. 이 방법을 추천합니다.'
        claims = extract_claims(content)
        self.assertGreaterEqual(len(claims), 1)
        self.assertIsInstance(claims[0], Claim)

    def test_empty_content(self):
        """빈 콘텐츠는 빈 리스트를 반환한다"""
        self.assertEqual(extract_claims(''), [])
        self.assertEqual(extract_claims('   '), [])

    def test_none_raises(self):
        """None 입력은 ValueError"""
        with self.assertRaises(ValueError):
            extract_claims(None)

    def test_short_sentences_skipped(self):
        """5자 미만 문장은 건너뛴다"""
        content = 'AB. 이것은 충분히 긴 문장입니다.'
        claims = extract_claims(content)
        texts = [c.text for c in claims]
        self.assertTrue(all(len(t) >= 5 for t in texts))

    def test_statistic_claim_detected(self):
        """숫자가 포함된 문장이 statistic으로 분류된다"""
        content = '사용자 수가 200만명을 돌파했습니다.'
        claims = extract_claims(content)
        self.assertTrue(any(c.claim_type == 'statistic' for c in claims))

    def test_evidence_needed_for_facts(self):
        """fact 유형은 evidence_needed=True이다"""
        content = '물은 섭씨 0도에서 얼기 시작한다.'
        claims = extract_claims(content)
        # 숫자 포함이라 statistic 또는 fact
        for c in claims:
            if c.claim_type in ('statistic', 'fact'):
                self.assertTrue(c.evidence_needed)

    def test_multiple_claims(self):
        """여러 문장에서 여러 주장이 추출된다"""
        content = (
            '매출이 30% 증가했다. '
            '개인적으로 이 전략이 효과적이라고 생각한다. '
            '모든 팀원이 참여해야 합니다.'
        )
        claims = extract_claims(content)
        self.assertGreaterEqual(len(claims), 2)


class TestAttachEvidence(unittest.TestCase):
    """attach_evidence 함수 테스트"""

    def test_basic_attach(self):
        """기본 근거팩 첨부가 동작한다"""
        content = '이 기술은 성능을 50% 향상시켰다.'
        pack = attach_evidence(content)

        self.assertIsInstance(pack, EvidencePack)
        self.assertTrue(len(pack.content_id) > 0)
        self.assertGreaterEqual(len(pack.claims), 1)

    def test_none_raises(self):
        """None 입력은 ValueError"""
        with self.assertRaises(ValueError):
            attach_evidence(None)

    def test_empty_content(self):
        """빈 콘텐츠는 빈 팩을 반환한다"""
        pack = attach_evidence('')
        self.assertEqual(pack.claims, [])
        self.assertEqual(pack.bibliography, [])
        self.assertAlmostEqual(pack.coverage_score, 1.0)

    def test_coverage_zero_without_evidence(self):
        """근거가 없으면 커버리지가 0이다"""
        content = '수출이 20% 감소했다. 국내 생산량은 전년 대비 낮아졌다.'
        pack = attach_evidence(content)
        # evidence_url이 모두 None이므로 커버리지 0
        needs = [c for c in pack.claims if c.evidence_needed]
        if needs:
            self.assertAlmostEqual(pack.coverage_score, 0.0)

    def test_unique_content_id(self):
        """호출마다 고유한 content_id가 생성된다"""
        pack1 = attach_evidence('테스트 콘텐츠 하나입니다.')
        pack2 = attach_evidence('테스트 콘텐츠 하나입니다.')
        self.assertNotEqual(pack1.content_id, pack2.content_id)

    def test_bibliography_empty_when_no_urls(self):
        """evidence_url이 없으면 bibliography가 비어있다"""
        pack = attach_evidence('AI 기술이 빠르게 발전하고 있다.')
        self.assertEqual(pack.bibliography, [])


if __name__ == '__main__':
    unittest.main()
