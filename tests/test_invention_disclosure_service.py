"""발명 공개서 서비스 테스트"""
import unittest
from services.invention_disclosure_service import (
    create_disclosure, add_claim, add_prior_art, validate_disclosure,
    export_disclosure, InventionDisclosure
)


class TestInventionDisclosureService(unittest.TestCase):

    def setUp(self):
        self.disclosure = create_disclosure(
            'AI 검색 엔진', ['김발명', '이공학'],
            'AI 기반 검색 엔진', 'GPT 활용 검색 시스템'
        )

    def test_create_disclosure(self):
        self.assertIsInstance(self.disclosure, InventionDisclosure)
        self.assertEqual(self.disclosure.title, 'AI 검색 엔진')
        self.assertEqual(len(self.disclosure.inventors), 2)

    def test_create_disclosure_empty_claims(self):
        self.assertEqual(self.disclosure.claims, [])
        self.assertEqual(self.disclosure.prior_art, [])

    def test_add_claim(self):
        updated = add_claim(self.disclosure, 'AI 모델 기반 검색 방법')
        self.assertEqual(len(updated.claims), 1)
        self.assertEqual(updated.claims[0], 'AI 모델 기반 검색 방법')

    def test_add_claim_multiple(self):
        d = add_claim(self.disclosure, '청구항 1')
        d = add_claim(d, '청구항 2')
        self.assertEqual(len(d.claims), 2)

    def test_add_prior_art(self):
        updated = add_prior_art(self.disclosure, 'Google BERT 논문 (2018)')
        self.assertEqual(len(updated.prior_art), 1)

    def test_validate_disclosure_valid(self):
        d = add_claim(self.disclosure, '청구항 1')
        errors = validate_disclosure(d)
        self.assertEqual(len(errors), 0)

    def test_validate_disclosure_missing_title(self):
        d = create_disclosure('', ['A'], 'abs', 'desc')
        d = add_claim(d, 'claim')
        errors = validate_disclosure(d)
        self.assertIn('제목이 비어 있습니다.', errors)

    def test_validate_disclosure_no_claims(self):
        errors = validate_disclosure(self.disclosure)
        self.assertIn('청구항이 없습니다.', errors)

    def test_export_disclosure_contains_sections(self):
        d = add_claim(self.disclosure, '청구항 1')
        d = add_prior_art(d, '참고문헌 1')
        text = export_disclosure(d)
        self.assertIn('AI 검색 엔진', text)
        self.assertIn('[초록]', text)
        self.assertIn('[청구항]', text)
        self.assertIn('참고문헌 1', text)

    def test_add_claim_immutable(self):
        add_claim(self.disclosure, '새 청구항')
        self.assertEqual(len(self.disclosure.claims), 0)

    def test_disclosure_has_filing_date(self):
        self.assertTrue(len(self.disclosure.filing_date) > 0)


if __name__ == '__main__':
    unittest.main()
