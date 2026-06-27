"""arxiv_service 단위 테스트 (XML 파싱 위주)"""
import unittest
from unittest.mock import patch
from xml.etree import ElementTree

from services.data.arxiv_service import (
    _ATOM_NS,
    _ARXIV_NS,
    _is_arxiv_pdf_url,
    _ns,
    _parse_entry,
    fetch_paper_fulltext,
)


def _make_entry_xml(
    title="Test Paper Title",
    summary="This is the abstract.",
    arxiv_id="2303.08774",
    authors=None,
    published="2023-03-15T00:00:00Z",
    pdf_url="http://arxiv.org/pdf/2303.08774v1",
    primary_category="cs.AI",
    categories=None,
):
    """테스트용 Atom <entry> XML 문자열 생성"""
    authors = authors or ["Author One", "Author Two"]
    categories = categories or ["cs.AI", "cs.LG"]

    author_xml = "\n".join(
        f'<author xmlns="{_ATOM_NS}"><name>{a}</name></author>'
        for a in authors
    )
    cat_xml = "\n".join(
        f'<category xmlns="{_ATOM_NS}" term="{c}"/>'
        for c in categories
    )

    xml = f"""<entry xmlns="{_ATOM_NS}">
        <id>http://arxiv.org/abs/{arxiv_id}</id>
        <title>{title}</title>
        <summary>{summary}</summary>
        <published>{published}</published>
        {author_xml}
        <link xmlns="{_ATOM_NS}" title="pdf" href="{pdf_url}" rel="related" type="application/pdf"/>
        <arxiv:primary_category xmlns:arxiv="{_ARXIV_NS}" term="{primary_category}"/>
        {cat_xml}
    </entry>"""
    return ElementTree.fromstring(xml)


class TestNs(unittest.TestCase):

    def test_ns_tag(self):
        """네임스페이스 접두사 반환"""
        result = _ns("entry")
        self.assertEqual(result, f"{{{_ATOM_NS}}}entry")

    def test_ns_title(self):
        """title 태그 네임스페이스"""
        result = _ns("title")
        self.assertIn("title", result)
        self.assertIn(_ATOM_NS, result)


class TestParseEntry(unittest.TestCase):

    def test_basic_fields(self):
        """기본 필드 파싱"""
        entry = _make_entry_xml()
        result = _parse_entry(entry)
        self.assertEqual(result['title'], 'Test Paper Title')
        self.assertEqual(result['abstract'], 'This is the abstract.')
        self.assertEqual(result['arxiv_id'], '2303.08774')
        self.assertEqual(result['source_type'], 'arxiv')

    def test_authors(self):
        """저자 목록 파싱"""
        entry = _make_entry_xml(authors=["Alice", "Bob", "Charlie"])
        result = _parse_entry(entry)
        self.assertEqual(result['authors'], ['Alice', 'Bob', 'Charlie'])

    def test_published_date(self):
        """발행일 파싱 (YYYY-MM-DD 형식)"""
        entry = _make_entry_xml(published="2024-01-20T12:00:00Z")
        result = _parse_entry(entry)
        self.assertEqual(result['published'], '2024-01-20')

    def test_pdf_url(self):
        """PDF URL 파싱"""
        entry = _make_entry_xml(pdf_url="http://arxiv.org/pdf/2303.08774v2")
        result = _parse_entry(entry)
        self.assertEqual(result['pdf_url'], 'http://arxiv.org/pdf/2303.08774v2')

    def test_url_format(self):
        """논문 URL 형식"""
        entry = _make_entry_xml(arxiv_id="2401.12345")
        result = _parse_entry(entry)
        self.assertEqual(result['url'], 'https://arxiv.org/abs/2401.12345')

    def test_category(self):
        """카테고리 파싱"""
        entry = _make_entry_xml(primary_category="cs.CL")
        result = _parse_entry(entry)
        self.assertEqual(result['category'], 'cs.CL')

    def test_categories_list(self):
        """복수 카테고리 파싱"""
        entry = _make_entry_xml(categories=["cs.AI", "cs.LG", "stat.ML"])
        result = _parse_entry(entry)
        self.assertIn('cs.AI', result['categories'])
        self.assertIn('cs.LG', result['categories'])
        self.assertIn('stat.ML', result['categories'])

    def test_content_includes_title_and_abstract(self):
        """content 필드에 제목과 초록 포함"""
        entry = _make_entry_xml(title="딥러닝 논문", summary="딥러닝에 관한 연구입니다.")
        result = _parse_entry(entry)
        self.assertIn('딥러닝 논문', result['content'])
        self.assertIn('딥러닝에 관한 연구입니다', result['content'])

    def test_content_includes_authors(self):
        """content 필드에 저자 포함"""
        entry = _make_entry_xml(authors=["홍길동"])
        result = _parse_entry(entry)
        self.assertIn('홍길동', result['content'])

    def test_whitespace_normalization(self):
        """제목/초록 공백 정규화"""
        entry = _make_entry_xml(
            title="Title   with\n  spaces",
            summary="Abstract   with\n\n  newlines"
        )
        result = _parse_entry(entry)
        self.assertNotIn('\n', result['title'])
        self.assertNotIn('  ', result['title'])
        self.assertNotIn('\n', result['abstract'])


class TestArxivPdfUrlSafety(unittest.TestCase):

    def test_arxiv_pdf_url_allowed_when_public(self):
        with patch('services.data.arxiv_service.public_url_error', return_value=None):
            self.assertTrue(_is_arxiv_pdf_url('https://arxiv.org/pdf/2303.08774'))

    def test_non_arxiv_pdf_url_blocked(self):
        with patch('services.data.arxiv_service.public_url_error', return_value=None):
            self.assertFalse(_is_arxiv_pdf_url('https://evil.example/pdf/2303.08774'))

    def test_arxiv_dns_private_result_blocked(self):
        with patch(
            'services.data.arxiv_service.public_url_error',
            return_value='arXiv PDF URL DNS 해석 결과가 안전하지 않아 차단되었습니다.',
        ):
            self.assertFalse(_is_arxiv_pdf_url('https://arxiv.org/pdf/2303.08774'))

    @patch('services.data.arxiv_service.requests.get')
    @patch('services.data.arxiv_service.fetch_paper')
    def test_fulltext_blocks_unsafe_pdf_url_without_download(self, mock_fetch, mock_get):
        paper = {
            'title': 'T',
            'abstract': 'A',
            'authors': [],
            'published': '',
            'category': '',
            'pdf_url': 'http://127.0.0.1/private.pdf',
        }
        mock_fetch.return_value = dict(paper)

        result = fetch_paper_fulltext('2303.08774')

        self.assertEqual(result['pdf_url'], paper['pdf_url'])
        self.assertNotIn('fulltext', result)
        mock_get.assert_not_called()


if __name__ == '__main__':
    unittest.main()
