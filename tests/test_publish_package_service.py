"""publish_package_service 단위 테스트"""
import json
import unittest

from services.publish_package_service import (
    PublishPackage,
    ValidationError,
    build_package,
    validate_package,
    export_package,
)


SAMPLE_CONTENT = """# AI 기술 동향

인공지능 기술이 빠르게 발전하고 있다. 특히 대규모 언어 모델(LLM)은 다양한 산업에서 활용되고 있다.

## 주요 활용 분야

자연어 처리, 이미지 생성, 코드 작성 등이 대표적이다.

LLM을 어떻게 활용할 수 있을까?

실무에서는 고객 서비스 자동화와 콘텐츠 생성에 주로 사용된다. 데이터 분석 자동화도 가능하다.
"""


class TestBuildPackage(unittest.TestCase):
    """기본 패키지 생성"""

    def test_build_package(self):
        """콘텐츠에서 패키지 조립"""
        pkg = build_package(SAMPLE_CONTENT)

        self.assertIsInstance(pkg, PublishPackage)
        self.assertTrue(len(pkg.title) > 0)
        self.assertTrue(len(pkg.meta_description) > 0)
        self.assertTrue(len(pkg.body_html) > 0)
        self.assertEqual(pkg.schema_version, "1.0")
        self.assertIsInstance(pkg.faq, list)
        self.assertIsInstance(pkg.sns_copies, dict)
        self.assertIsInstance(pkg.tags, list)


class TestBuildPackageWithTitle(unittest.TestCase):
    """제목 지정"""

    def test_build_package_with_title(self):
        """명시적 제목 사용"""
        pkg = build_package(SAMPLE_CONTENT, title="커스텀 제목")
        self.assertEqual(pkg.title, "커스텀 제목")

    def test_build_package_auto_title(self):
        """제목 미지정 시 첫 줄에서 추출"""
        pkg = build_package(SAMPLE_CONTENT)
        # 마크다운 헤딩 기호 제거된 제목
        self.assertEqual(pkg.title, "AI 기술 동향")

    def test_build_package_with_tags(self):
        """태그 지정"""
        tags = ["AI", "LLM", "기술"]
        pkg = build_package(SAMPLE_CONTENT, tags=tags)
        self.assertEqual(pkg.tags, tags)


class TestBuildPackageMetaLength(unittest.TestCase):
    """메타설명 160자 제한"""

    def test_build_package_meta_length(self):
        """메타설명이 160자 이내"""
        pkg = build_package(SAMPLE_CONTENT)
        self.assertLessEqual(len(pkg.meta_description), 160)

    def test_meta_description_long_content(self):
        """긴 콘텐츠에서도 160자 이내 보장"""
        long_content = "가나다라마바사. " * 100
        pkg = build_package(long_content)
        self.assertLessEqual(len(pkg.meta_description), 160)

    def test_meta_description_short_content(self):
        """짧은 콘텐츠는 그대로"""
        short = "짧은 콘텐츠입니다."
        pkg = build_package(short)
        self.assertIn("짧은 콘텐츠", pkg.meta_description)


class TestBuildPackageSnsCopies(unittest.TestCase):
    """SNS 카피 생성"""

    def test_build_package_sns_copies(self):
        """4개 플랫폼 카피 생성"""
        pkg = build_package(SAMPLE_CONTENT)

        self.assertIn("twitter", pkg.sns_copies)
        self.assertIn("linkedin", pkg.sns_copies)
        self.assertIn("instagram", pkg.sns_copies)
        self.assertIn("threads", pkg.sns_copies)

    def test_twitter_copy_length(self):
        """트위터 카피 280자 이내"""
        pkg = build_package(SAMPLE_CONTENT * 5)
        self.assertLessEqual(len(pkg.sns_copies["twitter"]), 280)

    def test_linkedin_copy_length(self):
        """링크드인 카피 700자 이내"""
        pkg = build_package(SAMPLE_CONTENT * 5)
        self.assertLessEqual(len(pkg.sns_copies["linkedin"]), 700)


class TestValidatePackageValid(unittest.TestCase):
    """유효 패키지 검증"""

    def test_validate_package_valid(self):
        """정상 패키지 → 에러 없음"""
        pkg = build_package(SAMPLE_CONTENT, title="테스트 제목")
        errors = validate_package(pkg)

        error_severities = [e.severity for e in errors]
        self.assertNotIn("error", error_severities)


