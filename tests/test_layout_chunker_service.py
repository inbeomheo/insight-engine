"""layout_chunker_service 단위 테스트."""

import unittest

from services.layout_chunker_service import LayoutChunk, chunk_with_layout


class TestChunkWithLayoutEmpty(unittest.TestCase):
    """빈/공백 문서 처리."""

    def test_empty_string_returns_empty_list(self):
        result = chunk_with_layout('')
        self.assertEqual(result, [])

    def test_none_returns_empty_list(self):
        result = chunk_with_layout(None)
        self.assertEqual(result, [])

    def test_whitespace_only_returns_empty_list(self):
        result = chunk_with_layout('   \n\n  \t  ')
        self.assertEqual(result, [])


class TestChunkWithLayoutHeading(unittest.TestCase):
    """헤딩 인식 테스트."""

    def test_single_heading(self):
        doc = '# 제목입니다'
        chunks = chunk_with_layout(doc)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].chunk_type, 'heading')
        self.assertEqual(chunks[0].heading, '제목입니다')

    def test_heading_levels(self):
        doc = '## 두번째 레벨'
        chunks = chunk_with_layout(doc)
        self.assertEqual(chunks[0].metadata.get('heading_level'), 2)

    def test_heading_followed_by_paragraph(self):
        doc = '# 제목\n\n이것은 본문입니다.'
        chunks = chunk_with_layout(doc)
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0].chunk_type, 'heading')
        self.assertEqual(chunks[1].chunk_type, 'paragraph')
        # 단락이 올바른 헤딩에 속해야 함
        self.assertEqual(chunks[1].heading, '제목')

    def test_multiple_sections(self):
        doc = '# 섹션A\n\n내용A\n\n# 섹션B\n\n내용B'
        chunks = chunk_with_layout(doc)
        # 섹션A 헤딩 + 내용 + 섹션B 헤딩 + 내용 = 4개
        self.assertEqual(len(chunks), 4)
        self.assertEqual(chunks[1].heading, '섹션A')
        self.assertEqual(chunks[3].heading, '섹션B')


class TestChunkWithLayoutTable(unittest.TestCase):
    """마크다운 표 인식."""

    def test_simple_table(self):
        doc = '| 이름 | 가격 |\n|------|------|\n| 사과 | 1000 |\n| 배 | 2000 |'
        chunks = chunk_with_layout(doc)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].chunk_type, 'table')
        # 표 구조 전체가 content에 보존되는지 확인
        self.assertIn('사과', chunks[0].content)
        self.assertIn('배', chunks[0].content)

    def test_table_metadata(self):
        doc = '| A | B | C |\n|---|---|---|\n| 1 | 2 | 3 |'
        chunks = chunk_with_layout(doc)
        meta = chunks[0].metadata
        # 데이터 행 수 (구분선 제외)
        self.assertEqual(meta['row_count'], 2)  # 헤더 + 데이터1
        self.assertEqual(meta['col_count'], 3)

    def test_table_after_heading(self):
        doc = '## 가격표\n\n| 품목 | 가격 |\n|------|------|\n| 볼트 | 500 |'
        chunks = chunk_with_layout(doc)
        table_chunk = [c for c in chunks if c.chunk_type == 'table'][0]
        self.assertEqual(table_chunk.heading, '가격표')


class TestChunkWithLayoutCodeBlock(unittest.TestCase):
    """코드 블록 인식."""

    def test_fenced_code_block(self):
        doc = '```python\nprint("hello")\n```'
        chunks = chunk_with_layout(doc)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].chunk_type, 'code_block')
        self.assertIn('print("hello")', chunks[0].content)

    def test_code_block_language_metadata(self):
        doc = '```javascript\nconsole.log("hi");\n```'
        chunks = chunk_with_layout(doc)
        self.assertEqual(chunks[0].metadata.get('language'), 'javascript')

    def test_unclosed_code_block(self):
        """닫히지 않은 코드 블록도 처리."""
        doc = '```\nsome code\nmore code'
        chunks = chunk_with_layout(doc)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].chunk_type, 'code_block')


class TestChunkWithLayoutList(unittest.TestCase):
    """리스트 인식."""

    def test_unordered_list(self):
        doc = '- 항목1\n- 항목2\n- 항목3'
        chunks = chunk_with_layout(doc)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].chunk_type, 'list')
        self.assertEqual(chunks[0].metadata['item_count'], 3)

    def test_ordered_list(self):
        doc = '1. 첫번째\n2. 두번째\n3. 세번째'
        chunks = chunk_with_layout(doc)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].chunk_type, 'list')

    def test_list_in_section(self):
        doc = '# 목록\n\n- a\n- b'
        chunks = chunk_with_layout(doc)
        list_chunks = [c for c in chunks if c.chunk_type == 'list']
        self.assertEqual(len(list_chunks), 1)
        self.assertEqual(list_chunks[0].heading, '목록')


class TestChunkWithLayoutMixed(unittest.TestCase):
    """복합 문서 처리."""

    def test_mixed_document(self):
        doc = (
            '# 소개\n\n'
            '이것은 소개 문단입니다.\n\n'
            '## 데이터\n\n'
            '| 키 | 값 |\n|---|---|\n| a | 1 |\n\n'
            '## 코드\n\n'
            '```python\nx = 1\n```\n\n'
            '- 항목A\n- 항목B'
        )
        chunks = chunk_with_layout(doc)

        types = [c.chunk_type for c in chunks]
        self.assertIn('heading', types)
        self.assertIn('paragraph', types)
        self.assertIn('table', types)
        self.assertIn('code_block', types)
        self.assertIn('list', types)

    def test_position_monotonic(self):
        """position이 단조 증가하는지 확인."""
        doc = '# A\n\n문단\n\n# B\n\n- 리스트'
        chunks = chunk_with_layout(doc)
        positions = [c.position for c in chunks]
        self.assertEqual(positions, sorted(positions))
        # 중복 없이 연속
        self.assertEqual(positions, list(range(len(chunks))))


class TestChunkWithLayoutMaxSize(unittest.TestCase):
    """max_chunk_size 제한."""

    def test_long_paragraph_is_split(self):
        long_text = '이것은 매우 긴 문단입니다. ' * 100
        chunks = chunk_with_layout(long_text, max_chunk_size=100)
        for c in chunks:
            self.assertLessEqual(len(c.content), 100)
        self.assertGreater(len(chunks), 1)

    def test_small_text_not_split(self):
        chunks = chunk_with_layout('짧은 텍스트', max_chunk_size=500)
        self.assertEqual(len(chunks), 1)


class TestLayoutChunkDataclass(unittest.TestCase):
    """LayoutChunk 데이터클래스 기본 동작."""

    def test_default_metadata(self):
        chunk = LayoutChunk(
            chunk_id='test',
            content='내용',
            chunk_type='paragraph',
            heading='',
            position=0,
        )
        self.assertEqual(chunk.metadata, {})

    def test_chunk_id_uniqueness(self):
        doc = '# A\n\n문단1\n\n# B\n\n문단2'
        chunks = chunk_with_layout(doc)
        ids = [c.chunk_id for c in chunks]
        self.assertEqual(len(ids), len(set(ids)), 'chunk_id는 고유해야 합니다')


if __name__ == '__main__':
    unittest.main()
