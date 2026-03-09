"""클레임 매핑 서비스 테스트"""
import unittest
from services.claim_mapping_service import (
    create_claim, assess_claim, update_status, calculate_total_exposure,
    group_by_type, Claim
)


class TestClaimMappingService(unittest.TestCase):

    def setUp(self):
        self.claim = create_claim('홍길동', 'property', 50000.0, ['사진', '영수증', '진단서'])

    def test_create_claim(self):
        self.assertIsInstance(self.claim, Claim)
        self.assertEqual(self.claim.claimant, '홍길동')
        self.assertEqual(self.claim.status, 'filed')

    def test_create_claim_invalid_type(self):
        with self.assertRaises(ValueError):
            create_claim('A', 'unknown', 1000, [])

    def test_assess_claim_high_evidence(self):
        result = assess_claim(self.claim)
        self.assertEqual(result['evidence_score'], 1.0)
        self.assertEqual(result['recommendation'], 'approve')

    def test_assess_claim_low_evidence(self):
        claim = create_claim('A', 'medical', 5000, [])
        result = assess_claim(claim)
        self.assertEqual(result['evidence_score'], 0.0)
        self.assertEqual(result['recommendation'], 'deny')

    def test_assess_claim_amount_risk(self):
        high = create_claim('A', 'business', 200000, ['e1'])
        result = assess_claim(high)
        self.assertEqual(result['amount_risk'], 'high')

    def test_update_status(self):
        updated = update_status(self.claim, 'approved')
        self.assertEqual(updated.status, 'approved')

    def test_update_status_invalid(self):
        with self.assertRaises(ValueError):
            update_status(self.claim, 'invalid')

    def test_calculate_total_exposure(self):
        claims = [
            create_claim('A', 'property', 10000, []),
            create_claim('B', 'medical', 20000, []),
        ]
        # 둘 다 filed 상태
        self.assertEqual(calculate_total_exposure(claims), 30000.0)

    def test_calculate_total_exposure_excludes_denied(self):
        claims = [
            create_claim('A', 'property', 10000, []),
            update_status(create_claim('B', 'medical', 20000, []), 'denied'),
        ]
        self.assertEqual(calculate_total_exposure(claims), 10000.0)

    def test_group_by_type(self):
        claims = [
            create_claim('A', 'property', 1000, []),
            create_claim('B', 'property', 2000, []),
            create_claim('C', 'medical', 3000, []),
        ]
        groups = group_by_type(claims)
        self.assertEqual(len(groups['property']), 2)
        self.assertEqual(len(groups['medical']), 1)

    def test_assess_claim_medium_evidence(self):
        claim = create_claim('A', 'liability', 5000, ['e1'])
        result = assess_claim(claim)
        self.assertEqual(result['recommendation'], 'review')


if __name__ == '__main__':
    unittest.main()
