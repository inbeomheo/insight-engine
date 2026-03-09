"""웨비나 캡처 서비스 테스트"""
import unittest
from services.webinar_capture_service import (
    capture_webinar, extract_qa, generate_highlights, WebinarCapture
)


class TestWebinarCaptureService(unittest.TestCase):

    def setUp(self):
        self.transcript = (
            "오늘 AI 트렌드에 대해 이야기합니다. "
            "AI가 미래를 어떻게 바꿀까요? 데이터가 핵심입니다. "
            "질문 있으신가요? 네, 보안 문제가 중요합니다. "
            "결론적으로 AI는 필수 기술입니다."
        )
        self.speakers = ['김박사', '이교수']

    def test_capture_webinar_basic(self):
        result = capture_webinar('AI 세미나', self.speakers, self.transcript, 60)
        self.assertIsInstance(result, WebinarCapture)
        self.assertEqual(result.title, 'AI 세미나')
        self.assertEqual(result.speakers, self.speakers)
        self.assertEqual(result.duration_min, 60)

    def test_capture_key_moments_question(self):
        result = capture_webinar('테스트', ['A'], self.transcript, 30)
        questions = [m for m in result.key_moments if m['type'] == 'question']
        self.assertGreater(len(questions), 0)

    def test_capture_key_moments_conclusion(self):
        result = capture_webinar('테스트', ['A'], self.transcript, 30)
        conclusions = [m for m in result.key_moments if m['type'] == 'conclusion']
        self.assertGreater(len(conclusions), 0)

    def test_capture_summary_not_empty(self):
        result = capture_webinar('테스트', ['A'], self.transcript, 30)
        self.assertTrue(len(result.summary) > 0)

    def test_extract_qa_finds_pairs(self):
        qa = extract_qa(self.transcript)
        self.assertGreater(len(qa), 0)
        self.assertIn('question', qa[0])
        self.assertIn('answer', qa[0])

    def test_extract_qa_empty_transcript(self):
        qa = extract_qa('아무 질문도 없는 텍스트')
        self.assertEqual(len(qa), 0)

    def test_generate_highlights_limit(self):
        capture = capture_webinar('테스트', ['A'], self.transcript, 30)
        highlights = generate_highlights(capture, 2)
        self.assertLessEqual(len(highlights), 2)

    def test_generate_highlights_questions_first(self):
        capture = capture_webinar('테스트', ['A'], self.transcript, 30)
        highlights = generate_highlights(capture, 10)
        if highlights:
            # 질문 타입이 우선
            question_indices = [i for i, h in enumerate(highlights) if h['type'] == 'question']
            conclusion_indices = [i for i, h in enumerate(highlights) if h['type'] == 'conclusion']
            if question_indices and conclusion_indices:
                self.assertLess(max(question_indices), min(conclusion_indices))

    def test_capture_webinar_unique_id(self):
        r1 = capture_webinar('A', [], 'text', 10)
        r2 = capture_webinar('B', [], 'text', 10)
        self.assertNotEqual(r1.capture_id, r2.capture_id)

    def test_capture_empty_transcript(self):
        result = capture_webinar('빈', ['A'], '', 0)
        self.assertEqual(result.key_moments, [])
        self.assertEqual(result.q_and_a, [])


if __name__ == '__main__':
    unittest.main()
