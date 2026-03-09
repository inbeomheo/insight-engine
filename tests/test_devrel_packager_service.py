"""DevRel 패키저 서비스 테스트"""

import unittest
from services.devrel_packager_service import (
    DevRelAsset, DevRelPackage,
    create_package, add_asset, assess_completeness, generate_readme,
)


class TestDevRelPackagerService(unittest.TestCase):
    """DevRel 패키저 서비스 테스트"""

    def test_create_package_basic(self):
        """기본 패키지 생성"""
        pkg = create_package("스타터 킷", "초보 개발자")
        self.assertEqual(pkg.name, "스타터 킷")
        self.assertEqual(pkg.target_audience, "초보 개발자")
        self.assertEqual(len(pkg.assets), 0)

    def test_create_package_empty_name(self):
        """빈 이름 거부"""
        with self.assertRaises(ValueError):
            create_package("", "대상")

    def test_create_package_with_version(self):
        """버전 지정"""
        pkg = create_package("킷", "대상", version="2.0.0")
        self.assertEqual(pkg.version, "2.0.0")

    def test_add_asset_tutorial(self):
        """튜토리얼 자산 추가"""
        pkg = create_package("킷", "대상")
        pkg = add_asset(pkg, {
            "type": "tutorial",
            "title": "시작하기",
            "content": "튜토리얼 내용",
            "language": "ko",
            "difficulty": "beginner",
        })
        self.assertEqual(len(pkg.assets), 1)
        self.assertEqual(pkg.assets[0].asset_type, "tutorial")

    def test_add_asset_invalid_type(self):
        """유효하지 않은 자산 타입"""
        pkg = create_package("킷", "대상")
        with self.assertRaises(ValueError):
            add_asset(pkg, {"type": "webinar"})

    def test_add_asset_invalid_difficulty(self):
        """유효하지 않은 난이도"""
        pkg = create_package("킷", "대상")
        with self.assertRaises(ValueError):
            add_asset(pkg, {"type": "tutorial", "difficulty": "expert"})

    def test_add_asset_multiple(self):
        """여러 자산 추가"""
        pkg = create_package("킷", "대상")
        for atype in ("tutorial", "sample_code", "blog_post"):
            pkg = add_asset(pkg, {"type": atype, "title": f"{atype} 자료", "content": "내용"})
        self.assertEqual(len(pkg.assets), 3)

    def test_assess_completeness_full(self):
        """완성된 패키지"""
        pkg = create_package("킷", "대상")
        for atype in ("tutorial", "sample_code", "sdk_doc"):
            pkg = add_asset(pkg, {"type": atype, "title": atype})
        result = assess_completeness(pkg)
        self.assertTrue(result["is_complete"])
        self.assertEqual(result["completeness_pct"], 100.0)
        self.assertEqual(result["missing_types"], [])

    def test_assess_completeness_partial(self):
        """부분 완성"""
        pkg = create_package("킷", "대상")
        pkg = add_asset(pkg, {"type": "tutorial", "title": "튜토리얼"})
        result = assess_completeness(pkg)
        self.assertFalse(result["is_complete"])
        self.assertIn("sample_code", result["missing_types"])
        self.assertIn("sdk_doc", result["missing_types"])

    def test_assess_completeness_empty(self):
        """빈 패키지"""
        pkg = create_package("킷", "대상")
        result = assess_completeness(pkg)
        self.assertFalse(result["is_complete"])
        self.assertEqual(result["completeness_pct"], 0.0)

    def test_generate_readme(self):
        """README 생성"""
        pkg = create_package("API 스타터 킷", "백엔드 개발자", "1.0.0")
        pkg = add_asset(pkg, {"type": "tutorial", "title": "시작하기", "language": "ko", "difficulty": "beginner"})
        readme = generate_readme(pkg)
        self.assertIn("# API 스타터 킷", readme)
        self.assertIn("1.0.0", readme)
        self.assertIn("백엔드 개발자", readme)
        self.assertIn("시작하기", readme)

    def test_generate_readme_empty(self):
        """빈 패키지 README"""
        pkg = create_package("킷", "대상")
        readme = generate_readme(pkg)
        self.assertIn("자료가 없습니다", readme)

    def test_add_asset_default_language(self):
        """기본 언어 ko"""
        pkg = create_package("킷", "대상")
        pkg = add_asset(pkg, {"type": "tutorial", "title": "제목"})
        self.assertEqual(pkg.assets[0].language, "ko")

    def test_add_asset_all_types(self):
        """모든 자산 타입"""
        pkg = create_package("킷", "대상")
        for atype in ("tutorial", "sample_code", "blog_post", "video", "sdk_doc"):
            pkg = add_asset(pkg, {"type": atype, "title": atype})
        self.assertEqual(len(pkg.assets), 5)


if __name__ == "__main__":
    unittest.main()
