"""라이선싱 코파일럿 서비스 테스트"""

import unittest
from services.licensing_copilot_service import (
    License, LicenseCheck,
    identify_license, check_compatibility, suggest_license, generate_attribution,
)


class TestLicensingCopilotService(unittest.TestCase):
    """라이선싱 코파일럿 서비스 테스트"""

    def test_identify_license_cc_by(self):
        """CC BY 식별"""
        lic = identify_license("This work is licensed under CC BY 4.0")
        self.assertEqual(lic.license_type, "CC-BY")

    def test_identify_license_cc_by_sa(self):
        """CC BY-SA 식별 (CC BY보다 우선)"""
        lic = identify_license("Licensed under CC BY-SA 4.0")
        self.assertEqual(lic.license_type, "CC-BY-SA")

    def test_identify_license_cc_by_nc(self):
        """CC BY-NC 식별"""
        lic = identify_license("CC BY-NC 3.0 License")
        self.assertEqual(lic.license_type, "CC-BY-NC")

    def test_identify_license_mit(self):
        """MIT 라이선스 식별"""
        lic = identify_license("Released under the MIT License")
        self.assertEqual(lic.license_type, "MIT")

    def test_identify_license_public_domain(self):
        """퍼블릭 도메인 식별"""
        lic = identify_license("CC0 Public Domain")
        self.assertEqual(lic.license_type, "public_domain")

    def test_identify_license_proprietary(self):
        """독점 라이선스 식별"""
        lic = identify_license("All Rights Reserved")
        self.assertEqual(lic.license_type, "proprietary")

    def test_identify_license_unknown_default(self):
        """매칭 없으면 proprietary"""
        lic = identify_license("어떤 텍스트")
        self.assertEqual(lic.license_type, "proprietary")

    def test_check_compatibility_compatible(self):
        """호환 라이선스"""
        l1 = identify_license("CC BY")
        l2 = identify_license("CC BY-SA")
        result = check_compatibility([l1, l2])
        self.assertTrue(result.compatible)
        self.assertEqual(result.issues, [])

    def test_check_compatibility_incompatible(self):
        """비호환 라이선스"""
        l1 = identify_license("CC BY-NC")
        l2 = identify_license("CC BY")
        result = check_compatibility([l1, l2])
        self.assertFalse(result.compatible)
        self.assertTrue(len(result.issues) > 0)

    def test_check_compatibility_single(self):
        """단일 라이선스"""
        lic = identify_license("MIT License")
        result = check_compatibility([lic])
        self.assertTrue(result.compatible)

    def test_check_compatibility_proprietary_blocks(self):
        """독점 + 다른 라이선스 = 비호환"""
        l1 = identify_license("All Rights Reserved")
        l2 = identify_license("MIT License")
        result = check_compatibility([l1, l2])
        self.assertFalse(result.compatible)

    def test_suggest_license_commercial(self):
        """상업적 용도 → MIT"""
        lic = suggest_license("상업적 판매 목적")
        self.assertEqual(lic.license_type, "MIT")

    def test_suggest_license_open_source(self):
        """오픈소스 → CC-BY-SA"""
        lic = suggest_license("오픈소스 공유")
        self.assertEqual(lic.license_type, "CC-BY-SA")

    def test_suggest_license_education(self):
        """교육 → CC-BY-NC"""
        lic = suggest_license("교육 목적 비영리")
        self.assertEqual(lic.license_type, "CC-BY-NC")

    def test_suggest_license_default(self):
        """기본 → CC-BY"""
        lic = suggest_license("일반적인 블로그")
        self.assertEqual(lic.license_type, "CC-BY")

    def test_generate_attribution_cc(self):
        """CC 저작자 표시"""
        lic = identify_license("CC BY 4.0")
        attr = generate_attribution(lic, "작성자A")
        self.assertIn("작성자A", attr)
        self.assertIn("CC BY", attr)

    def test_generate_attribution_mit(self):
        """MIT 저작자 표시"""
        lic = identify_license("MIT License")
        attr = generate_attribution(lic, "DevTeam")
        self.assertIn("DevTeam", attr)
        self.assertIn("MIT", attr)

    def test_generate_attribution_public_domain(self):
        """퍼블릭 도메인 표시"""
        lic = identify_license("Public Domain")
        attr = generate_attribution(lic, "Author")
        self.assertIn("퍼블릭 도메인", attr)

    def test_generate_attribution_proprietary(self):
        """독점 라이선스 표시"""
        lic = identify_license("All Rights Reserved")
        attr = generate_attribution(lic, "Company")
        self.assertIn("All Rights Reserved", attr)

    def test_identify_license_case_insensitive(self):
        """대소문자 무관 식별"""
        lic = identify_license("licensed under mit license")
        self.assertEqual(lic.license_type, "MIT")


if __name__ == "__main__":
    unittest.main()
