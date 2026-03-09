"""
답변 마커 서비스 테스트

mark_answer_moments, AnswerMoment 검증.
"""
import unittest
from services.answer_moment_service import (
    AnswerMoment,
    mark_answer_moments,
)


class TestMarkAnswerMomentsEmpty(unittest.TestCase):
    """빈/무효 입력 처리"""

    def test_empty_string(self):
        """빈 문자열 → 빈 리스트"""
        self.assertEqual(mark_answer_moments(''), [])

    def test_none_input(self):
        """None → 빈 리스트"""
        self.assertEqual(mark_answer_moments(None), [])

    def test_whitespace_only(self):
        """공백만 → 빈 리스트"""
        self.assertEqual(mark_answer_moments('   \n\t  '), [])


class TestKoreanQA(unittest.TestCase):
    """한국어 Q&A 감지"""

    def test_explicit_qa_format(self):
        """Q: / A: 형식 감지"""
        transcript = (
            'Q: 파이썬에서 리스트와 튜플의 차이점은 무엇인가요?\n'
            'A: 리스트는 변경 가능한 자료형이고 튜플은 변경 불가능합니다. '
            '리스트는 대괄호로 생성하고 튜플은 소괄호로 생성합니다. '
            '성능 면에서는 튜플이 약간 더 빠릅니다. '
            '데이터를 수정할 필요가 없다면 튜플을 사용하는 것이 좋습니다. '
            '반대로 데이터를 자주 변경해야 한다면 리스트를 선택하세요.'
        )
        moments = mark_answer_moments(transcript)
        self.assertGreaterEqual(len(moments), 1)
        self.assertIsInstance(moments[0], AnswerMoment)

    def test_question_mark_korean(self):
        """물음표가 있는 한국어 질문"""
        transcript = (
            '머신러닝에서 과적합이란 무엇인가요?\n\n'
            '과적합은 모델이 훈련 데이터에 너무 맞춰진 상태를 말합니다. '
            '새로운 데이터에 대한 일반화 성능이 떨어지게 됩니다. '
            '이를 방지하려면 정규화 기법을 사용하거나 '
            '더 많은 훈련 데이터를 확보해야 합니다. '
            '교차 검증으로 과적합 여부를 확인할 수 있습니다.'
        )
        moments = mark_answer_moments(transcript)
        self.assertGreaterEqual(len(moments), 1)

    def test_how_question_korean(self):
        """'어떻게' 질문 감지"""
        transcript = (
            '어떻게 하면 코드 리뷰를 효과적으로 할 수 있나요?\n\n'
            '코드 리뷰는 작은 단위로 나누어 진행하는 것이 좋습니다. '
            '한 번에 너무 많은 코드를 리뷰하면 집중력이 떨어집니다. '
            '명확한 기준을 세우고 체크리스트를 활용하세요. '
            '건설적인 피드백을 주는 것도 중요합니다. '
            '자동화 도구를 병행하면 더 효율적입니다.'
        )
        moments = mark_answer_moments(transcript)
        self.assertGreaterEqual(len(moments), 1)
        # 질문 텍스트에 '어떻게' 포함
        question_texts = [m.question for m in moments]
        self.assertTrue(any('어떻게' in q for q in question_texts))


class TestEnglishQA(unittest.TestCase):
    """영어 Q&A 감지"""

    def test_what_question(self):
        """What 질문 감지"""
        transcript = (
            'What is the difference between REST and GraphQL?\n\n'
            'REST uses fixed endpoints for each resource while GraphQL '
            'provides a single endpoint with flexible queries. '
            'GraphQL allows clients to request exactly the data they need. '
            'REST can lead to over-fetching or under-fetching of data. '
            'GraphQL uses a schema to define available data types. '
            'Both approaches have their own strengths and trade-offs.'
        )
        moments = mark_answer_moments(transcript)
        self.assertGreaterEqual(len(moments), 1)

    def test_how_question_english(self):
        """How 질문 감지"""
        transcript = (
            'How do you handle errors in async JavaScript?\n\n'
            'The recommended approach is using try-catch blocks with async await. '
            'You can also use the catch method on promises directly. '
            'Global error handlers like window.onerror provide a safety net. '
            'Proper error boundaries in React catch rendering errors. '
            'Always log errors for debugging purposes.'
        )
        moments = mark_answer_moments(transcript)
        self.assertGreaterEqual(len(moments), 1)

    def test_qa_with_explicit_marker(self):
        """Q: / A: 형식 (영어)"""
        transcript = (
            'Q: Should I use TypeScript for new projects?\n'
            'A: TypeScript adds type safety which catches bugs early. '
            'It improves developer experience with better autocomplete. '
            'The learning curve is minimal if you know JavaScript. '
            'Most modern frameworks have excellent TypeScript support. '
            'For large projects the benefits clearly outweigh the costs.'
        )
        moments = mark_answer_moments(transcript)
        self.assertGreaterEqual(len(moments), 1)
        # 명시적 마커 → 높은 신뢰도
        if moments:
            self.assertGreaterEqual(moments[0].confidence, 50.0)