class TestValidatePackageMissingTitle(unittest.TestCase):
    """제목 누락 검증"""

    def test_validate_package_missing_title(self):
        """제목 빈 문자열 → error"""
        pkg = PublishPackage(
            title="",
            meta_description="메타설명",
            body_html="<p>본문</p>",
        )
        errors = validate_package(pkg)

        title_errors = [e for e in errors if e.field == "title"]
        self.assertTrue(len(title_errors) > 0)
        self.assertEqual(title_errors[0].severity, "error")

    def test_validate_package_missing_body(self):
        """본문 빈 문자열 → error"""
        pkg = PublishPackage(
            title="제목",
            meta_description="메타",
            body_html="",
        )
        errors = validate_package(pkg)

        body_errors = [e for e in errors if e.field == "body_html"]
        self.assertTrue(len(body_errors) > 0)


class TestValidatePackageMetaTooLong(unittest.TestCase):
    """메타설명 초과 검증"""

    def test_validate_package_meta_too_long(self):
        """메타설명 161자 이상 → error"""
        pkg = PublishPackage(
            title="제목",
            meta_description="가" * 200,
            body_html="<p>본문</p>",
        )
        errors = validate_package(pkg)

        meta_errors = [e for e in errors if e.field == "meta_description"]
        self.assertTrue(len(meta_errors) > 0)
        self.assertEqual(meta_errors[0].severity, "error")

    def test_validate_package_faq_invalid_format(self):
        """FAQ 항목에 q/a 키 누락 → error"""
        pkg = PublishPackage(
            title="제목",
            meta_description="메타",
            body_html="<p>본문</p>",
            faq=[{"question": "잘못된 키"}],
        )
        errors = validate_package(pkg)

        faq_errors = [e for e in errors if e.field == "faq"]
        self.assertTrue(len(faq_errors) > 0)


class TestExportPackageJson(unittest.TestCase):
    """JSON 내보내기"""

    def test_export_package_json(self):
        """JSON 형식 직렬화"""
        pkg = build_package(SAMPLE_CONTENT, title="내보내기 테스트")
        exported = export_package(pkg, format="json")

        # 유효한 JSON인지 확인
        data = json.loads(exported)
        self.assertEqual(data["title"], "내보내기 테스트")
        self.assertEqual(data["schema_version"], "1.0")
        self.assertIn("meta_description", data)
        self.assertIn("body_html", data)
        self.assertIn("faq", data)
        self.assertIn("sns_copies", data)
        self.assertIn("tags", data)

    def test_export_package_unsupported_format(self):
        """지원하지 않는 형식 → ValueError"""
        pkg = build_package("콘텐츠")
        with self.assertRaises(ValueError) as ctx:
            export_package(pkg, format="xml")
        self.assertIn("xml", str(ctx.exception))

    def test_export_roundtrip(self):
        """JSON 내보내기 → 파싱 → 필드 일치"""
        tags = ["태그1", "태그2"]
        pkg = build_package(SAMPLE_CONTENT, title="라운드트립", tags=tags)
        data = json.loads(export_package(pkg))

        self.assertEqual(data["title"], "라운드트립")
        self.assertEqual(data["tags"], tags)
        self.assertIsInstance(data["faq"], list)
        self.assertIsInstance(data["sns_copies"], dict)


class TestBuildPackageEdgeCases(unittest.TestCase):
    """엣지 케이스"""

    def test_empty_content(self):
        """빈 콘텐츠로 패키지 생성"""
        pkg = build_package("")
        self.assertEqual(pkg.title, "")
        self.assertEqual(pkg.meta_description, "")

    def test_faq_extraction(self):
        """질문형 문장이 포함된 콘텐츠에서 FAQ 추출"""
        content = "AI란 무엇인가? 딥러닝은 어떻게 작동하는가?"
        pkg = build_package(content)
        self.assertTrue(len(pkg.faq) > 0)
        self.assertIn("q", pkg.faq[0])
        self.assertIn("a", pkg.faq[0])


if __name__ == "__main__":
    unittest.main()
