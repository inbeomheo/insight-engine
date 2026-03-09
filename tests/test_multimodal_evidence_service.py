"""멀티모달 증거 서비스 테스트"""
import unittest
from services.multimodal_evidence_service import (
    Evidence, EvidenceBundle,
    classify_strength, bundle_evidence,
    assess_coverage, find_contradictions,
)


class TestClassifyStrength(unittest.TestCase):
    """증거 강도 분류 테스트"""

    def test_strong_with_data(self):
        result = classify_strength('데이터에 따르면 연구 결과 통계적으로 유의미합니다.', '기후 변화')
        self.assertEqual(result, 'strong')

    def test_strong_with_stats(self):
        result = classify_strength('실험 결과 80% 증가했습니다.', '효과')
        self.assertEqual(result, 'strong')

    def test_weak_with_opinion(self):
        result = classify_strength('아마 그런 것 같다는 의견이 있습니다. 추측이지만.', '주장')
        self.assertEqual(result, 'weak')

    def test_moderate_mixed(self):
        """strong/weak 키워드가 균등 → moderate"""
        result = classify_strength('데이터가 있지만 의견도 있습니다.', '주장')
        self.assertEqual(result, 'moderate')

    def test_moderate_default(self):
        result = classify_strength('일반적인 내용입니다.', '주장')
        self.assertEqual(result, 'moderate')

    def test_empty_content(self):
        result = classify_strength('', '주장')
        self.assertEqual(result, 'weak')

    def test_claim_also_considered(self):
        """주장 텍스트도 분류에 반영"""
        result = classify_strength('내용', '통계 데이터 연구 분석')
        self.assertEqual(result, 'strong')

    def test_english_keywords(self):
        result = classify_strength('The research data shows evidence of improvement.', 'claim')
        self.assertEqual(result, 'strong')


class TestBundleEvidence(unittest.TestCase):
    """증거 묶음 테스트"""

    def test_basic_bundle(self):
        evidences = [
            Evidence('e1', '주장', 'text', '텍스트 증거', 'strong', '출처1'),
            Evidence('e2', '주장', 'data', '데이터 증거', 'strong', '출처2'),
        ]
        bundle = bundle_evidence('주장', evidences)
        self.assertEqual(bundle.claim, '주장')
        self.assertEqual(len(bundle.evidences), 2)
        self.assertEqual(bundle.overall_strength, 'strong')

    def test_overall_strength_most_common(self):
        """최빈값으로 전체 강도 결정"""
        evidences = [
            Evidence('e1', '주장', 'text', '내용', 'moderate'),
            Evidence('e2', '주장', 'data', '내용', 'moderate'),
            Evidence('e3', '주장', 'image', '내용', 'strong'),
        ]
        bundle = bundle_evidence('주장', evidences)
        self.assertEqual(bundle.overall_strength, 'moderate')

    def test_strength_tie_favor_strong(self):
        """동률 시 강한 쪽 우선"""
        evidences = [
            Evidence('e1', '주장', 'text', '내용', 'strong'),
            Evidence('e2', '주장', 'data', '내용', 'weak'),
        ]
        bundle = bundle_evidence('주장', evidences)
        self.assertEqual(bundle.overall_strength, 'strong')

    def test_modality_coverage(self):
        evidences = [
            Evidence('e1', '주장', 'text', '내용', 'moderate'),
            Evidence('e2', '주장', 'image', '내용', 'moderate'),
            Evidence('e3', '주장', 'data', '내용', 'moderate'),
        ]
        bundle = bundle_evidence('주장', evidences)
        self.assertIn('text', bundle.modality_coverage)
        self.assertIn('image', bundle.modality_coverage)
        self.assertIn('data', bundle.modality_coverage)

    def test_empty_evidences(self):
        bundle = bundle_evidence('주장', [])
        self.assertEqual(bundle.overall_strength, 'weak')
        self.assertEqual(bundle.modality_coverage, [])

    def test_single_evidence(self):
        evidences = [Evidence('e1', '주장', 'text', '내용', 'strong')]
        bundle = bundle_evidence('주장', evidences)
        self.assertEqual(bundle.overall_strength, 'strong')


