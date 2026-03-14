"""
YouTube 영상 Q&A 서비스 단위 테스트

- video_qa_service: 인덱싱, 검색, 답변 생성
- /api/video-qa 엔드포인트 (Flask 라우트)
- ChromaDB와 LiteLLM을 모킹하여 격리 테스트
"""
import unittest
from unittest.mock import MagicMock, patch


class TestIndexVideoTranscript(unittest.TestCase):
    """index_video_transcript 함수 테스트"""

    def test_빈_자막은_실패(self):
        """빈 자막 입력 시 False 반환"""
        from services.media.video_qa_service import index_video_transcript
        result = index_video_transcript("test_id", "")
        self.assertFalse(result)

    def test_공백만_있는_자막은_실패(self):
        """공백만 있는 자막 입력 시 False 반환"""
        from services.media.video_qa_service import index_video_transcript
        result = index_video_transcript("test_id", "   ")
        self.assertFalse(result)

    @patch("services.video_qa_service._CHROMA_AVAILABLE", False)
    def test_chromadb_없으면_실패(self):
        """ChromaDB 미설치 시 False 반환"""
        from services.media.video_qa_service import index_video_transcript
        result = index_video_transcript("test_id", "자막 내용")
        self.assertFalse(result)

    @patch("services.video_qa_service._get_chroma_client")
    def test_정상_인덱싱(self, mock_client_fn):
        """정상 자막을 ChromaDB에 저장하면 True 반환"""
        # ChromaDB 모킹
        mock_collection = MagicMock()
        mock_collection.count.return_value = 0
        mock_client = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client_fn.return_value = mock_client

        with patch("services.video_qa_service._CHROMA_AVAILABLE", True):
            from services.media.video_qa_service import index_video_transcript
            result = index_video_transcript("abc123", "이것은 테스트 자막입니다. " * 50)

        self.assertTrue(result)
        mock_collection.add.assert_called_once()

    @patch("services.video_qa_service._get_chroma_client")
    def test_기존_인덱스_재인덱싱(self, mock_client_fn):
        """기존 데이터 있으면 삭제 후 재인덱싱"""
        mock_collection = MagicMock()
        mock_collection.count.return_value = 5  # 기존 데이터 있음
        mock_collection.get.return_value = {"ids": ["abc123_chunk_0", "abc123_chunk_1"]}
        mock_client = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client_fn.return_value = mock_client

        with patch("services.video_qa_service._CHROMA_AVAILABLE", True):
            from services.media.video_qa_service import index_video_transcript
            result = index_video_transcript("abc123", "새로운 자막 내용입니다. " * 50)

        self.assertTrue(result)
        # 기존 데이터 삭제 호출 확인
        mock_collection.delete.assert_called_once()


class TestIsVideoIndexed(unittest.TestCase):
    """is_video_indexed 함수 테스트"""

    @patch("services.video_qa_service._CHROMA_AVAILABLE", False)
    def test_chromadb_없으면_False(self):
        from services.media.video_qa_service import is_video_indexed
        self.assertFalse(is_video_indexed("test_id"))

    @patch("services.video_qa_service._get_chroma_client")
    def test_컬렉션_비어있으면_False(self, mock_client_fn):
        mock_collection = MagicMock()
        mock_collection.count.return_value = 0
        mock_client = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client_fn.return_value = mock_client

        with patch("services.video_qa_service._CHROMA_AVAILABLE", True):
            from services.media.video_qa_service import is_video_indexed
            self.assertFalse(is_video_indexed("test_id"))

    @patch("services.video_qa_service._get_chroma_client")
    def test_컬렉션_있으면_True(self, mock_client_fn):
        mock_collection = MagicMock()
        mock_collection.count.return_value = 10
        mock_client = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client_fn.return_value = mock_client

        with patch("services.video_qa_service._CHROMA_AVAILABLE", True):
            from services.media.video_qa_service import is_video_indexed
            self.assertTrue(is_video_indexed("test_id"))


class TestSearchRelevantChunks(unittest.TestCase):
    """search_relevant_chunks 함수 테스트"""

    @patch("services.video_qa_service._CHROMA_AVAILABLE", False)
    def test_chromadb_없으면_빈_리스트(self):
        from services.media.video_qa_service import search_relevant_chunks
        result = search_relevant_chunks("test_id", "질문")
        self.assertEqual(result, [])

    @patch("services.video_qa_service._get_chroma_client")
    def test_컬렉션_비어있으면_빈_리스트(self, mock_client_fn):
        mock_collection = MagicMock()
        mock_collection.count.return_value = 0
        mock_client = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client_fn.return_value = mock_client

        with patch("services.video_qa_service._CHROMA_AVAILABLE", True):
            from services.media.video_qa_service import search_relevant_chunks
            result = search_relevant_chunks("test_id", "질문")
        self.assertEqual(result, [])

    @patch("services.video_qa_service._get_chroma_client")
    def test_검색_결과_반환_형식(self, mock_client_fn):
        """검색 결과가 올바른 형식으로 반환되는지 확인"""
        mock_collection = MagicMock()
        mock_collection.count.return_value = 3
        mock_collection.query.return_value = {
            "documents": [["청크1 텍스트", "청크2 텍스트"]],
            "metadatas": [
                [{"video_id": "abc", "chunk_index": 0, "timestamp_start": 0.0},
                 {"video_id": "abc", "chunk_index": 1, "timestamp_start": 0.0}]
            ],
            "distances": [[0.1, 0.3]],
        }
        mock_client = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client_fn.return_value = mock_client

        with patch("services.video_qa_service._CHROMA_AVAILABLE", True):
            from services.media.video_qa_service import search_relevant_chunks
            result = search_relevant_chunks("abc", "테스트 질문", top_k=5)

        self.assertEqual(len(result), 2)
        self.assertIn("text", result[0])
        self.assertIn("chunk_index", result[0])
        self.assertIn("distance", result[0])
        self.assertEqual(result[0]["text"], "청크1 텍스트")
        self.assertEqual(result[0]["chunk_index"], 0)


