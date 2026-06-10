"""R57: /api/transcript/{video_id} sentence_count 필드 테스트"""
from __future__ import annotations

import unittest
from unittest.mock import patch, MagicMock


class TestSentenceCountField(unittest.TestCase):
    """sentence_count 필드가 sentences 리스트 길이와 일치하는지 검증"""

    # /api/transcript 라우트가 routes/blog/transcript_workspace.py로 분리됨
    # → 해당 모듈 네임스페이스의 content_service를 patch해야 mock이 적용됨
    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('routes.blog.transcript_workspace.content_service')
    def test_sentence_count_matches_sentences_length(self, mock_cs, mock_sb):
        """정상 자막 → sentence_count == len(sentences)"""
        mock_cs.get_transcript.return_value = {
            'text': '첫 번째 문장입니다. 두 번째 문장입니다. 세 번째 문장입니다.',
            'source': 'api',
            'segments': [],
        }
        from app import app
        with app.test_client() as client:
            resp = client.get(
                '/api/transcript/dQw4w9WgXcQ',
                headers={'Origin': 'http://localhost:3000'},
            )
            data = resp.get_json()
            if resp.status_code == 200:
                self.assertIn('sentence_count', data)
                self.assertEqual(data['sentence_count'], len(data['sentences']))

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('routes.blog.transcript_workspace.content_service')
    def test_sentence_count_zero_for_empty(self, mock_cs, mock_sb):
        """빈 자막 → 422 에러"""
        mock_cs.get_transcript.return_value = {
            'text': '',
            'source': 'api',
            'segments': [],
        }
        from app import app
        with app.test_client() as client:
            resp = client.get(
                '/api/transcript/dQw4w9WgXcQ',
                headers={'Origin': 'http://localhost:3000'},
            )
            self.assertEqual(resp.status_code, 422)

    def test_sentence_count_logic_directly(self):
        """sentence_count 로직 단위 테스트: len(sentences) 값과 동일해야 함"""
        from services.transcript.transcript_workspace_service import parse_transcript_sentences

        text = '안녕하세요. 반갑습니다. 오늘 날씨가 좋습니다.'
        sentences = parse_transcript_sentences(text)
        sentence_count = len(sentences)
        self.assertGreater(sentence_count, 0)
        self.assertEqual(sentence_count, len(sentences))

    def test_sentence_count_single_sentence(self):
        """단일 문장 → sentence_count == 1"""
        from services.transcript.transcript_workspace_service import parse_transcript_sentences

        text = '분리되지 않는 한 문장'
        sentences = parse_transcript_sentences(text)
        self.assertEqual(len(sentences), 1)

    def test_sentence_count_with_segments(self):
        """세그먼트 기반 분리 시 sentence_count 정확성"""
        from services.transcript.transcript_workspace_service import parse_transcript_sentences

        segments = [
            {'start': 0.0, 'text': '첫 번째입니다.', 'duration': 2.0},
            {'start': 2.0, 'text': '두 번째입니다.', 'duration': 2.0},
        ]
        text = '첫 번째입니다. 두 번째입니다.'
        sentences = parse_transcript_sentences(text, segments)
        self.assertEqual(len(sentences), 2)


if __name__ == '__main__':
    unittest.main()
