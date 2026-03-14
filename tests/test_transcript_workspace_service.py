"""transcript_workspace_service 단위 테스트"""
import unittest

from services.transcript.transcript_workspace_service import parse_transcript_sentences, apply_edits


class TestParseTranscriptSentences(unittest.TestCase):
    """parse_transcript_sentences 테스트"""

    def test_empty_text(self):
        """빈 텍스트"""
        self.assertEqual(parse_transcript_sentences(''), [])

    def test_text_only(self):
        """타임스탬프 없는 텍스트 분리"""
        text = '첫 번째 문장입니다. 두 번째 문장입니다.'
        result = parse_transcript_sentences(text)
        self.assertGreaterEqual(len(result), 1)
        self.assertEqual(result[0]['index'], 0)
        self.assertIsNone(result[0]['start_time'])

    def test_with_segments(self):
        """세그먼트 기반 문장 분리"""
        segments = [
            {'start': 0.0, 'text': '안녕하세요.', 'duration': 2.0},
            {'start': 2.0, 'text': '반갑습니다.', 'duration': 2.0},
        ]
        result = parse_transcript_sentences('안녕하세요. 반갑습니다.', segments)
        self.assertGreaterEqual(len(result), 1)
        self.assertIsNotNone(result[0]['start_time'])

    def test_unsplittable_text(self):
        """분리 불가 텍스트 → 1문장"""
        text = '분리할 수 없는 하나의 긴 텍스트'
        result = parse_transcript_sentences(text)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['text'], text)

    def test_korean_sentence_end(self):
        """한국어 종결 패턴 분리"""
        text = '이것은 첫 번째입니다. 이것은 두 번째입니다.'
        result = parse_transcript_sentences(text)
        self.assertGreaterEqual(len(result), 2)

    def test_empty_segments_skipped(self):
        """빈 세그먼트 건너뜀"""
        segments = [
            {'start': 0.0, 'text': '', 'duration': 1.0},
            {'start': 1.0, 'text': '내용 있음', 'duration': 2.0},
        ]
        result = parse_transcript_sentences('내용 있음', segments)
        self.assertTrue(any('내용 있음' in s['text'] for s in result))


class TestApplyEdits(unittest.TestCase):
    """apply_edits 테스트"""

    def _make_sentences(self, texts):
        return [{'index': i, 'text': t, 'start_time': None} for i, t in enumerate(texts)]

    def test_no_edits(self):
        """편집 없으면 원본 유지"""
        sentences = self._make_sentences(['문장1', '문장2', '문장3'])
        result = apply_edits(sentences, {})
        self.assertEqual(result, '문장1 문장2 문장3')

    def test_delete(self):
        """문장 삭제"""
        sentences = self._make_sentences(['문장1', '삭제됨', '문장3'])
        result = apply_edits(sentences, {'deleted': [1]})
        self.assertEqual(result, '문장1 문장3')

    def test_modify(self):
        """문장 수정"""
        sentences = self._make_sentences(['원본', '유지'])
        result = apply_edits(sentences, {'modified': {'0': '수정됨'}})
        self.assertEqual(result, '수정됨 유지')

    def test_delete_and_modify(self):
        """삭제 + 수정 동시"""
        sentences = self._make_sentences(['A', 'B', 'C'])
        result = apply_edits(sentences, {'deleted': [1], 'modified': {'2': 'D'}})
        self.assertEqual(result, 'A D')

    def test_empty_sentences(self):
        """빈 문장 목록"""
        result = apply_edits([], {})
        self.assertEqual(result, '')


if __name__ == '__main__':
    unittest.main()