class TestAssessCoverage(unittest.TestCase):
    """커버리지 분석 테스트"""

    def test_full_coverage(self):
        evidences = [
            Evidence('e1', '주장', 'text', '내용', 'strong'),
            Evidence('e2', '주장', 'image', '내용', 'moderate'),
            Evidence('e3', '주장', 'audio', '내용', 'moderate'),
            Evidence('e4', '주장', 'data', '내용', 'strong'),
        ]
        bundle = bundle_evidence('주장', evidences)
        coverage = assess_coverage(bundle)
        self.assertEqual(coverage['coverage_ratio'], 1.0)
        self.assertEqual(len(coverage['missing_modalities']), 0)

    def test_partial_coverage(self):
        evidences = [
            Evidence('e1', '주장', 'text', '내용', 'strong'),
        ]
        bundle = bundle_evidence('주장', evidences)
        coverage = assess_coverage(bundle)
        self.assertEqual(coverage['coverage_ratio'], 0.25)
        self.assertEqual(len(coverage['missing_modalities']), 3)

    def test_strength_distribution(self):
        evidences = [
            Evidence('e1', '주장', 'text', '내용', 'strong'),
            Evidence('e2', '주장', 'text', '내용2', 'weak'),
        ]
        bundle = bundle_evidence('주장', evidences)
        coverage = assess_coverage(bundle)
        self.assertEqual(coverage['strength_distribution']['strong'], 1)
        self.assertEqual(coverage['strength_distribution']['weak'], 1)

    def test_total_evidences(self):
        evidences = [Evidence(f'e{i}', '주장', 'text', f'내용{i}', 'moderate') for i in range(5)]
        bundle = bundle_evidence('주장', evidences)
        coverage = assess_coverage(bundle)
        self.assertEqual(coverage['total_evidences'], 5)


class TestFindContradictions(unittest.TestCase):
    """모순 탐지 테스트"""

    def test_strength_contradiction(self):
        """strong vs weak = 모순"""
        evidences = [
            Evidence('e1', '기후 변화', 'text', '데이터로 확인된 연구 결과', 'strong', '논문'),
            Evidence('e2', '기후 변화', 'text', '아마 추측이지만 의견', 'weak', '블로그'),
        ]
        contradictions = find_contradictions(evidences)
        self.assertEqual(len(contradictions), 1)
        self.assertEqual(contradictions[0][0].evidence_id, 'e1')
        self.assertEqual(contradictions[0][1].evidence_id, 'e2')

    def test_negation_contradiction(self):
        """부정 키워드 대립 = 모순"""
        evidences = [
            Evidence('e1', '효과', 'text', '효과가 있다', 'moderate'),
            Evidence('e2', '효과', 'text', '효과가 없다', 'moderate'),
        ]
        contradictions = find_contradictions(evidences)
        self.assertGreater(len(contradictions), 0)

    def test_different_claims_no_contradiction(self):
        """다른 주장 간에는 모순 아님"""
        evidences = [
            Evidence('e1', '주장A', 'text', '연구 데이터', 'strong'),
            Evidence('e2', '주장B', 'text', '추측 의견', 'weak'),
        ]
        contradictions = find_contradictions(evidences)
        self.assertEqual(len(contradictions), 0)

    def test_no_contradictions(self):
        evidences = [
            Evidence('e1', '주장', 'text', '데이터 연구', 'strong'),
            Evidence('e2', '주장', 'text', '통계 확인', 'strong'),
        ]
        contradictions = find_contradictions(evidences)
        self.assertEqual(len(contradictions), 0)

    def test_empty_evidences(self):
        contradictions = find_contradictions([])
        self.assertEqual(len(contradictions), 0)

    def test_single_evidence(self):
        evidences = [Evidence('e1', '주장', 'text', '내용', 'strong')]
        contradictions = find_contradictions(evidences)
        self.assertEqual(len(contradictions), 0)

    def test_multiple_contradictions(self):
        """여러 모순 쌍"""
        evidences = [
            Evidence('e1', '주장', 'text', '연구 데이터 확인', 'strong'),
            Evidence('e2', '주장', 'text', '추측 의견일 뿐', 'weak'),
            Evidence('e3', '주장', 'text', '통계 실험 결과', 'strong'),
            Evidence('e4', '주장', 'text', '아마 소문', 'weak'),
        ]
        contradictions = find_contradictions(evidences)
        self.assertGreater(len(contradictions), 1)


if __name__ == '__main__':
    unittest.main()
