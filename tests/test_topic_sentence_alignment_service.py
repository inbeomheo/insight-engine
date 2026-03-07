"""Topic Sentence Alignment Analyzer 서비스 테스트."""
import unittest
from services.topic_sentence_alignment_service import analyze_topic_sentence_alignment


class TestTopicSentenceAlignment(unittest.TestCase):

    def test_empty_content(self):
        result = analyze_topic_sentence_alignment('')
        self.assertEqual(result['score'], 100.0)
        self.assertEqual(result['summary']['level'], 'none')

    def test_none_content(self):
        result = analyze_topic_sentence_alignment(None)
        self.assertEqual(result['score'], 100.0)

    def test_no_paragraphs(self):
        content = '짧은 문장.'
        result = analyze_topic_sentence_alignment(content)
        self.assertEqual(result['summary']['total_paragraphs'], 0)

    def test_aligned_paragraph(self):
        content = ('데이터베이스 성능을 최적화하는 방법을 알아봅니다. '
                   '데이터베이스 인덱스를 활용하면 성능이 개선됩니다. '
                   '데이터베이스 쿼리를 최적화하는 것도 중요합니다. '
                   '성능 모니터링을 통해 병목을 찾을 수 있습니다.')
        result = analyze_topic_sentence_alignment(content)
        self.assertGreater(result['summary']['aligned_count'], 0)

    def test_weak_opener(self):
        content = ('그리고 다음 단계로 넘어갑니다. '
                   '설정 파일을 수정해야 합니다. '
                   '환경변수도 설정이 필요합니다. '
                   '최종적으로 서버를 재시작합니다.')
        result = analyze_topic_sentence_alignment(content)
        self.assertGreater(result['summary']['weak_opener_count'], 0)

    def test_multiple_paragraphs(self):
        content = ('첫 번째 문단의 주제문입니다. '
                   '첫 번째 문단의 내용이 이어집니다. '
                   '첫 번째 문단의 마무리입니다.\n\n'
                   '두 번째 문단의 주제문입니다. '
                   '두 번째 문단의 세부 내용입니다. '
                   '두 번째 문단을 마칩니다.')
        result = analyze_topic_sentence_alignment(content)
        self.assertEqual(result['summary']['total_paragraphs'], 2)

    def test_english_alignment(self):
        content = ('This section covers database optimization techniques. '
                   'Database indexes improve query performance significantly. '
                   'Database caching reduces response time for repeated queries. '
                   'Performance testing validates the optimization results.')
        result = analyze_topic_sentence_alignment(content)
        self.assertGreater(result['summary']['aligned_count'], 0)

    def test_score_range(self):
        content = '일반적인 콘텐츠로 충분히 긴 문장이 포함되어 있습니다.'
        result = analyze_topic_sentence_alignment(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_return_structure(self):
        content = '구조 확인을 위한 충분히 긴 테스트 콘텐츠입니다.'
        result = analyze_topic_sentence_alignment(content)
        self.assertIn('score', result)
        self.assertIn('summary', result)
        self.assertIn('paragraph_details', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_paragraphs', result['summary'])
        self.assertIn('aligned_count', result['summary'])
        self.assertIn('misaligned_count', result['summary'])
        self.assertIn('weak_opener_count', result['summary'])
        self.assertIn('level', result['summary'])

    def test_suggestions_exist(self):
        content = ('그리고 추가적인 내용을 설명합니다. '
                   '서버 설정을 진행합니다. '
                   '네트워크도 설정합니다. '
                   '마지막으로 테스트합니다.')
        result = analyze_topic_sentence_alignment(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_heading_excluded(self):
        content = ('# 제목은 제외됩니다\n\n'
                   '본문 문단의 주제문입니다. '
                   '본문의 세부 내용을 설명합니다. '
                   '본문의 마무리를 합니다.')
        result = analyze_topic_sentence_alignment(content)
        # 제목은 문단으로 카운트되지 않음
        details = result['paragraph_details']
        for d in details:
            self.assertFalse(d['first_sentence'].startswith('#'))

    def test_short_paragraph_skipped(self):
        content = '짧은 문단.\n\n또 다른 짧은 문단.'
        result = analyze_topic_sentence_alignment(content)
        self.assertEqual(result['summary']['total_paragraphs'], 0)


if __name__ == '__main__':
    unittest.main()
