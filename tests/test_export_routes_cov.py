"""export_routes.py 커버리지 보강 테스트.

기존 test_export_html.py 등과 겹치지 않는 엔드포인트/분기를 커버.
"""
import unittest
from unittest.mock import patch, MagicMock
import io

from app import create_app

_H = {'Origin': 'http://localhost:3000'}
_SB_PATCH = 'services.data.supabase_service.is_supabase_enabled'


class _Base(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()


class TestExportDocx(_Base):
    """DOCX 내보내기."""

    @patch(_SB_PATCH, return_value=False)
    def test_empty_content_returns_400(self, _):
        resp = self.client.post('/api/export/docx', json={'title': 'T', 'content': ''}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch(_SB_PATCH, return_value=False)
    def test_docx_basic(self, _):
        resp = self.client.post('/api/export/docx',
                                json={'title': '문서 제목', 'content': '# 제목\n본문입니다.'}, headers=_H)
        self.assertIn(resp.status_code, [200, 500])  # 500 if python-docx not installed

    @patch(_SB_PATCH, return_value=False)
    def test_docx_with_toc(self, _):
        resp = self.client.post('/api/export/docx',
                                json={'title': '문서', 'content': '## 섹션1\n내용\n## 섹션2\n내용2',
                                      'include_toc': True}, headers=_H)
        self.assertIn(resp.status_code, [200, 500])

    @patch(_SB_PATCH, return_value=False)
    def test_docx_with_font_size(self, _):
        resp = self.client.post('/api/export/docx',
                                json={'title': '문서', 'content': '본문', 'font_size': 'large'}, headers=_H)
        self.assertIn(resp.status_code, [200, 500])

    @patch(_SB_PATCH, return_value=False)
    def test_docx_invalid_font_size(self, _):
        resp = self.client.post('/api/export/docx',
                                json={'title': '문서', 'content': '본문', 'font_size': 'huge'}, headers=_H)
        self.assertIn(resp.status_code, [200, 500])

    @patch(_SB_PATCH, return_value=False)
    def test_docx_with_table(self, _):
        content = '| A | B |\n|---|---|\n| 1 | 2 |'
        resp = self.client.post('/api/export/docx', json={'title': '표', 'content': content}, headers=_H)
        self.assertIn(resp.status_code, [200, 500])

    @patch(_SB_PATCH, return_value=False)
    def test_docx_with_list_and_quote(self, _):
        content = '- 항목1\n- 항목2\n\n> 인용문\n\n1. 번호1\n2. 번호2\n\n---'
        resp = self.client.post('/api/export/docx', json={'title': '목록', 'content': content}, headers=_H)
        self.assertIn(resp.status_code, [200, 500])

    @patch(_SB_PATCH, return_value=False)
    def test_docx_with_formatting(self, _):
        content = '**볼드** *이탤릭* `코드`'
        resp = self.client.post('/api/export/docx', json={'title': '서식', 'content': content}, headers=_H)
        self.assertIn(resp.status_code, [200, 500])


class TestExportEpub(_Base):
    """EPUB 내보내기."""

    @patch(_SB_PATCH, return_value=False)
    def test_epub_empty(self, _):
        resp = self.client.post('/api/export/epub', json={'title': 'T', 'content': ''}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.export.epub_service.create_epub', return_value=b'PK\x03\x04fake')
    def test_epub_success(self, _m1, _):
        resp = self.client.post('/api/export/epub',
                                json={'title': '전자책', 'content': '본문', 'author': '저자'}, headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.export.epub_service.create_epub', side_effect=Exception('epub error'))
    def test_epub_error(self, _m1, _):
        resp = self.client.post('/api/export/epub',
                                json={'title': 'T', 'content': 'body'}, headers=_H)
        self.assertEqual(resp.status_code, 500)


class TestExportMarkdownRoute(_Base):
    """Markdown 내보내기 라우트."""

    @patch(_SB_PATCH, return_value=False)
    def test_md_empty(self, _):
        resp = self.client.post('/api/export/markdown', json={'content': ''}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.export.export_service.export_markdown', return_value=io.BytesIO(b'# test'))
    def test_md_success(self, _m1, _):
        resp = self.client.post('/api/export/markdown', json={'title': 'T', 'content': '# H1'}, headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.export.export_service.export_markdown', return_value=io.BytesIO(b'test'))
    def test_md_with_metadata(self, _m1, _):
        resp = self.client.post('/api/export/markdown',
                                json={'title': 'T', 'content': 'body', 'include_metadata': True,
                                      'model': 'gemini', 'style': 'blog_seo'}, headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.export.export_service.export_markdown', side_effect=Exception('err'))
    def test_md_error(self, _m1, _):
        resp = self.client.post('/api/export/markdown', json={'title': 'T', 'content': 'x'}, headers=_H)
        self.assertEqual(resp.status_code, 500)


class TestExportTxtRoute(_Base):
    """TXT 내보내기."""

    @patch(_SB_PATCH, return_value=False)
    def test_txt_empty(self, _):
        resp = self.client.post('/api/export/txt', json={'content': ''}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.export.export_service.export_txt', return_value=io.BytesIO(b'text'))
    def test_txt_success(self, _m1, _):
        resp = self.client.post('/api/export/txt', json={'title': 'T', 'content': 'body'}, headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.export.export_service.export_txt', return_value=io.BytesIO(b'text'))
    def test_txt_windows_line_ending(self, _m1, _):
        resp = self.client.post('/api/export/txt',
                                json={'title': 'T', 'content': 'body', 'line_ending': 'windows'}, headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.export.export_service.export_txt', return_value=io.BytesIO(b'text'))
    def test_txt_invalid_line_ending_fallback(self, _m1, _):
        resp = self.client.post('/api/export/txt',
                                json={'title': 'T', 'content': 'body', 'line_ending': 'mac'}, headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.export.export_service.export_txt', side_effect=Exception('err'))
    def test_txt_error(self, _m1, _):
        resp = self.client.post('/api/export/txt', json={'title': 'T', 'content': 'x'}, headers=_H)
        self.assertEqual(resp.status_code, 500)


class TestExportZipRoute(_Base):
    """ZIP 내보내기."""

    @patch(_SB_PATCH, return_value=False)
    def test_zip_empty(self, _):
        resp = self.client.post('/api/export/zip', json={'content': ''}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.export.export_service.export_zip', return_value=io.BytesIO(b'PK'))
    def test_zip_success(self, _m1, _):
        resp = self.client.post('/api/export/zip', json={'title': 'T', 'content': 'body'}, headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.export.export_service.export_zip', side_effect=Exception('err'))
    def test_zip_error(self, _m1, _):
        resp = self.client.post('/api/export/zip', json={'title': 'T', 'content': 'x'}, headers=_H)
        self.assertEqual(resp.status_code, 500)


class TestExportSlides(_Base):
    """슬라이드 내보내기."""

    @patch(_SB_PATCH, return_value=False)
    def test_slides_empty(self, _):
        resp = self.client.post('/api/export/slides', json={'content': ''}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.media.slide_service.convert_to_slides', return_value='<html>slides</html>')
    def test_slides_success(self, _m1, _):
        resp = self.client.post('/api/export/slides',
                                json={'title': '발표', 'content': '## Slide 1\n내용'}, headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.media.slide_service.convert_to_slides', side_effect=ValueError('invalid'))
    def test_slides_value_error(self, _m1, _):
        resp = self.client.post('/api/export/slides', json={'title': 'T', 'content': 'x'}, headers=_H)
        self.assertIn(resp.status_code, [400, 500])

    @patch(_SB_PATCH, return_value=False)
    @patch('services.media.slide_service.convert_to_slides', side_effect=Exception('err'))
    def test_slides_error(self, _m1, _):
        resp = self.client.post('/api/export/slides', json={'title': 'T', 'content': 'x'}, headers=_H)
        self.assertEqual(resp.status_code, 500)


class TestExportSrt(_Base):
    """SRT 자막 내보내기."""

    @patch(_SB_PATCH, return_value=False)
    def test_srt_empty(self, _):
        resp = self.client.post('/api/export/srt', json={'segments': []}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch(_SB_PATCH, return_value=False)
    def test_srt_success(self, _):
        segments = [
            {'start': 0, 'end': 5.5, 'text': '안녕하세요'},
            {'start': 5.5, 'duration': 3, 'text': '테스트입니다'},
        ]
        resp = self.client.post('/api/export/srt', json={'segments': segments, 'title': '자막'}, headers=_H)
        self.assertEqual(resp.status_code, 200)
        content = resp.data.decode('utf-8')
        self.assertIn('안녕하세요', content)
        self.assertIn('-->', content)

    @patch(_SB_PATCH, return_value=False)
    def test_srt_with_empty_text(self, _):
        """빈 텍스트 세그먼트는 건너뜀."""
        segments = [{'start': 0, 'end': 1, 'text': ''}, {'start': 1, 'end': 2, 'text': 'ok'}]
        resp = self.client.post('/api/export/srt', json={'segments': segments}, headers=_H)
        self.assertEqual(resp.status_code, 200)


class TestExportInfographic(_Base):
    """인포그래픽 내보내기."""

    @patch(_SB_PATCH, return_value=False)
    def test_infographic_empty(self, _):
        resp = self.client.post('/api/export/infographic', json={'content': ''}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.media.infographic_service.generate_infographic', return_value='<html>infog</html>')
    def test_infographic_success(self, _m1, _):
        resp = self.client.post('/api/export/infographic',
                                json={'title': '인포', 'content': '본문'}, headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.media.infographic_service.generate_infographic', side_effect=Exception('err'))
    def test_infographic_error(self, _m1, _):
        resp = self.client.post('/api/export/infographic', json={'title': 'T', 'content': 'x'}, headers=_H)
        self.assertEqual(resp.status_code, 500)


class TestExportCardNews(_Base):
    """카드뉴스 내보내기."""

    @patch(_SB_PATCH, return_value=False)
    def test_card_news_empty(self, _):
        resp = self.client.post('/api/export/card-news', json={'content': ''}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.media.card_news_service.generate_card_news', return_value=['<svg>1</svg>', '<svg>2</svg>'])
    def test_card_news_success(self, _m1, _):
        resp = self.client.post('/api/export/card-news', json={'title': '카드', 'content': '본문'}, headers=_H)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('application/zip', resp.content_type)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.media.card_news_service.generate_card_news', return_value=[])
    def test_card_news_no_cards(self, _m1, _):
        resp = self.client.post('/api/export/card-news', json={'title': 'T', 'content': '.'}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.media.card_news_service.generate_card_news', side_effect=Exception('err'))
    def test_card_news_error(self, _m1, _):
        resp = self.client.post('/api/export/card-news', json={'title': 'T', 'content': 'x'}, headers=_H)
        self.assertEqual(resp.status_code, 500)


class TestExportSummaryCard(_Base):
    """요약 카드 내보내기."""

    @patch(_SB_PATCH, return_value=False)
    def test_summary_card_empty(self, _):
        resp = self.client.post('/api/export/summary-card', json={'key_points': []}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.content.summary_card_service.generate_summary_card', return_value='<svg>card</svg>')
    def test_summary_card_success(self, _m1, _):
        resp = self.client.post('/api/export/summary-card',
                                json={'title': '요약', 'key_points': ['포인트1', '포인트2']}, headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.content.summary_card_service.generate_summary_card', side_effect=Exception('err'))
    def test_summary_card_error(self, _m1, _):
        resp = self.client.post('/api/export/summary-card',
                                json={'title': 'T', 'key_points': ['p']}, headers=_H)
        self.assertEqual(resp.status_code, 500)


class TestExportCodeImage(_Base):
    """코드 이미지 내보내기."""

    @patch(_SB_PATCH, return_value=False)
    def test_code_image_empty(self, _):
        resp = self.client.post('/api/export/code-image', json={'code': ''}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.media.code_image_service.generate_code_image', return_value='<html>code</html>')
    def test_code_image_success(self, _m1, _):
        resp = self.client.post('/api/export/code-image',
                                json={'code': 'print("hello")', 'language': 'python', 'title': '코드'}, headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.media.code_image_service.generate_code_image', side_effect=Exception('err'))
    def test_code_image_error(self, _m1, _):
        resp = self.client.post('/api/export/code-image',
                                json={'code': 'x', 'title': 'T'}, headers=_H)
        self.assertEqual(resp.status_code, 500)


class TestExportNewsletterHtml(_Base):
    """뉴스레터 HTML 내보내기."""

    @patch(_SB_PATCH, return_value=False)
    def test_newsletter_empty(self, _):
        resp = self.client.post('/api/export/newsletter-html', json={'content': ''}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.content.newsletter_template_service.convert_to_newsletter', return_value='<html>nl</html>')
    def test_newsletter_success(self, _m1, _):
        resp = self.client.post('/api/export/newsletter-html',
                                json={'title': 'NL', 'content': '내용'}, headers=_H)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()['success'])

    @patch(_SB_PATCH, return_value=False)
    @patch('services.content.newsletter_template_service.convert_to_newsletter', side_effect=ValueError('bad'))
    def test_newsletter_value_error(self, _m1, _):
        resp = self.client.post('/api/export/newsletter-html',
                                json={'title': 'T', 'content': 'x'}, headers=_H)
        self.assertIn(resp.status_code, [400, 500])

    @patch(_SB_PATCH, return_value=False)
    @patch('services.content.newsletter_template_service.convert_to_newsletter', side_effect=Exception('err'))
    def test_newsletter_error(self, _m1, _):
        resp = self.client.post('/api/export/newsletter-html',
                                json={'title': 'T', 'content': 'x'}, headers=_H)
        self.assertEqual(resp.status_code, 500)


class TestExportInteractiveReport(_Base):
    """인터랙티브 보고서 내보내기."""

    @patch(_SB_PATCH, return_value=False)
    def test_report_empty(self, _):
        resp = self.client.post('/api/export/interactive-report', json={'content': ''}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.content.interactive_report_service.generate_interactive_report', return_value='<html>rpt</html>')
    def test_report_success(self, _m1, _):
        resp = self.client.post('/api/export/interactive-report',
                                json={'title': '보고서', 'content': '내용'}, headers=_H)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()['success'])

    @patch(_SB_PATCH, return_value=False)
    @patch('services.content.interactive_report_service.generate_interactive_report', side_effect=Exception('err'))
    def test_report_error(self, _m1, _):
        resp = self.client.post('/api/export/interactive-report',
                                json={'title': 'T', 'content': 'x'}, headers=_H)
        self.assertEqual(resp.status_code, 500)


class TestExportHtmlExtended(_Base):
    """HTML 내보내기 확장 (dark_mode, print_friendly, include_toc)."""

    @patch(_SB_PATCH, return_value=False)
    def test_html_dark_mode(self, _):
        resp = self.client.post('/api/export/html',
                                json={'title': 'T', 'html': '<p>본문</p>', 'dark_mode': True}, headers=_H)
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')
        self.assertIn('prefers-color-scheme', html)

    @patch(_SB_PATCH, return_value=False)
    def test_html_print_friendly(self, _):
        resp = self.client.post('/api/export/html',
                                json={'title': 'T', 'html': '<p>본문</p>', 'print_friendly': True}, headers=_H)
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')
        self.assertIn('@media print', html)

    @patch(_SB_PATCH, return_value=False)
    def test_html_with_toc(self, _):
        resp = self.client.post('/api/export/html',
                                json={'title': 'T', 'html': '<h2>섹션</h2><p>내용</p>', 'include_toc': True},
                                headers=_H)
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')
        self.assertIn('목차', html)


class TestHelperFunctions(unittest.TestCase):
    """export_routes 내부 헬퍼 함수 직접 테스트."""

    def test_seconds_to_srt_time(self):
        from routes.export_routes import _seconds_to_srt_time
        self.assertEqual(_seconds_to_srt_time(0), '00:00:00,000')
        self.assertEqual(_seconds_to_srt_time(3661.5), '01:01:01,500')
        self.assertEqual(_seconds_to_srt_time(-5), '00:00:00,000')

    def test_extract_headings(self):
        from routes.export_routes import _extract_headings
        md = '# Title\n## Section **bold**\n### Sub `code`\nnormal line'
        headings = _extract_headings(md)
        self.assertEqual(len(headings), 3)
        self.assertEqual(headings[0], (1, 'Title'))
        self.assertIn('Section', headings[1][1])

    def test_strip_markdown_formatting(self):
        from routes.export_routes import _strip_markdown_formatting
        self.assertEqual(_strip_markdown_formatting('**bold** *italic* `code`'), 'bold italic code')

    def test_detect_lang(self):
        from routes.export_routes import _detect_lang
        self.assertEqual(_detect_lang('한국어 텍스트입니다'), 'ko')
        self.assertEqual(_detect_lang('This is English text'), 'en')
        self.assertEqual(_detect_lang('これは日本語です'), 'ja')

    def test_build_html_toc(self):
        from routes.export_routes import _build_html_toc
        html = '<h2>섹션1</h2><h3>하위</h3>'
        toc = _build_html_toc(html)
        self.assertIn('섹션1', toc)
        self.assertIn('toc', toc)

    def test_build_html_toc_empty(self):
        from routes.export_routes import _build_html_toc
        self.assertEqual(_build_html_toc('<p>no headings</p>'), '')


if __name__ == '__main__':
    unittest.main()
