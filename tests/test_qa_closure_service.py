"""
질문-답변 완결성 검사 서비스 테스트
"""
import unittest
from services.qa_closure_service import check_qa_closure


class TestQaClosureService(unittest.TestCase):
    """check_qa_closure 함수 단위 테스트"""

    def test_empty_content(self):
        """빈 콘텐츠 입력 시 기본 결과를 반환한다."""
        result = check_qa_closure('')
        self.assertEqual(result['questions'], [])
        self.assertEqual(result['summary']['total_questions'], 0)
        self.assertEqual(result['closure_score'], 100.0)
        self.assertIn('콘텐츠가 비어 있습니다.', result['suggestions'])

        # None 입력도 동일하게 처리
        result_none = check_qa_closure(None)
        self.assertEqual(result_none['questions'], [])

    def test_no_questions(self):
        """질문이 없는 콘텐츠에서는 빈 질문 목록을 반환한다."""
        content = (
            "## 프로젝트 소개\n"
            "이 프로젝트는 웹 애플리케이션입니다.\n"
            "React와 TypeScript를 사용합니다.\n"
        )
        result = check_qa_closure(content)
        self.assertEqual(len(result['questions']), 0)
        self.assertEqual(result['summary']['total_questions'], 0)
        self.assertEqual(result['closure_score'], 100.0)

    def test_heading_question_detection(self):
        """마크다운 헤딩의 질문형을 정확히 감지한다."""
        content = (
            "## React란 무엇인가요?\n"
            "React는 UI 라이브러리입니다.\n"
            "\n"
            "## 설치 방법\n"
            "npm install로 설치합니다.\n"
            "\n"
            "### TypeScript를 사용할까요?\n"
            "네, TypeScript 사용을 권장합니다.\n"
        )
        result = check_qa_closure(content)
        heading_qs = [q for q in result['questions'] if q['source'] == 'heading']
        self.assertEqual(len(heading_qs), 2)
        # "설치 방법"은 질문형이 아니므로 감지되지 않아야 함
        q_texts = [q['question'] for q in heading_qs]
        self.assertIn('React란 무엇인가요?', q_texts)
        self.assertIn('TypeScript를 사용할까요?', q_texts)
        self.assertNotIn('설치 방법', q_texts)

    def test_body_question_detection(self):
        """본문 내 질문 문장을 감지한다."""
        content = (
            "## 개요\n"
            "이 기능을 어떻게 구현할까?\n"
            "먼저 설계를 해야 합니다.\n"
        )
        result = check_qa_closure(content)
        body_qs = [q for q in result['questions'] if q['source'] == 'body']
        self.assertTrue(len(body_qs) >= 1)
        self.assertEqual(body_qs[0]['question'], '이 기능을 어떻게 구현할까?')

    def test_answered_question(self):
        """질문 뒤에 답변이 있으면 answered로 표시한다."""
        content = (
            "## Python이란 무엇인가요?\n"
            "Python은 범용 프로그래밍 언어입니다.\n"
            "간결한 문법이 특징입니다.\n"
        )
        result = check_qa_closure(content)
        self.assertTrue(len(result['questions']) >= 1)
        q = result['questions'][0]
        self.assertTrue(q['has_answer'])
        self.assertEqual(q['status'], 'answered')
        self.assertIn('입니다', q['answer_excerpt'])

    def test_unanswered_question(self):
        """질문 뒤에 답변이 없으면 unanswered로 표시한다."""
        content = (
            "## API 키는 어디서 발급받나요?\n"
            "\n"
            "## 다음 단계\n"
            "배포 준비를 진행합니다.\n"
        )
        result = check_qa_closure(content)
        self.assertTrue(len(result['questions']) >= 1)
        q = result['questions'][0]
        self.assertFalse(q['has_answer'])
        self.assertEqual(q['status'], 'unanswered')

    def test_closure_score_range(self):
        """closure_score는 항상 0~100 범위여야 한다."""
        # 전부 미답변 → 0점
        content_no_answer = (
            "## 왜 느린가?\n"
            "\n"
            "## 왜 안 되는가?\n"
            "\n"
        )
        result_0 = check_qa_closure(content_no_answer)
        self.assertEqual(result_0['closure_score'], 0.0)
        self.assertGreaterEqual(result_0['closure_score'], 0)
        self.assertLessEqual(result_0['closure_score'], 100)

        # 전부 답변 → 100점
        content_all_answer = (
            "## 왜 사용하는가?\n"
            "성능을 개선하기 위해 사용한다.\n"
        )
        result_100 = check_qa_closure(content_all_answer)
        self.assertEqual(result_100['closure_score'], 100.0)

    def test_answer_excerpt(self):
        """답변 발췌문이 올바르게 추출된다."""
        content = (
            "## Docker란 무엇인가?\n"
            "Docker는 컨테이너 기반 가상화 플랫폼이다.\n"
        )
        result = check_qa_closure(content)
        q = result['questions'][0]
        self.assertTrue(q['has_answer'])
        self.assertTrue(len(q['answer_excerpt']) > 0)
        self.assertIn('Docker', q['answer_excerpt'])

        # 100자 초과 시 자르기 확인
        long_answer = "A" * 150 + "는 이것을 의미합니다."
        content_long = f"## 이것이 무엇인가?\n{long_answer}\n"
        result_long = check_qa_closure(content_long)
        if result_long['questions'] and result_long['questions'][0]['has_answer']:
            self.assertLessEqual(len(result_long['questions'][0]['answer_excerpt']), 100)

    def test_multiple_questions(self):
        """여러 질문이 올바르게 감지되고 개별 평가된다."""
        content = (
            "## 서버는 어떻게 시작하나요?\n"
            "npm run dev 명령어를 실행합니다.\n"
            "\n"
            "## 포트 번호는 변경할 수 있나요?\n"
            ".env 파일에서 PORT 값을 수정하면 됩니다.\n"
            "\n"
            "## 배포는 어디에 하나요?\n"
            "\n"
            "## 마무리\n"
            "이상으로 설명을 마칩니다.\n"
        )
        result = check_qa_closure(content)
        self.assertEqual(result['summary']['total_questions'], 3)
        self.assertEqual(result['summary']['answered'], 2)
        self.assertEqual(result['summary']['unanswered'], 1)
        # 점수: 2/3 = 66.7
        self.assertAlmostEqual(result['closure_score'], 66.7, places=1)

    def test_consecutive_questions(self):
        """연속된 미답변 질문에 대해 경고 제안을 생성한다."""
        content = (
            "## 기능이 왜 필요한가?\n"
            "\n"
            "## 어떻게 구현할까요?\n"
            "\n"
            "## 언제 완료되나요?\n"
            "\n"
        )
        result = check_qa_closure(content)
        self.assertEqual(result['summary']['unanswered'], 3)
        self.assertEqual(result['closure_score'], 0.0)
        # 연속 질문 경고가 제안에 포함되어야 함
        consecutive_warn = [s for s in result['suggestions'] if '연속' in s]
        self.assertTrue(len(consecutive_warn) >= 1)

    def test_mixed_sources(self):
        """헤딩과 본문 질문이 혼합된 경우 모두 감지한다."""
        content = (
            "## What is Flask?\n"
            "Flask is a micro web framework for Python.\n"
            "\n"
            "성능 테스트를 어떻게 할까?\n"
            "locust 도구를 사용하면 됩니다.\n"
        )
        result = check_qa_closure(content)
        sources = {q['source'] for q in result['questions']}
        self.assertIn('heading', sources)
        self.assertIn('body', sources)
        # 두 질문 모두 답변됨
        self.assertEqual(result['summary']['answered'], 2)

    def test_suggestions(self):
        """제안 목록이 상황에 맞게 생성된다."""
        # 미답변 있는 경우 → 개선 제안 포함
        content_unanswered = (
            "## 이 도구는 무엇인가요?\n"
            "\n"
            "## 어디서 다운로드하나요?\n"
            "\n"
        )
        result = check_qa_closure(content_unanswered)
        self.assertTrue(len(result['suggestions']) >= 1)
        self.assertTrue(any('답변이 부족' in s for s in result['suggestions']))
        # 미답변 질문 구체적 안내 포함
        self.assertTrue(any('미답변 질문' in s for s in result['suggestions']))

        # 전부 답변된 경우 → 긍정적 메시지
        content_all_ok = (
            "## 설치 방법은 무엇인가요?\n"
            "pip install로 설치합니다.\n"
        )
        result_ok = check_qa_closure(content_all_ok)
        self.assertTrue(any('모든 질문에 답변' in s for s in result_ok['suggestions']))

    def test_english_question_detection(self):
        """영어 질문 패턴도 정확히 감지한다."""
        content = (
            "## How to install the package?\n"
            "Run npm install to get started.\n"
            "\n"
            "## What is the default port?\n"
            "The answer is port 3000.\n"
        )
        result = check_qa_closure(content)
        self.assertEqual(result['summary']['total_questions'], 2)
        self.assertEqual(result['summary']['answered'], 2)

    def test_question_within_3_sentences(self):
        """질문 뒤 3문장 이내만 답변으로 인정한다."""
        # 4번째 줄에 답변 신호 → 미답변 처리
        content = (
            "## 이 기능은 무엇인가?\n"
            "첫째 줄은 보충 설명\n"
            "둘째 줄도 보충 설명\n"
            "셋째 줄도 보충 설명\n"
            "이것은 중요한 기능입니다.\n"
        )
        result = check_qa_closure(content)
        q = result['questions'][0]
        # 3문장 이내에 답변 신호가 없으므로 미답변
        self.assertFalse(q['has_answer'])

    def test_duplicate_question_dedup(self):
        """동일한 질문 텍스트는 중복 제거된다."""
        content = (
            "## 왜 필요한가?\n"
            "왜 필요한가?\n"
            "이유는 성능 때문입니다.\n"
        )
        result = check_qa_closure(content)
        q_texts = [q['question'] for q in result['questions']]
        # 중복 제거되어 1개만 존재
        self.assertEqual(q_texts.count('왜 필요한가?'), 1)


if __name__ == '__main__':
    unittest.main()
