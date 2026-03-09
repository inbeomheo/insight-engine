"""Structured RAG 서비스 테스트"""
import unittest
from services.structured_rag_service import (
    RAGChunk, RAGContext, RAGResponse,
    chunk_document, search_chunks, build_context, format_response,
    _estimate_tokens,
)


class TestChunkDocument(unittest.TestCase):
    """문서 청킹 테스트"""

    def test_basic_chunking(self):
        """기본 문장 단위 청킹"""
        text = '첫 번째 문장입니다. 두 번째 문장입니다. 세 번째 문장입니다.'
        chunks = chunk_document(text, chunk_size=30, overlap=0)
        self.assertGreater(len(chunks), 0)
        for chunk in chunks:
            self.assertTrue(len(chunk.chunk_id) > 0)
            self.assertTrue(len(chunk.content) > 0)

    def test_chunk_size_limit(self):
        """청크 크기 제한 확인"""
        text = '. '.join([f'문장 {i}번 내용' for i in range(20)])
        chunks = chunk_document(text, chunk_size=50, overlap=0)
        for chunk in chunks:
            # 오버랩 없이 각 청크는 chunk_size 근처
            self.assertLessEqual(len(chunk.content), 80)  # 문장 단위라 약간 초과 가능

    def test_overlap(self):
        """오버랩 적용 확인"""
        text = '첫 번째 문장입니다. 두 번째 문장입니다. 세 번째 문장입니다. 네 번째 문장입니다.'
        chunks = chunk_document(text, chunk_size=30, overlap=10)
        self.assertGreater(len(chunks), 1)

    def test_empty_text(self):
        chunks = chunk_document('', chunk_size=200)
        self.assertEqual(len(chunks), 0)

    def test_single_sentence(self):
        chunks = chunk_document('단일 문장.', chunk_size=200)
        self.assertEqual(len(chunks), 1)

    def test_metadata_included(self):
        """청크 메타데이터 포함 확인"""
        text = '테스트 문장. 두 번째 문장.'
        chunks = chunk_document(text, chunk_size=200)
        for chunk in chunks:
            self.assertIn('chunk_index', chunk.metadata)
            self.assertIn('char_count', chunk.metadata)

    def test_embedding_hint(self):
        """임베딩 힌트 (키워드) 생성 확인"""
        text = '머신러닝은 인공지능의 한 분야입니다.'
        chunks = chunk_document(text, chunk_size=200)
        for chunk in chunks:
            self.assertIsInstance(chunk.embedding_hint, str)

    def test_large_chunk_size(self):
        """큰 청크 크기 (전체가 1청크)"""
        text = '짧은 텍스트.'
        chunks = chunk_document(text, chunk_size=10000)
        self.assertEqual(len(chunks), 1)


class TestSearchChunks(unittest.TestCase):
    """청크 검색 테스트"""

    def setUp(self):
        self.chunks = [
            RAGChunk('c1', '파이썬은 프로그래밍 언어입니다.', {}, '파이썬 프로그래밍'),
            RAGChunk('c2', '자바는 객체지향 언어입니다.', {}, '자바 객체지향'),
            RAGChunk('c3', '머신러닝은 인공지능의 분야입니다.', {}, '머신러닝 인공지능'),
            RAGChunk('c4', '파이썬으로 머신러닝을 할 수 있습니다.', {}, '파이썬 머신러닝'),
        ]

    def test_keyword_search(self):
        results = search_chunks(self.chunks, '파이썬', top_k=2)
        self.assertGreater(len(results), 0)
        # 파이썬 관련 청크가 상위에
        contents = [r.content for r in results]
        self.assertTrue(any('파이썬' in c for c in contents))

    def test_top_k_limit(self):
        results = search_chunks(self.chunks, '프로그래밍', top_k=1)
        self.assertEqual(len(results), 1)

    def test_empty_query(self):
        results = search_chunks(self.chunks, '')
        self.assertEqual(len(results), 0)

    def test_no_match(self):
        results = search_chunks(self.chunks, 'ZZZZZ없는단어', top_k=3)
        # 매칭 안 되더라도 결과는 반환 (점수 0)
        self.assertEqual(len(results), 3)

    def test_empty_chunks(self):
        results = search_chunks([], '파이썬')
        self.assertEqual(len(results), 0)


class TestBuildContext(unittest.TestCase):
    """컨텍스트 빌드 테스트"""

    def test_token_limit(self):
        """토큰 제한 내 청크 선택"""
        chunks = [
            RAGChunk('c1', '짧은 텍스트', {}, ''),
            RAGChunk('c2', '이것은 조금 더 긴 텍스트입니다' * 100, {}, ''),
        ]
        context = build_context(chunks, max_tokens=50)
        # 첫 번째 청크만 포함될 가능성
        self.assertGreater(len(context.chunks), 0)
        self.assertLessEqual(context.total_tokens, 50)

    def test_empty_chunks(self):
        context = build_context([], max_tokens=100)
        self.assertEqual(len(context.chunks), 0)
        self.assertEqual(context.total_tokens, 0)

    def test_all_fit(self):
        """모든 청크가 제한 내"""
        chunks = [
            RAGChunk('c1', '짧은', {}, ''),
            RAGChunk('c2', '텍스트', {}, ''),
        ]
        context = build_context(chunks, max_tokens=10000)
        self.assertEqual(len(context.chunks), 2)


class TestFormatResponse(unittest.TestCase):
    """응답 포맷 테스트"""

    def test_sources_from_metadata(self):
        """메타데이터에서 출처 추출"""
        context = RAGContext(
            query='테스트',
            chunks=[
                RAGChunk('c1', '내용', {'source': 'wiki'}, ''),
            ],
            total_tokens=10,
        )
        response = format_response(context, '답변 내용')
        self.assertIn('wiki', response.sources)

    def test_sources_fallback_to_chunk_id(self):
        """메타데이터 없으면 chunk ID 사용"""
        context = RAGContext(
            query='테스트',
            chunks=[RAGChunk('abc123', '내용', {}, '')],
            total_tokens=10,
        )
        response = format_response(context, '답변')
        self.assertTrue(any('abc123' in s for s in response.sources))

    def test_confidence_calculation(self):
        """신뢰도 계산 (청크 수 기반)"""
        context = RAGContext(
            query='테스트',
            chunks=[RAGChunk(f'c{i}', f'내용{i}', {}, '') for i in range(5)],
            total_tokens=100,
        )
        response = format_response(context, '답변')
        self.assertEqual(response.confidence, 1.0)  # 5 * 0.2 = 1.0

    def test_low_confidence(self):
        """적은 청크 → 낮은 신뢰도"""
        context = RAGContext(query='', chunks=[RAGChunk('c1', '내용', {}, '')], total_tokens=5)
        response = format_response(context, '답변')
        self.assertEqual(response.confidence, 0.2)

    def test_empty_context(self):
        context = RAGContext(query='', chunks=[], total_tokens=0)
        response = format_response(context, '답변')
        self.assertEqual(response.confidence, 0.0)
        self.assertEqual(response.sources, [])


class TestEstimateTokens(unittest.TestCase):
    """토큰 추정 테스트"""

    def test_empty(self):
        self.assertEqual(_estimate_tokens(''), 0)

    def test_non_empty(self):
        self.assertGreater(_estimate_tokens('테스트 문장입니다'), 0)


if __name__ == '__main__':
    unittest.main()
