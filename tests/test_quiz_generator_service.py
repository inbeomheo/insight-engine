"""quiz_generator_service 단위 테스트"""
import unittest

from services.quiz_generator_service import (
    generate_quiz,
    _extract_key_sentences,
    _generate_wrong_options,
)


class TestGenerateQuiz(unittest.TestCase):

    def test_empty_content(self):
        result = generate_quiz('')
        self.assertEqual(result['total_questions'], 0)
        self.assertEqual(result['questions'], [])

    def test_none_content(self):
        result = generate_quiz(None)
        self.assertEqual(result['total_questions'], 0)

    def test_generates_questions(self):
        content = """
        # 파이썬 프로그래밍 가이드

        파이썬은 1991년에 귀도 반 로섬이 개발한 프로그래밍 언어입니다.
        파이썬의 문법은 간결하고 읽기 쉬워서 초보자에게 적합합니다.
        전 세계 개발자의 약 30%가 파이썬을 주력 언어로 사용합니다.
        데이터 과학, 웹 개발, 인공지능 분야에서 널리 활용됩니다.
        파이썬 생태계에는 20만개 이상의 패키지가 등록되어 있습니다.
        최신 버전은 성능이 크게 향상되었고 타입 힌트를 지원합니다.
        """
        result = generate_quiz(content, count=5)
        self.assertGreater(result['total_questions'], 0)
        self.assertLessEqual(result['total_questions'], 5)
        self.assertIsInstance(result['quiz_id'], str)
        self.assertTrue(len(result['quiz_id']) > 0)

    def test_question_structure(self):
        content = '파이썬은 간결한 문법을 가진 프로그래밍 언어입니다. 데이터 분석에 널리 사용됩니다.'
        result = generate_quiz(content, count=3)
        for q in result['questions']:
            self.assertIn('id', q)
            self.assertIn('type', q)
            self.assertIn('question', q)
            self.assertIn('answer', q)
            self.assertIn(q['type'], ('multiple_choice', 'true_false', 'fill_blank'))

    def test_count_limit(self):
        content = '문장1입니다 내용이 풍부합니다. ' * 20
        result = generate_quiz(content, count=3)
        self.assertLessEqual(result['total_questions'], 3)

    def test_max_count_cap(self):
        content = '문장입니다 길이를 맞추기 위한 내용입니다. ' * 30
        result = generate_quiz(content, count=20)
        self.assertLessEqual(result['total_questions'], 10)


class TestExtractKeySentences(unittest.TestCase):

    def test_filters_short_sentences(self):
        sentences = _extract_key_sentences('짧다. 이것은 충분히 긴 문장으로 핵심 정보를 담고 있습니다.')
        self.assertTrue(all(len(s) >= 15 for s in sentences))

    def test_filters_skip_patterns(self):
        text = '참고: 이것은 참고입니다. 이것은 중요한 핵심 내용을 담은 문장입니다.'
        sentences = _extract_key_sentences(text)
        self.assertTrue(all(not s.startswith('참고:') for s in sentences))


class TestGenerateWrongOptions(unittest.TestCase):

    def test_generates_options(self):
        options = _generate_wrong_options('파이썬은 인기 있는 프로그래밍 언어입니다')
        self.assertGreater(len(options), 0)
        self.assertLessEqual(len(options), 3)

    def test_number_variant(self):
        options = _generate_wrong_options('사용자가 100명 참여했습니다')
        self.assertGreater(len(options), 0)


if __name__ == '__main__':
    unittest.main()
