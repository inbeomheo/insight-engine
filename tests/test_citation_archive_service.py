"""
인용 아카이브 서비스 테스트
"""

import unittest

from services.citation_archive_service import (
    Citation,
    CitationArchive,
    _create_archive,
    add_citation,
    search_citations,
    get_by_author,
    verify_citation,
    export_bibliography,
)


class TestAddCitation(unittest.TestCase):
    """인용 추가 테스트"""

    def test_add_single(self):
        """단일 인용 추가"""
        archive = _create_archive()
        archive = add_citation(archive, "지식이 힘이다.", "프랜시스 베이컨", "Meditationes Sacrae")
        self.assertEqual(len(archive.citations), 1)
        self.assertEqual(archive.citations[0].quote, "지식이 힘이다.")
        self.assertEqual(archive.citations[0].author, "프랜시스 베이컨")

    def test_add_with_tags(self):
        """태그 포함 추가"""
        archive = _create_archive()
        archive = add_citation(
            archive, "생각한다 고로 존재한다.", "데카르트", "방법서설",
            tags=["철학", "존재론"],
        )
        self.assertEqual(archive.citations[0].tags, ["철학", "존재론"])

    def test_duplicate_prevention(self):
        """중복 인용 방지"""
        archive = _create_archive()
        archive = add_citation(archive, "지식이 힘이다.", "프랜시스 베이컨", "출처1")
        archive = add_citation(archive, "지식이 힘이다.", "프랜시스 베이컨", "출처2")
        self.assertEqual(len(archive.citations), 1)

    def test_same_quote_different_author(self):
        """같은 인용문 다른 저자는 허용"""
        archive = _create_archive()
        archive = add_citation(archive, "동일 문구", "저자A", "출처A")
        archive = add_citation(archive, "동일 문구", "저자B", "출처B")
        self.assertEqual(len(archive.citations), 2)

    def test_add_multiple(self):
        """여러 인용 추가"""
        archive = _create_archive()
        for i in range(5):
            archive = add_citation(archive, f"인용 {i}", f"저자 {i}", f"출처 {i}")
        self.assertEqual(len(archive.citations), 5)

    def test_add_default_verified_false(self):
        """기본 verified는 False"""
        archive = _create_archive()
        archive = add_citation(archive, "테스트", "저자", "출처")
        self.assertFalse(archive.citations[0].verified)


class TestSearchCitations(unittest.TestCase):
    """인용 검색 테스트"""

    def setUp(self):
        self.archive = _create_archive()
        self.archive = add_citation(
            self.archive, "지식이 힘이다.", "프랜시스 베이컨", "Meditationes",
            tags=["철학", "지식"],
        )
        self.archive = add_citation(
            self.archive, "나는 생각한다 고로 존재한다.", "데카르트", "방법서설",
            tags=["철학", "존재론"],
        )
        self.archive = add_citation(
            self.archive, "시간은 금이다.", "벤자민 프랭클린", "Advice to a Young Tradesman",
            tags=["경제", "시간"],
        )

    def test_search_by_quote(self):
        """인용문으로 검색"""
        results = search_citations(self.archive, "지식", by_field="quote")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].author, "프랜시스 베이컨")

    def test_search_by_author(self):
        """저자로 검색"""
        results = search_citations(self.archive, "데카르트", by_field="author")
        self.assertEqual(len(results), 1)

    def test_search_by_tag(self):
        """태그로 검색"""
        results = search_citations(self.archive, "철학", by_field="tag")
        self.assertEqual(len(results), 2)

    def test_search_empty_query(self):
        """빈 검색어"""
        results = search_citations(self.archive, "")
        self.assertEqual(results, [])

    def test_search_no_results(self):
        """결과 없는 검색"""
        results = search_citations(self.archive, "양자역학", by_field="quote")
        self.assertEqual(results, [])


class TestGetByAuthor(unittest.TestCase):
    """저자별 조회 테스트"""

    def test_get_by_author(self):
        """저자별 조회"""
        archive = _create_archive()
        archive = add_citation(archive, "인용1", "저자A", "출처1")
        archive = add_citation(archive, "인용2", "저자A", "출처2")
        archive = add_citation(archive, "인용3", "저자B", "출처3")
        results = get_by_author(archive, "저자A")
        self.assertEqual(len(results), 2)


class TestVerifyCitation(unittest.TestCase):
    """인용 검증 테스트"""

    def test_verify(self):
        """검증 완료"""
        archive = _create_archive()
        archive = add_citation(archive, "테스트", "저자", "출처")
        cid = archive.citations[0].citation_id
        archive = verify_citation(archive, cid)
        self.assertTrue(archive.citations[0].verified)

    def test_verify_invalid_id(self):
        """잘못된 ID"""
        archive = _create_archive()
        with self.assertRaises(ValueError):
            verify_citation(archive, "nonexistent")


class TestExportBibliography(unittest.TestCase):
    """참고문헌 내보내기 테스트"""

    def setUp(self):
        self.archive = _create_archive()
        self.archive = add_citation(
            self.archive, "지식이 힘이다.", "프랜시스 베이컨", "Meditationes",
            date="1597",
        )

    def test_export_apa(self):
        """APA 스타일"""
        result = export_bibliography(self.archive, format="apa")
        self.assertIn("프랜시스 베이컨", result)
        self.assertIn("(1597)", result)
        self.assertIn("지식이 힘이다.", result)

    def test_export_mla(self):
        """MLA 스타일"""
        result = export_bibliography(self.archive, format="mla")
        self.assertIn("프랜시스 베이컨", result)
        self.assertIn("1597", result)

    def test_export_empty(self):
        """빈 아카이브"""
        archive = _create_archive()
        result = export_bibliography(archive)
        self.assertEqual(result, "")

    def test_export_unknown_format(self):
        """알 수 없는 포맷 (기본 출력)"""
        result = export_bibliography(self.archive, format="unknown")
        self.assertIn("프랜시스 베이컨", result)


if __name__ == "__main__":
    unittest.main()
