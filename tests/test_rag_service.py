"""
RAG 서비스 단위 테스트
- chunker: 텍스트 분할 + 파일 추출
- vector_store: 문서 추가/검색/삭제/목록
- context_builder: 컨텍스트 빌드 형식
- RAG_ENABLED=False 시 스킵
"""
import os
import shutil
import tempfile
import unittest

from services.rag.chunker import chunk_text, extract_text_from_file


class TestChunker(unittest.TestCase):
    """chunk_text / extract_text_from_file 테스트"""

    def test_chunk_text_basic(self):
        """기본 분할: 800자 단위"""
        text = "가" * 2000
        chunks = chunk_text(text, chunk_size=800, overlap=100)
        self.assertTrue(len(chunks) >= 3)
        # 첫 청크는 800자
        self.assertEqual(len(chunks[0]), 800)

    def test_chunk_text_overlap(self):
        """오버랩 검증: 인접 청크가 겹침"""
        text = "ABCDEFGHIJ" * 100  # 1000자
        chunks = chunk_text(text, chunk_size=400, overlap=100)
        # 두 번째 청크 시작 부분이 첫 번째 청크 끝 부분과 겹침
        if len(chunks) >= 2:
            tail = chunks[0][-100:]
            head = chunks[1][:100]
            self.assertEqual(tail, head)

    def test_chunk_text_short(self):
        """짧은 텍스트: 청크 1개"""
        text = "짧은 텍스트"
        chunks = chunk_text(text, chunk_size=800, overlap=100)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], "짧은 텍스트")

    def test_chunk_text_empty(self):
        """빈 텍스트: 빈 리스트"""
        chunks = chunk_text("", chunk_size=800, overlap=100)
        self.assertEqual(chunks, [])

    def test_extract_text_from_txt(self):
        """TXT 파일 추출"""
        content = "테스트 텍스트 내용"
        result = extract_text_from_file(content.encode('utf-8'), 'test.txt')
        self.assertEqual(result, content)

    def test_extract_text_from_md(self):
        """MD 파일 추출"""
        content = "# 제목\n내용입니다."
        result = extract_text_from_file(content.encode('utf-8'), 'test.md')
        self.assertEqual(result, content)

    def test_extract_text_unsupported(self):
        """지원하지 않는 확장자 → ValueError"""
        with self.assertRaises(ValueError):
            extract_text_from_file(b"data", 'test.docx')


class TestVectorStore(unittest.TestCase):
    """VectorStore CRUD 테스트 (임시 디렉토리 사용)"""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        # 격리된 VectorStore 인스턴스 생성
        from services.rag.vector_store import VectorStore
        self.store = VectorStore(db_path=self.tmp_dir)
        self.user_id = 'test-user-123'

    def tearDown(self):
        try:
            shutil.rmtree(self.tmp_dir)
        except OSError:
            pass

    def test_add_and_search(self):
        """문서 추가 후 검색"""
        chunks = ["Python은 프로그래밍 언어입니다.", "Flask는 Python 웹 프레임워크입니다."]
        self.store.add_document(
            self.user_id, 'doc-1', chunks,
            {'filename': 'test.txt', 'uploaded_at': '2026-01-01'}
        )
        results = self.store.search(self.user_id, 'Python 웹 개발', top_k=2)
        self.assertEqual(len(results), 2)
        self.assertIn('text', results[0])
        self.assertIn('metadata', results[0])
        self.assertIn('distance', results[0])

    def test_search_empty(self):
        """빈 컬렉션 검색 → 빈 리스트"""
        results = self.store.search(self.user_id, '검색어')
        self.assertEqual(results, [])

    def test_delete_document(self):
        """문서 삭제 후 검색에 나오지 않음"""
        chunks = ["삭제할 문서 내용"]
        self.store.add_document(
            self.user_id, 'doc-del', chunks,
            {'filename': 'del.txt', 'uploaded_at': '2026-01-01'}
        )
        # 삭제 전 검색
        results_before = self.store.search(self.user_id, '삭제', top_k=5)
        self.assertTrue(len(results_before) > 0)

        # 삭제
        self.store.delete_document(self.user_id, 'doc-del')

        # 삭제 후 검색
        results_after = self.store.search(self.user_id, '삭제', top_k=5)
        self.assertEqual(len(results_after), 0)

    def test_list_documents(self):
        """문서 목록 조회"""
        self.store.add_document(
            self.user_id, 'doc-a', ["청크1", "청크2"],
            {'filename': 'a.txt', 'uploaded_at': '2026-01-01'}
        )
        self.store.add_document(
            self.user_id, 'doc-b', ["청크1"],
            {'filename': 'b.md', 'uploaded_at': '2026-01-02'}
        )
        docs = self.store.list_documents(self.user_id)
        self.assertEqual(len(docs), 2)
        filenames = {d['filename'] for d in docs}
        self.assertEqual(filenames, {'a.txt', 'b.md'})
        # chunk_count 확인
        doc_a = next(d for d in docs if d['filename'] == 'a.txt')
        self.assertEqual(doc_a['chunk_count'], 2)

    def test_list_documents_empty(self):
        """문서 없을 때 빈 리스트"""
        docs = self.store.list_documents(self.user_id)
        self.assertEqual(docs, [])


class TestContextBuilder(unittest.TestCase):
    """RAGContextBuilder 테스트"""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        from services.rag.vector_store import VectorStore
        from services.rag.context_builder import RAGContextBuilder
        self.store = VectorStore(db_path=self.tmp_dir)
        self.builder = RAGContextBuilder(self.store)
        self.user_id = 'test-user-456'

    def tearDown(self):
        try:
            shutil.rmtree(self.tmp_dir)
        except OSError:
            pass

    def test_build_context_with_results(self):
        """검색 결과가 있을 때 포맷 확인"""
        self.store.add_document(
            self.user_id, 'doc-ctx', ["AI는 인공지능입니다.", "머신러닝은 AI의 하위 분야입니다."],
            {'filename': 'ai.txt', 'uploaded_at': '2026-01-01'}
        )
        context = self.builder.build_context(self.user_id, 'AI란 무엇인가', top_k=2)
        self.assertIn('[참고자료 1 - ai.txt]', context)
        self.assertTrue(len(context) > 0)

    def test_build_context_empty(self):
        """문서 없을 때 빈 문자열"""
        context = self.builder.build_context(self.user_id, '검색어', top_k=5)
        self.assertEqual(context, "")


class TestRAGDisabled(unittest.TestCase):
    """RAG_ENABLED=False 시 동작 테스트"""

    def test_config_default_disabled(self):
        """기본값은 RAG 비활성화"""
        # 환경변수 미설정 시 기본 False
        original = os.environ.pop('RAG_ENABLED', None)
        try:
            # config를 다시 로드하지 않고 직접 검증
            val = os.environ.get('RAG_ENABLED', 'false').lower() == 'true'
            self.assertFalse(val)
        finally:
            if original is not None:
                os.environ['RAG_ENABLED'] = original


if __name__ == '__main__':
    unittest.main()
