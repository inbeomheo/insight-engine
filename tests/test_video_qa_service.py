"""video_qa_service 단위 테스트"""
import unittest
from unittest.mock import patch, MagicMock

from services.media.video_qa_service import (
    DEFAULT_CHUNK_SIZE,
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_TOP_K,
    MAX_HISTORY_MESSAGES,
    VIDEO_COLLECTION_PREFIX,
    DEFAULT_QA_MODEL,
    _get_video_collection,
    is_video_indexed,
    index_video_transcript,
    search_relevant_chunks,
    answer_question,
)


class TestConstants(unittest.TestCase):

    def test_chunk_size(self):
        """청크 크기 기본값"""
        self.assertEqual(DEFAULT_CHUNK_SIZE, 600)

    def test_chunk_overlap(self):
        """청크 오버랩 기본값"""
        self.assertEqual(DEFAULT_CHUNK_OVERLAP, 80)

    def test_top_k(self):
        """TOP K 기본값"""
        self.assertEqual(DEFAULT_TOP_K, 5)

    def test_max_history(self):
        """대화 히스토리 최대 수"""
        self.assertEqual(MAX_HISTORY_MESSAGES, 10)

    def test_collection_prefix(self):
        """컬렉션 접두사"""
        self.assertEqual(VIDEO_COLLECTION_PREFIX, 'video_qa_')

    def test_qa_model(self):
        """기본 QA 모델"""
        self.assertEqual(DEFAULT_QA_MODEL, 'zhipuai/GLM-4.5-Air')


class TestGetVideoCollection(unittest.TestCase):

    def test_collection_name(self):
        """컬렉션 이름 형식"""
        mock_client = MagicMock()
        _get_video_collection(mock_client, 'abc123')
        mock_client.get_or_create_collection.assert_called_once_with(
            name='video_qa_abc123'
        )


class TestIsVideoIndexed(unittest.TestCase):

    @patch('services.media.video_qa_service._CHROMA_AVAILABLE', False)
    def test_no_chromadb(self):
        """ChromaDB 미설치 → False"""
        self.assertFalse(is_video_indexed('vid1'))

    @patch('services.media.video_qa_service._get_chroma_client', return_value=None)
    @patch('services.media.video_qa_service._CHROMA_AVAILABLE', True)
    def test_client_none(self, mock_client):
        """클라이언트 None → False"""
        self.assertFalse(is_video_indexed('vid1'))

    @patch('services.media.video_qa_service._get_video_collection')
    @patch('services.media.video_qa_service._get_chroma_client')
    @patch('services.media.video_qa_service._CHROMA_AVAILABLE', True)
    def test_indexed(self, mock_client, mock_collection):
        """인덱싱됨 → True"""
        mock_coll = MagicMock()
        mock_coll.count.return_value = 5
        mock_collection.return_value = mock_coll
        mock_client.return_value = MagicMock()
        self.assertTrue(is_video_indexed('vid1'))

    @patch('services.media.video_qa_service._get_video_collection')
    @patch('services.media.video_qa_service._get_chroma_client')
    @patch('services.media.video_qa_service._CHROMA_AVAILABLE', True)
    def test_not_indexed(self, mock_client, mock_collection):
        """인덱싱 안 됨 → False"""
        mock_coll = MagicMock()
        mock_coll.count.return_value = 0
        mock_collection.return_value = mock_coll
        mock_client.return_value = MagicMock()
        self.assertFalse(is_video_indexed('vid1'))


class TestIndexVideoTranscript(unittest.TestCase):

    @patch('services.media.video_qa_service._CHROMA_AVAILABLE', False)
    def test_no_chromadb(self):
        """ChromaDB 미설치 → False"""
        self.assertFalse(index_video_transcript('vid1', '자막 텍스트'))

    @patch('services.media.video_qa_service._CHROMA_AVAILABLE', True)
    def test_empty_transcript(self):
        """빈 자막 → False"""
        self.assertFalse(index_video_transcript('vid1', ''))

    @patch('services.media.video_qa_service._CHROMA_AVAILABLE', True)
    def test_whitespace_transcript(self):
        """공백 자막 → False"""
        self.assertFalse(index_video_transcript('vid1', '   '))


class TestSearchRelevantChunks(unittest.TestCase):

    @patch('services.media.video_qa_service._CHROMA_AVAILABLE', False)
    def test_no_chromadb(self):
        """ChromaDB 미설치 → 빈 리스트"""
        result = search_relevant_chunks('vid1', '질문')
        self.assertEqual(result, [])


class TestAnswerQuestion(unittest.TestCase):

    @patch('services.media.video_qa_service._LITELLM_AVAILABLE', False)
    def test_no_litellm(self):
        """LiteLLM 미설치 → 안내 메시지"""
        result = answer_question('vid1', '질문')
        self.assertIn('litellm', result['answer'])
        self.assertEqual(result['sources'], [])

    @patch('services.media.video_qa_service.search_relevant_chunks', return_value=[])
    @patch('services.media.video_qa_service._LITELLM_AVAILABLE', True)
    def test_no_chunks(self, mock_search):
        """인덱싱 안 됨 → 안내 메시지"""
        result = answer_question('vid1', '질문')
        self.assertIn('자막 데이터를 찾을 수 없습니다', result['answer'])

    @patch('services.media.video_qa_service.litellm_completion')
    @patch('services.media.video_qa_service.search_relevant_chunks')
    @patch('services.media.video_qa_service._LITELLM_AVAILABLE', True)
    def test_success(self, mock_search, mock_completion):
        """정상 답변 생성"""
        mock_search.return_value = [
            {'text': '자막 내용입니다', 'chunk_index': 0, 'distance': 0.2},
        ]
        mock_choice = MagicMock()
        mock_choice.message.content = '답변입니다.'
        mock_completion.return_value = MagicMock(choices=[mock_choice])

        result = answer_question('vid1', '이 영상은 뭐에 대한 거야?')
        self.assertEqual(result['answer'], '답변입니다.')
        self.assertEqual(len(result['sources']), 1)
        self.assertAlmostEqual(result['sources'][0]['relevance'], 0.8, places=1)

    @patch('services.media.video_qa_service.litellm_completion', side_effect=Exception('API error'))
    @patch('services.media.video_qa_service.search_relevant_chunks')
    @patch('services.media.video_qa_service._LITELLM_AVAILABLE', True)
    def test_api_error(self, mock_search, mock_completion):
        """API 오류 → 에러 메시지"""
        mock_search.return_value = [
            {'text': '내용', 'chunk_index': 0, 'distance': 0.1},
        ]
        result = answer_question('vid1', '질문')
        self.assertIn('오류가 발생', result['answer'])


if __name__ == '__main__':
    unittest.main()
