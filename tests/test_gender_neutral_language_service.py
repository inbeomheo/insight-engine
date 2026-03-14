"""Gender-Neutral Language Checker 서비스 테스트."""
import unittest
from services.analysis.gender_neutral_language_service import check_gender_neutral


class TestGenderNeutralLanguage(unittest.TestCase):

    def test_empty_content(self):
        result = check_gender_neutral('')
        self.assertEqual(result['score'], 100.0)
        self.assertEqual(result['summary']['total_issues'], 0)

    def test_none_content(self):
        result = check_gender_neutral(None)
        self.assertEqual(result['score'], 100.0)

    def test_inclusive_content(self):
        content = '직원들이 회의에 참석했습니다. 교사가 수업을 진행합니다.'
        result = check_gender_neutral(content)
        self.assertEqual(result['summary']['total_issues'], 0)
        self.assertEqual(result['summary']['level'], 'inclusive')

    def test_korean_gendered_employee(self):
        content = '여직원이 프레젠테이션을 잘 했습니다.'
        result = check_gender_neutral(content)
        self.assertGreater(result['summary']['ko_issues'], 0)

    def test_korean_gendered_doctor(self):
        content = '여의사 선생님이 진료를 합니다.'
        result = check_gender_neutral(content)
        self.assertGreater(result['summary']['ko_issues'], 0)

    def test_korean_gendered_debut(self):
        content = '이것은 그 작가의 처녀작입니다.'
        result = check_gender_neutral(content)
        self.assertGreater(result['summary']['ko_issues'], 0)

    def test_english_gendered(self):
        content = 'The chairman called the meeting. The fireman arrived quickly.'
        result = check_gender_neutral(content)
        self.assertGreater(result['summary']['en_issues'], 0)

    def test_english_mankind(self):
        content = 'This is a great achievement for mankind.'
        result = check_gender_neutral(content)
        self.assertGreater(result['summary']['en_issues'], 0)

    def test_alternative_provided(self):
        content = '여직원이 보고서를 작성했습니다.'
        result = check_gender_neutral(content)
        self.assertGreater(len(result['findings']), 0)
        self.assertIn('alternative', result['findings'][0])

    def test_score_decreases_with_issues(self):
        clean = '직원이 회의에 참석했습니다.'
        dirty = '여직원이 회의에 참석했습니다. 남직원은 외근입니다.'
        clean_result = check_gender_neutral(clean)
        dirty_result = check_gender_neutral(dirty)
        self.assertGreater(clean_result['score'], dirty_result['score'])

    def test_level_significant(self):
        content = ('여직원이 보고합니다. 여의사가 진료합니다. '
                   '여교사가 수업합니다. 처녀작을 발표합니다. '
                   '여류 작가가 등장합니다. 여걸로 불립니다. 아줌마가 옵니다.')
        result = check_gender_neutral(content)
        self.assertEqual(result['summary']['level'], 'significant')

    def test_score_range(self):
        content = '일반적인 콘텐츠입니다.'
        result = check_gender_neutral(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_return_structure(self):
        content = '구조 확인입니다.'
        result = check_gender_neutral(content)
        self.assertIn('findings', result)
        self.assertIn('summary', result)
        self.assertIn('score', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_issues', result['summary'])
        self.assertIn('ko_issues', result['summary'])
        self.assertIn('en_issues', result['summary'])
        self.assertIn('level', result['summary'])

    def test_suggestions_for_issues(self):
        content = 'The chairman announced the policy.'
        result = check_gender_neutral(content)
        self.assertGreater(len(result['suggestions']), 0)


if __name__ == '__main__':
    unittest.main()
