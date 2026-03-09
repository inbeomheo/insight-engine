"""마이크로러닝 서비스 테스트"""

import unittest

from services.microlearning_service import (
    MicroLesson,
    MicroCourse,
    split_into_lessons,
    add_quiz,
    reorder_lessons,
    estimate_completion,
)


class TestSplitIntoLessons(unittest.TestCase):
    """split_into_lessons 함수 테스트"""

    def test_기본_분할(self):
        # 충분히 긴 콘텐츠 (단락 2개)
        content = "첫 번째 단락입니다. " * 100 + "\n\n" + "두 번째 단락입니다. " * 100
        course = split_into_lessons(content, max_duration_min=3.0)
        self.assertGreater(len(course.lessons), 0)
        self.assertGreater(course.total_duration, 0)

    def test_짧은_콘텐츠_단일_레슨(self):
        content = "짧은 콘텐츠"
        course = split_into_lessons(content, max_duration_min=5.0)
        self.assertEqual(len(course.lessons), 1)

    def test_빈_콘텐츠(self):
        course = split_into_lessons("", max_duration_min=5.0)
        self.assertEqual(len(course.lessons), 0)
        self.assertEqual(course.total_duration, 0.0)

    def test_레슨_순서(self):
        content = "단락1\n\n단락2\n\n단락3"
        course = split_into_lessons(content)
        for i, lesson in enumerate(course.lessons):
            self.assertEqual(lesson.order, i + 1)

    def test_레슨_학습목표_생성(self):
        content = "충분한 길이의 콘텐츠입니다. " * 50
        course = split_into_lessons(content)
        for lesson in course.lessons:
            self.assertGreater(len(lesson.learning_objective), 0)

    def test_총_시간_일치(self):
        content = "단락1 " * 100 + "\n\n" + "단락2 " * 100
        course = split_into_lessons(content)
        calculated_total = sum(l.duration_min for l in course.lessons)
        self.assertAlmostEqual(course.total_duration, calculated_total, places=1)


class TestAddQuiz(unittest.TestCase):
    """add_quiz 함수 테스트"""

    def test_퀴즈_추가(self):
        lesson = MicroLesson(lesson_id="l1", title="레슨1", content="내용")
        result = add_quiz(lesson, "퀴즈 질문?")
        self.assertEqual(result.quiz_question, "퀴즈 질문?")
        self.assertEqual(result.lesson_id, "l1")

    def test_원본_보존(self):
        lesson = MicroLesson(lesson_id="l1", title="레슨1", content="내용", duration_min=3.0)
        result = add_quiz(lesson, "Q?")
        self.assertEqual(result.title, "레슨1")
        self.assertEqual(result.content, "내용")
        self.assertEqual(result.duration_min, 3.0)


class TestReorderLessons(unittest.TestCase):
    """reorder_lessons 함수 테스트"""

    def test_순서_변경(self):
        lessons = [
            MicroLesson(lesson_id="a", title="A", order=1),
            MicroLesson(lesson_id="b", title="B", order=2),
            MicroLesson(lesson_id="c", title="C", order=3),
        ]
        course = MicroCourse(course_id="c1", lessons=lessons, total_duration=10)
        result = reorder_lessons(course, ["c", "a", "b"])
        self.assertEqual(result.lessons[0].lesson_id, "c")
        self.assertEqual(result.lessons[1].lesson_id, "a")
        self.assertEqual(result.lessons[2].lesson_id, "b")

    def test_순서_번호_업데이트(self):
        lessons = [
            MicroLesson(lesson_id="a", order=1),
            MicroLesson(lesson_id="b", order=2),
        ]
        course = MicroCourse(course_id="c1", lessons=lessons)
        result = reorder_lessons(course, ["b", "a"])
        self.assertEqual(result.lessons[0].order, 1)
        self.assertEqual(result.lessons[1].order, 2)

    def test_누락_레슨_뒤에_추가(self):
        lessons = [
            MicroLesson(lesson_id="a", order=1),
            MicroLesson(lesson_id="b", order=2),
        ]
        course = MicroCourse(course_id="c1", lessons=lessons)
        result = reorder_lessons(course, ["a"])  # b 누락
        self.assertEqual(len(result.lessons), 2)


class TestEstimateCompletion(unittest.TestCase):
    """estimate_completion 함수 테스트"""

    def test_기본_속도(self):
        course = MicroCourse(total_duration=60.0)
        time = estimate_completion(course)
        self.assertEqual(time, 60.0)

    def test_2배속(self):
        course = MicroCourse(total_duration=60.0)
        time = estimate_completion(course, speed_factor=2.0)
        self.assertEqual(time, 30.0)

    def test_0_속도_기본값(self):
        course = MicroCourse(total_duration=60.0)
        time = estimate_completion(course, speed_factor=0)
        self.assertEqual(time, 60.0)

    def test_빈_코스(self):
        course = MicroCourse(total_duration=0.0)
        time = estimate_completion(course)
        self.assertEqual(time, 0.0)


if __name__ == "__main__":
    unittest.main()
