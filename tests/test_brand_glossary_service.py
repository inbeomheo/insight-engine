"""브랜드 용어집 서비스 테스트"""

import unittest

from services.brand_glossary_service import (
    GlossaryTerm,
    Glossary,
    add_term,
    search_term,
    check_content,
    export_glossary,
)


class TestAddTerm(unittest.TestCase):
    """add_term 함수 테스트"""

    def test_용어_추가(self):
        glossary = Glossary(glossary_id="g1")
        result = add_term(glossary, "인사이트 엔진", "AI 콘텐츠 생성 도구", "인사이트 엔진으로 콘텐츠 생성")
        self.assertEqual(len(result.terms), 1)
        self.assertEqual(result.terms[0].term, "인사이트 엔진")

    def test_금지_표현_포함(self):
        glossary = Glossary(glossary_id="g1")
        result = add_term(
            glossary, "인사이트 엔진", "도구",
            do_not_use=["인사이트엔진", "insight engine"]
        )
        self.assertEqual(len(result.terms[0].do_not_use), 2)

    def test_여러_용어_추가(self):
        glossary = Glossary(glossary_id="g1")
        glossary = add_term(glossary, "용어1", "정의1")
        glossary = add_term(glossary, "용어2", "정의2")
        self.assertEqual(len(glossary.terms), 2)


class TestSearchTerm(unittest.TestCase):
    """search_term 함수 테스트"""

    def setUp(self):
        self.glossary = Glossary(glossary_id="g1")
        self.glossary = add_term(self.glossary, "인사이트 엔진", "AI 콘텐츠 생성 도구")
        self.glossary = add_term(self.glossary, "파이프라인", "자동화 작업 흐름")

    def test_용어명_검색(self):
        results = search_term(self.glossary, "인사이트")
        self.assertEqual(len(results), 1)

    def test_정의_검색(self):
        results = search_term(self.glossary, "자동화")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].term, "파이프라인")

    def test_미매칭(self):
        results = search_term(self.glossary, "없는용어")
        self.assertEqual(len(results), 0)

    def test_대소문자_무시(self):
        self.glossary = add_term(self.glossary, "API", "Application Programming Interface")
        results = search_term(self.glossary, "api")
        self.assertEqual(len(results), 1)


class TestCheckContent(unittest.TestCase):
    """check_content 함수 테스트"""

    def test_금지_표현_감지(self):
        glossary = Glossary(glossary_id="g1")
        glossary = add_term(
            glossary, "인사이트 엔진", "도구",
            do_not_use=["인사이트엔진", "InsightEngine"]
        )
        violations = check_content(glossary, "인사이트엔진을 사용합니다")
        self.assertEqual(len(violations), 1)
        self.assertIn("인사이트 엔진", violations[0]["suggestion"])

    def test_위반_없음(self):
        glossary = Glossary(glossary_id="g1")
        glossary = add_term(glossary, "인사이트 엔진", "도구", do_not_use=["잘못된표현"])
        violations = check_content(glossary, "인사이트 엔진으로 콘텐츠를 생성합니다")
        self.assertEqual(len(violations), 0)

    def test_여러_금지_표현(self):
        glossary = Glossary(glossary_id="g1")
        glossary = add_term(glossary, "서비스", "제품", do_not_use=["프로그램", "소프트웨어"])
        violations = check_content(glossary, "이 프로그램은 소프트웨어입니다")
        self.assertEqual(len(violations), 2)


class TestExportGlossary(unittest.TestCase):
    """export_glossary 함수 테스트"""

    def test_마크다운_내보내기(self):
        glossary = Glossary(glossary_id="g1")
        glossary = add_term(glossary, "용어", "정의", "예시", ["금지1"])
        md = export_glossary(glossary)
        self.assertIn("# 브랜드 용어집", md)
        self.assertIn("## 용어", md)
        self.assertIn("**정의**: 정의", md)
        self.assertIn("**사용 금지**: 금지1", md)

    def test_빈_용어집(self):
        glossary = Glossary(glossary_id="g1")
        md = export_glossary(glossary)
        self.assertIn("# 브랜드 용어집", md)


if __name__ == "__main__":
    unittest.main()