class TestAnswerQuestion(unittest.TestCase):
    """answer_question 함수 테스트"""

    @patch("services.video_qa_service._LITELLM_AVAILABLE", False)
    def test_litellm_없으면_오류_메시지(self):
        from services.media.video_qa_service import answer_question
        result = answer_question("test_id", "질문")
        self.assertIn("answer", result)
        self.assertIn("sources", result)
        self.assertEqual(result["sources"], [])

    @patch("services.video_qa_service.search_relevant_chunks")
    def test_청크_없으면_안내_메시지(self, mock_search):
        """인덱싱이 안 된 상태 — 자막 데이터 없음 안내"""
        mock_search.return_value = []
        with patch("services.video_qa_service._LITELLM_AVAILABLE", True):
            from services.media.video_qa_service import answer_question
            result = answer_question("test_id", "질문")
        self.assertIn("answer", result)
        self.assertIn("찾을 수 없습니다", result["answer"])

    @patch("services.video_qa_service.litellm_completion")
    @patch("services.video_qa_service.search_relevant_chunks")
    def test_정상_답변_생성(self, mock_search, mock_completion):
        """정상 흐름 — LiteLLM 호출하여 답변 생성"""
        mock_search.return_value = [
            {"text": "테스트 자막 내용", "chunk_index": 0, "distance": 0.15}
        ]
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "테스트 답변입니다."
        mock_completion.return_value = mock_response

        with patch("services.video_qa_service._LITELLM_AVAILABLE", True):
            from services.media.video_qa_service import answer_question
            result = answer_question("test_id", "질문", history=[])

        self.assertEqual(result["answer"], "테스트 답변입니다.")
        self.assertEqual(len(result["sources"]), 1)
        # 관련도 = 1 - distance (0.15) = 0.85
        self.assertAlmostEqual(result["sources"][0]["relevance"], 0.85, places=2)

    @patch("services.video_qa_service.litellm_completion")
    @patch("services.video_qa_service.search_relevant_chunks")
    def test_대화_히스토리_전달(self, mock_search, mock_completion):
        """히스토리 메시지가 LiteLLM에 올바르게 전달되는지 확인"""
        mock_search.return_value = [
            {"text": "자막 내용", "chunk_index": 0, "distance": 0.2}
        ]
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "답변"
        mock_completion.return_value = mock_response

        history = [
            {"role": "user", "content": "이전 질문"},
            {"role": "assistant", "content": "이전 답변"},
        ]

        with patch("services.video_qa_service._LITELLM_AVAILABLE", True):
            from services.media.video_qa_service import answer_question
            answer_question("test_id", "새 질문", history=history)

        # completion에 전달된 messages 확인
        call_kwargs = mock_completion.call_args[1]
        messages = call_kwargs["messages"]

        # system + 이전2 + 현재1 = 4개
        self.assertEqual(len(messages), 4)
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[1]["content"], "이전 질문")
        self.assertEqual(messages[2]["content"], "이전 답변")
        self.assertEqual(messages[3]["content"], "새 질문")


class TestVideoQaRoute(unittest.TestCase):
    """Flask /api/video-qa 라우트 테스트"""

    def setUp(self):
        """테스트용 Flask 앱 설정"""
        os.environ["SUPABASE_URL"] = ""
        os.environ["SUPABASE_ANON_KEY"] = ""

    @patch("services.supabase_service.is_supabase_enabled", return_value=False)
    def _get_client(self, mock_enabled):
        import app as flask_app
        return flask_app.app.test_client()

    @patch("services.supabase_service.is_supabase_enabled", return_value=False)
    def test_video_url_없으면_400(self, mock_enabled):
        import app as flask_app
        client = flask_app.app.test_client()
        res = client.post(
            "/api/video-qa",
            json={"question": "질문"},
            headers={"X-User-Id": "test-user"},
        )
        # Supabase 비활성화 시 인증 우회 — 400이거나 인증 에러
        self.assertIn(res.status_code, [400, 401])

    @patch("services.supabase_service.is_supabase_enabled", return_value=False)
    def test_비_유튜브_url은_400(self, mock_enabled):
        import app as flask_app
        client = flask_app.app.test_client()
        res = client.post(
            "/api/video-qa",
            json={"video_url": "https://example.com", "question": "질문"},
        )
        self.assertIn(res.status_code, [400, 401])


import os

if __name__ == "__main__":
    unittest.main()
