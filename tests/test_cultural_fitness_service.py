"""문화 적합성 서비스 테스트"""

import unittest

from services.cultural_fitness_service import (
    CulturalIssue,
    CulturalReport,
    check_idioms,
    check_date_format,
    check_taboo_topics,
    assess_fitness,
)


class TestCheckIdioms(unittest.TestCase):
    """check_idioms 함수 테스트"""

    def test_영어_관용구_한국_타깃(self):
        content = "This is a piece of cake for anyone."
        issues = check_idioms(content, "ko")
        self.assertGreater(len(issues), 0)
        self.assertEqual(issues[0].issue_type, "idiom")

    def test_한국어_관용구_영어_타깃(self):
        content = "눈치가 빠른 사람이 성공한다"
        issues = check_idioms(content, "en")
        self.assertGreater(len(issues), 0)

    def test_이슈_없음(self):
        content = "일반적인 기술 문서입니다."
        issues = check_idioms(content, "ko")
        self.assertEqual(len(issues), 0)

    def test_미등록_문화(self):
        content = "piece of cake"
        issues = check_idioms(content, "unknown")
        self.assertEqual(len(issues), 0)


class TestCheckDateFormat(unittest.TestCase):
    """check_date_format 함수 테스트"""

    def test_미국식_날짜_한국_타깃(self):
        content = "회의일: 03/15/2026"
        issues = check_date_format(content, "ko")
        self.assertGreater(len(issues), 0)

    def test_유럽식_날짜_한국_타깃(self):
        content = "회의일: 15.03.2026"
        issues = check_date_format(content, "ko")
        self.assertGreater(len(issues), 0)

    def test_한국식_날짜_정상(self):
        content = "회의일: 2026-03-15"
        issues = check_date_format(content, "ko")
        self.assertEqual(len(issues), 0)

    def test_유럽식_날짜_미국_타깃(self):
        content = "Date: 15.03.2026"
        issues = check_date_format(content, "en")
        self.assertGreater(len(issues), 0)

    def test_미국식_날짜_일본_타깃(self):
        content = "日程: 03/15/2026"
        issues = check_date_format(content, "ja")
        self.assertGreater(len(issues), 0)


class TestCheckTabooTopics(unittest.TestCase):
    """check_taboo_topics 함수 테스트"""

    def test_금기_주제_감지(self):
        content = "정치적 편향이 있는 콘텐츠"
        issues = check_taboo_topics(content, "ko")
        self.assertGreater(len(issues), 0)
        self.assertEqual(issues[0].issue_type, "taboo")

    def test_금기_없음(self):
        content = "기술 관련 콘텐츠입니다."
        issues = check_taboo_topics(content, "ko")
        self.assertEqual(len(issues), 0)


class TestAssessFitness(unittest.TestCase):
    """assess_fitness 함수 테스트"""

    def test_적합한_콘텐츠(self):
        content = "일반적인 기술 문서입니다."
        report = assess_fitness(content, "ko")
        self.assertEqual(report.fitness_score, 1.0)
        self.assertEqual(len(report.issues), 0)

    def test_이슈_있는_콘텐츠(self):
        content = "This is a piece of cake. 회의일: 03/15/2026"
        report = assess_fitness(content, "ko")
        self.assertLess(report.fitness_score, 1.0)
        self.assertGreater(len(report.issues), 0)

    def test_점수_범위(self):
        content = "piece of cake break a leg raining cats and dogs 03/15/2026 정치적 편향 종교 비하"
        report = assess_fitness(content, "ko")
        self.assertGreaterEqual(report.fitness_score, 0.0)
        self.assertLessEqual(report.fitness_score, 1.0)

    def test_보고서_문화권(self):
        report = assess_fitness("test", "en")
        self.assertEqual(report.target_culture, "en")


if __name__ == "__main__":
    unittest.main()
