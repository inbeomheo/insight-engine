"""Paragraph Unity Checker 서비스 테스트."""
import unittest
from services.paragraph_unity_service import check_paragraph_unity


class TestParagraphUnity(unittest.TestCase):

    def test_empty_content(self):
        result = check_paragraph_unity('')
        self.assertEqual(result['score'], 100.0)
        self.assertEqual(result['summary']['level'], 'none')

    def test_none_content(self):
        result = check_paragraph_unity(None)
        self.assertEqual(result['score'], 100.0)

    def test_no_paragraphs(self):
        content = '짧은 문장.'
        result = check_paragraph_unity(content)
        self.assertEqual(result['summary']['total_paragraphs'], 0)

    def test_unified_paragraph(self):
        content = ('데이터베이스 성능을 최적화합니다. '
                   '데이터베이스 인덱스를 추가합니다. '
                   '데이터베이스 쿼리를 개선합니다. '
                   '데이터베이스 캐시를 활성화합니다.')
        result = check_paragraph_unity(content)
        self.assertGreater(result['summary']['unified_count'], 0)

    def test_fragmented_paragraph(self):
        content = ('서버 설치 방법을 설명합니다. '
                   '한편 마케팅 전략도 중요합니다. '
                   '그런데 요리 레시피를 알아봅시다. '
                   '반면 우주 탐사 계획이 발표되었습니다. '
                   '또한 음악 축제 일정을 확인하세요.')
        result = check_paragraph_unity(content)
        self.assertGreater(result['summary']['fragmented_count'], 0)

    def test_multiple_paragraphs(self):
        content = ('첫 번째 문단에서는 서버 설정을 다룹니다. '
                   '서버 포트를 열고 서버를 시작합니다. '
                   '서버 로그를 확인하여 정상 작동을 검증합니다.\n\n'
                   '두 번째 문단에서는 클라이언트를 설정합니다. '
                   '클라이언트 인증을 구성하고 테스트합니다. '
                   '클라이언트가 서버에 정상 연결되는지 확인합니다.')
        result = check_paragraph_unity(content)
        self.assertEqual(result['summary']['total_paragraphs'], 2)

    def test_topic_shift_detection(self):
        content = ('프로그래밍 언어를 배웁니다. '
                   '파이썬은 쉽게 배울 수 있습니다. '
                   '한편 요리는 창의적인 활동입니다. '
                   '그런데 운동도 건강에 중요합니다. '
                   '또한 독서는 지식을 넓혀줍니다.')
        result = check_paragraph_unity(content)
        details = result['paragraph_details']
        if details:
            self.assertGreater(details[0]['topic_shift_count'], 0)

    def test_coherence_score(self):
        content = ('파이썬 프로그래밍을 시작합니다. '
                   '파이썬 변수를 선언하는 방법입니다. '
                   '파이썬 함수를 정의하는 방법입니다. '
                   '파이썬 클래스를 만드는 방법입니다.')
        result = check_paragraph_unity(content)
        self.assertGreater(result['summary']['avg_coherence'], 0)

    def test_score_range(self):
        content = '충분히 긴 문장으로 구성된 일반적인 콘텐츠 테스트입니다.'
        result = check_paragraph_unity(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_return_structure(self):
        content = '구조 확인을 위한 충분히 긴 콘텐츠 테스트 문장입니다.'
        result = check_paragraph_unity(content)
        self.assertIn('score', result)
        self.assertIn('summary', result)
        self.assertIn('paragraph_details', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_paragraphs', result['summary'])
        self.assertIn('unified_count', result['summary'])
        self.assertIn('fragmented_count', result['summary'])
        self.assertIn('avg_coherence', result['summary'])
        self.assertIn('level', result['summary'])

    def test_suggestions_for_fragmented(self):
        content = ('주제 하나를 설명합니다. '
                   '한편 완전히 다른 주제입니다. '
                   '그런데 또 다른 주제로 넘어갑니다. '
                   '반면 네 번째 주제도 등장합니다. '
                   '또한 다섯 번째 이야기를 합니다.')
        result = check_paragraph_unity(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_code_block_excluded(self):
        content = '```python\nprint("hello")\n```'
        result = check_paragraph_unity(content)
        self.assertEqual(result['summary']['total_paragraphs'], 0)

    def test_heading_excluded(self):
        content = '# 제목입니다'
        result = check_paragraph_unity(content)
        self.assertEqual(result['summary']['total_paragraphs'], 0)


if __name__ == '__main__':
    unittest.main()
