"""퀴즈 생성 서비스 테스트"""

import unittest
from services.quiz_generator_service import (
    QuizQuestion, Quiz,
    generate_quiz, grade_answer, calculate_results,
    VALID_DIFFICULTIES,
)


class TestGenerateQuiz(unittest.TestCase):
    """generate_quiz 테스트"""

    def setUp(self):
        self.content = (
            "인공지능은 컴퓨터 과학의 한 분야로 기계가 학습하는 것을 연구합니다.\n"
            "머신러닝은 데이터에서 패턴을 찾아 자동으로 학습하는 기술입니다.\n"
            "딥러닝은 신경망을 여러 층으로 쌓아 복잡한 패턴을 인식합니다.\n"
            "자연어처리는 컴퓨터가 인간의 언어를 이해하고 생성하는 기술입니다.\n"
            "컴퓨터 비전은 이미지와 영상을 분석하여 정보를 추출합니다."
        )

    def test_generate_returns_quiz(self):
        """Quiz 객체 반환"""
        quiz = generate_quiz(self.content, 3, "medium")
        self.assertIsInstance(quiz, Quiz)
        self.assertTrue(quiz.quiz_id.startswith("quiz_"))

    def test_generate_question_count(self):
        """요청한 문항 수 생성"""
        quiz = generate_quiz(self.content, 3, "medium")
        self.assertEqual(len(quiz.questions), 3)

    def test_generate_question_types_cycle(self):
        """문항 타입 순환 (MC → TF → SA)"""
        quiz = generate_quiz(self.content, 3, "easy")
        types = [q.question_type for q in quiz.questions]
        self.assertEqual(types[0], "multiple_choice")
        self.assertEqual(types[1], "true_false")
        self.assertEqual(types[2], "short_answer")

    def test_passing_score_by_difficulty(self):
        """난이도별 합격 점수"""
        easy = generate_quiz(self.content, 1, "easy")
        hard = generate_quiz(self.content, 1, "hard")
        self.assertEqual(easy.passing_score, 0.6)
        self.assertEqual(hard.passing_score, 0.8)

    def test_invalid_difficulty_raises(self):
        """유효하지 않은 난이도는 ValueError"""
        with self.assertRaises(ValueError):
            generate_quiz(self.content, 3, "impossible")

    def test_zero_questions_raises(self):
        """0 문항은 ValueError"""
        with self.assertRaises(ValueError):
            generate_quiz(self.content, 0, "medium")

    def test_empty_content_returns_empty(self):
        """빈 콘텐츠는 빈 퀴즈"""
        quiz = generate_quiz("", 5, "medium")
        self.assertEqual(len(quiz.questions), 0)

    def test_questions_have_ids(self):
        """모든 문항에 고유 ID"""
        quiz = generate_quiz(self.content, 3, "medium")
        ids = [q.question_id for q in quiz.questions]
        self.assertEqual(len(ids), len(set(ids)))


class TestGradeAnswer(unittest.TestCase):
    """grade_answer 테스트"""

    def test_correct_answer(self):
        """정답 채점"""
        q = QuizQuestion(
            question_id="q1",
            question_text="질문",
            question_type="multiple_choice",
            options=["A", "B"],
            correct_answer="A",
        )
        result = grade_answer(q, "A")
        self.assertTrue(result["correct"])
        self.assertEqual(result["score"], 1.0)

    def test_wrong_answer(self):
        """오답 채점"""
        q = QuizQuestion(
            question_id="q1",
            question_text="질문",
            question_type="multiple_choice",
            options=["A", "B"],
            correct_answer="A",
        )
        result = grade_answer(q, "B")
        self.assertFalse(result["correct"])
        self.assertEqual(result["score"], 0.0)

    def test_case_insensitive(self):
        """대소문자 무시"""
        q = QuizQuestion(
            question_id="q1",
            question_text="질문",
            question_type="true_false",
            options=["O", "X"],
            correct_answer="O",
        )
        result = grade_answer(q, "o")
        self.assertTrue(result["correct"])

    def test_short_answer_partial_score(self):
        """단답형 부분 점수"""
        q = QuizQuestion(
            question_id="q1",
            question_text="빈칸을 채우세요",
            question_type="short_answer",
            correct_answer="인공지능",
        )
        # 정답 포함 시 부분 점수
        result = grade_answer(q, "인공지능 기술")
        self.assertEqual(result["score"], 0.5)

    def test_grade_returns_explanation(self):
        """설명 포함"""
        q = QuizQuestion(
            question_id="q1",
            question_text="질문",
            question_type="true_false",
            correct_answer="O",
            explanation="설명 텍스트",
        )
        result = grade_answer(q, "O")
        self.assertEqual(result["explanation"], "설명 텍스트")


class TestCalculateResults(unittest.TestCase):
    """calculate_results 테스트"""

    def test_all_correct(self):
        """전부 정답"""
        quiz = Quiz(
            quiz_id="quiz1",
            title="테스트",
            questions=[
                QuizQuestion("q1", "질문1", "true_false", ["O", "X"], "O"),
                QuizQuestion("q2", "질문2", "true_false", ["O", "X"], "X"),
            ],
            passing_score=0.7,
        )
        answers = [
            {"question_id": "q1", "answer": "O"},
            {"question_id": "q2", "answer": "X"},
        ]
        results = calculate_results(quiz, answers)
        self.assertEqual(results["correct"], 2)
        self.assertEqual(results["score"], 1.0)
        self.assertTrue(results["passed"])

    def test_all_wrong(self):
        """전부 오답"""
        quiz = Quiz(
            quiz_id="quiz1",
            title="테스트",
            questions=[
                QuizQuestion("q1", "질문1", "true_false", ["O", "X"], "O"),
            ],
            passing_score=0.7,
        )
        answers = [{"question_id": "q1", "answer": "X"}]
        results = calculate_results(quiz, answers)
        self.assertEqual(results["correct"], 0)
        self.assertFalse(results["passed"])

    def test_empty_quiz(self):
        """빈 퀴즈"""
        quiz = Quiz(quiz_id="q", title="빈", questions=[], passing_score=0.7)
        results = calculate_results(quiz, [])
        self.assertEqual(results["total"], 0)

    def test_missing_answer_treated_as_wrong(self):
        """답안 누락은 오답 처리"""
        quiz = Quiz(
            quiz_id="quiz1",
            title="테스트",
            questions=[
                QuizQuestion("q1", "질문", "true_false", ["O", "X"], "O"),
            ],
            passing_score=0.7,
        )
        results = calculate_results(quiz, [])  # 답안 없음
        self.assertEqual(results["correct"], 0)

    def test_details_included(self):
        """상세 결과 포함"""
        quiz = Quiz(
            quiz_id="quiz1",
            title="테스트",
            questions=[
                QuizQuestion("q1", "질문", "true_false", ["O", "X"], "O"),
            ],
            passing_score=0.5,
        )
        answers = [{"question_id": "q1", "answer": "O"}]
        results = calculate_results(quiz, answers)
        self.assertEqual(len(results["details"]), 1)
        self.assertTrue(results["details"][0]["correct"])


if __name__ == "__main__":
    unittest.main()
