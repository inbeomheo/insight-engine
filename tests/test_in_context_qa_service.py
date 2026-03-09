"""인컨텍스트 QA 서비스 테스트"""

import unittest

from services.in_context_qa_service import (
    QACheck,
    QAReport,
    check_consistency,
    check_grammar_basics,
    check_broken_references,
    run_qa,
)


class TestCheckConsistency(unittest.TestCase):
    """check_consistency 함수 테스트"""

    def test_혼용_감지(self):
        content = "인공지능과 AI를 활용한 서비스"
        checks = check_consistency(content)
        failed = [c for c in checks if not c.passed]
        self.assertGreater(len(failed), 0)

    def test_일관된_용어(self):
        content = "AI를 활용한 서비스. AI 기반 분석."
        checks = check_consistency(content)
        passed = [c for c in checks if c.passed]
        self.assertGreater(len(passed), 0)

    def test_여러_혼용_쌍(self):
        content = "인공지능 AI 머신러닝 기계학습"
        checks = check_consistency(content)
        failed = [c for c in checks if not c.passed]
        self.assertGreaterEqual(len(failed), 2)

    def test_빈_콘텐츠(self):
        checks = check_consistency("")
        self.assertGreater(len(checks), 0)
        self.assertTrue(checks[0].passed)


class TestCheckGrammarBasics(unittest.TestCase):
    """check_grammar_basics 함수 테스트"""

    def test_이중_공백_감지(self):
        content = "이것은  이중 공백입니다"
        checks = check_grammar_basics(content)
        failed = [c for c in checks if not c.passed]
        self.assertGreater(len(failed), 0)

    def test_이중_마침표_감지(self):
        content = "문장 끝.."
        checks = check_grammar_basics(content)
        failed = [c for c in checks if not c.passed]
        self.assertGreater(len(failed), 0)

    def test_말줄임표_허용(self):
        content = "생각해보면..."
        checks = check_grammar_basics(content)
        # ...은 이중 마침표로 간주하지 않음
        failed = [c for c in checks if not c.passed and "마침표" in c.details]
        self.assertEqual(len(failed), 0)

    def test_정상_텍스트(self):
        content = "깨끗한 문장입니다."
        checks = check_grammar_basics(content)
        passed = [c for c in checks if c.passed]
        self.assertGreater(len(passed), 0)


class TestCheckBrokenReferences(unittest.TestCase):
    """check_broken_references 함수 테스트"""

    def test_TODO_감지(self):
        content = "여기에 [TODO] 내용을 추가하세요"
        checks = check_broken_references(content)
        failed = [c for c in checks if not c.passed]
        self.assertGreater(len(failed), 0)

    def test_TBD_감지(self):
        content = "날짜: [TBD]"
        checks = check_broken_references(content)
        failed = [c for c in checks if not c.passed]
        self.assertGreater(len(failed), 0)

    def test_FIXME_감지(self):
        content = "[FIXME] 수정 필요"
        checks = check_broken_references(content)
        failed = [c for c in checks if not c.passed]
        self.assertGreater(len(failed), 0)

    def test_정상_콘텐츠(self):
        content = "완성된 문서입니다. 모든 내용이 채워져 있습니다."
        checks = check_broken_references(content)
        passed = [c for c in checks if c.passed]
        self.assertGreater(len(passed), 0)

    def test_TODO_콜론(self):
        content = "TODO: 이것을 나중에 수정"
        checks = check_broken_references(content)
        failed = [c for c in checks if not c.passed]
        self.assertGreater(len(failed), 0)


class TestRunQa(unittest.TestCase):
    """run_qa 함수 테스트"""

    def test_깨끗한_콘텐츠(self):
        content = "AI를 활용한 분석 서비스입니다. 좋은 결과를 제공합니다."
        report = run_qa(content)
        self.assertGreater(report.pass_rate, 0.5)

    def test_문제_많은_콘텐츠(self):
        content = "인공지능과 AI..  [TODO] 내용"
        report = run_qa(content)
        self.assertLess(report.pass_rate, 1.0)

    def test_critical_issues_카운트(self):
        content = "[TODO] [TBD] [FIXME]"
        report = run_qa(content)
        self.assertGreater(report.critical_issues, 0)

    def test_보고서_구조(self):
        report = run_qa("테스트 콘텐츠")
        self.assertIsInstance(report.checks, list)
        self.assertGreaterEqual(report.pass_rate, 0)
        self.assertLessEqual(report.pass_rate, 1.0)


if __name__ == "__main__":
    unittest.main()
