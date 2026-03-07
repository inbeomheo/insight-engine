"""Claim-Evidence Distance Analyzer 서비스 테스트."""
import unittest
from services.claim_evidence_distance_service import analyze_claim_evidence_distance


class TestClaimEvidenceDistance(unittest.TestCase):

    def test_empty_content(self):
        result = analyze_claim_evidence_distance('')
        self.assertEqual(result['score'], 100.0)
        self.assertEqual(result['summary']['level'], 'none')

    def test_none_content(self):
        result = analyze_claim_evidence_distance(None)
        self.assertEqual(result['score'], 100.0)

    def test_no_claims(self):
        content = '오늘 날씨가 좋습니다. 산책을 나갔습니다.'
        result = analyze_claim_evidence_distance(content)
        self.assertEqual(result['summary']['total_claims'], 0)

    def test_claim_with_nearby_evidence(self):
        content = ('이 방법은 매우 효과적입니다. '
                   '연구에 따르면 70%의 성능 향상이 있습니다.')
        result = analyze_claim_evidence_distance(content)
        self.assertGreater(result['summary']['supported_claims'], 0)

    def test_claim_with_distant_evidence(self):
        content = ('이 방법은 매우 효과적입니다. '
                   '첫 번째 내용입니다. '
                   '두 번째 내용입니다. '
                   '세 번째 내용입니다. '
                   '네 번째 내용입니다. '
                   '다섯 번째 내용입니다. '
                   '여섯 번째 내용입니다. '
                   '연구에 따르면 효과가 있습니다.')
        result = analyze_claim_evidence_distance(content)
        self.assertGreater(result['summary']['distant_claims'], 0)

    def test_unsupported_claim(self):
        content = ('이것은 매우 중요합니다. '
                   '또한 필수적입니다. '
                   '모두가 해야 합니다.')
        result = analyze_claim_evidence_distance(content)
        self.assertGreater(result['summary']['unsupported_claims'], 0)

    def test_well_supported_level(self):
        content = ('이 도구는 효과적입니다. '
                   '예를 들어 처리 속도가 30% 빨라집니다. '
                   '캐싱은 필수적입니다. '
                   '연구에 따르면 응답 시간이 50% 감소합니다.')
        result = analyze_claim_evidence_distance(content)
        self.assertIn(result['summary']['level'],
                       ('well_supported', 'mostly_supported'))

    def test_english_content(self):
        content = ('This approach is essential for performance. '
                   'According to research, it improves throughput by 40%. '
                   'Caching should be implemented. '
                   'For example, Redis reduces latency significantly.')
        result = analyze_claim_evidence_distance(content)
        self.assertGreater(result['summary']['total_claims'], 0)
        self.assertGreater(result['summary']['supported_claims'], 0)

    def test_url_as_evidence(self):
        content = ('이 라이브러리는 추천합니다. '
                   '자세한 내용은 https://example.com 을 참고하세요.')
        result = analyze_claim_evidence_distance(content)
        self.assertGreater(result['summary']['supported_claims'], 0)

    def test_score_range(self):
        content = '일반적인 콘텐츠입니다.'
        result = analyze_claim_evidence_distance(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_return_structure(self):
        content = '구조 확인 테스트입니다.'
        result = analyze_claim_evidence_distance(content)
        self.assertIn('score', result)
        self.assertIn('summary', result)
        self.assertIn('distant_claims', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_claims', result['summary'])
        self.assertIn('supported_claims', result['summary'])
        self.assertIn('distant_claims', result['summary'])
        self.assertIn('unsupported_claims', result['summary'])
        self.assertIn('level', result['summary'])

    def test_suggestions_for_weak(self):
        content = '이것은 매우 중요합니다. 반드시 필요합니다.'
        result = analyze_claim_evidence_distance(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_code_block_as_evidence(self):
        content = ('이 함수가 가장 좋습니다. '
                   '예를 들어:\n'
                   '```python\ndef fast(): pass\n```')
        result = analyze_claim_evidence_distance(content)
        self.assertGreater(result['summary']['supported_claims'], 0)


if __name__ == '__main__':
    unittest.main()