class TestAnswerMomentFields(unittest.TestCase):
    """AnswerMoment 필드 검증"""

    def _get_sample_moments(self):
        transcript = (
            'Q: 데이터베이스 인덱스는 왜 중요한가요?\n'
            'A: 인덱스는 데이터 검색 속도를 크게 향상시킵니다. '
            '인덱스가 없으면 전체 테이블을 스캔해야 합니다. '
            '적절한 인덱스 설계가 데이터베이스 성능의 핵심입니다. '
            '하지만 너무 많은 인덱스는 쓰기 성능을 저하시킵니다. '
            '쿼리 패턴을 분석하여 필요한 인덱스만 생성하세요.'
        )
        return mark_answer_moments(transcript)

    def test_question_field(self):
        """question 필드가 비어있지 않음"""
        moments = self._get_sample_moments()
        for m in moments:
            self.assertTrue(len(m.question) > 0)

    def test_answer_field(self):
        """answer 필드가 비어있지 않음"""
        moments = self._get_sample_moments()
        for m in moments:
            self.assertTrue(len(m.answer) > 0)

    def test_start_position_non_negative(self):
        """start_position ≥ 0"""
        moments = self._get_sample_moments()
        for m in moments:
            self.assertGreaterEqual(m.start_position, 0)

    def test_word_count_positive(self):
        """word_count > 0"""
        moments = self._get_sample_moments()
        for m in moments:
            self.assertGreater(m.word_count, 0)

    def test_confidence_range(self):
        """confidence 0~100"""
        moments = self._get_sample_moments()
        for m in moments:
            self.assertGreaterEqual(m.confidence, 0.0)
            self.assertLessEqual(m.confidence, 100.0)


class TestMultipleQA(unittest.TestCase):
    """다중 Q&A 구간 처리"""

    def test_multiple_questions(self):
        """여러 질문이 있는 자막"""
        transcript = (
            'Q: 파이썬이란 무엇인가요?\n'
            'A: 파이썬은 범용 프로그래밍 언어입니다. '
            '가독성이 뛰어나고 배우기 쉽습니다. '
            '웹 개발부터 데이터 분석까지 다양하게 활용됩니다. '
            '풍부한 라이브러리 생태계를 보유하고 있습니다. '
            '전 세계적으로 가장 인기 있는 언어 중 하나입니다.\n\n'
            'Q: 파이썬의 단점은 무엇인가요?\n'
            'A: 실행 속도가 C나 자바보다 느립니다. '
            '모바일 앱 개발에는 적합하지 않습니다. '
            '멀티스레딩에 GIL 제약이 있습니다. '
            '메모리 사용량이 상대적으로 많습니다. '
            '타입 안전성이 컴파일 언어보다 약합니다.'
        )
        moments = mark_answer_moments(transcript)
        self.assertGreaterEqual(len(moments), 2)

    def test_sorted_by_position(self):
        """결과가 start_position 오름차순 정렬"""
        transcript = (
            'Q: 첫 번째 질문은 무엇인가요?\n'
            'A: 첫 번째 답변입니다. 이것은 테스트를 위한 내용입니다. '
            '답변의 길이를 적절하게 맞추기 위해 추가 내용을 포함합니다. '
            '이 문장도 단어 수를 채우기 위한 것입니다. '
            '실제 콘텐츠에서는 더 의미 있는 내용이 들어갑니다.\n\n'
            'Q: 두 번째 질문은 어떤 것인가요?\n'
            'A: 두 번째 답변입니다. 여기도 테스트 목적으로 작성합니다. '
            '충분한 단어 수를 확보하기 위해 여러 문장을 포함합니다. '
            '이렇게 하면 답변 블록이 적정 길이가 됩니다.'
        )
        moments = mark_answer_moments(transcript)
        if len(moments) >= 2:
            positions = [m.start_position for m in moments]
            self.assertEqual(positions, sorted(positions))


class TestNoQAContent(unittest.TestCase):
    """Q&A가 아닌 콘텐츠"""

    def test_narrative_text(self):
        """서술형 텍스트 → 적거나 없는 결과"""
        transcript = (
            '오늘 날씨가 정말 좋습니다. '
            '공원에서 산책을 했습니다. '
            '새들이 노래하고 꽃이 피었습니다. '
            '점심은 샌드위치를 먹었습니다. '
            '오후에는 책을 읽었습니다.'
        )
        moments = mark_answer_moments(transcript)
        # Q&A 패턴이 없으므로 결과 매우 적어야 함
        self.assertLessEqual(len(moments), 1)

    def test_short_question_filtered(self):
        """5자 미만 짧은 질문 → 필터링"""
        transcript = '왜?\n이유는 복잡합니다.'
        moments = mark_answer_moments(transcript)
        # "왜?" 단독은 5자 미만이므로 필터링
        short_questions = [m for m in moments if len(m.question) < 5]
        self.assertEqual(len(short_questions), 0)


if __name__ == '__main__':
    unittest.main()
