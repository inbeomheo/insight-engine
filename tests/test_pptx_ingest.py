"""PPTX 추출 단위 테스트"""
import unittest
from unittest.mock import patch, MagicMock

from services.document_ingest_service import _extract_pptx, extract_text, ALLOWED_MIME_TYPES


PPTX_MIME = 'application/vnd.openxmlformats-officedocument.presentationml.presentation'


def _make_slides_mock(slides_list):
    """slides를 반복 가능하고 len 지원하는 MagicMock으로 생성"""
    mock = MagicMock()
    mock.__iter__ = MagicMock(return_value=iter(slides_list))
    mock.__len__ = MagicMock(return_value=len(slides_list))
    mock.__getitem__ = MagicMock(side_effect=lambda i: slides_list[i])
    return mock


class TestPptxMimeType(unittest.TestCase):
    def test_pptx_mime_registered(self):
        self.assertIn(PPTX_MIME, ALLOWED_MIME_TYPES)
        self.assertEqual(ALLOWED_MIME_TYPES[PPTX_MIME], 'pptx')


class TestExtractPptx(unittest.TestCase):

    @patch('pptx.Presentation')
    def test_basic_extraction(self, MockPresentation):
        """슬라이드 제목 + 본문 추출"""
        title_shape = MagicMock()
        title_shape.text = '슬라이드 제목'
        title_shape.has_text_frame = True
        title_shape.text_frame.text = '슬라이드 제목'

        body_shape = MagicMock()
        body_shape.has_text_frame = True
        body_shape.text_frame.text = '본문 내용입니다.'

        slide = MagicMock()
        slide.shapes.title = title_shape
        slide.shapes.__iter__ = MagicMock(return_value=iter([title_shape, body_shape]))
        slide.has_notes_slide = False

        prs = MagicMock()
        prs.slides = _make_slides_mock([slide])
        MockPresentation.return_value = prs

        result = _extract_pptx('test.pptx')

        self.assertEqual(result['title'], '슬라이드 제목')
        self.assertIn('본문 내용', result['content'])
        self.assertEqual(result['source_type'], 'document')
        self.assertEqual(result['page_count'], 1)

    @patch('pptx.Presentation')
    def test_with_notes(self, MockPresentation):
        """발표자 노트 포함 추출"""
        title_shape = MagicMock()
        title_shape.text = '제목'
        title_shape.has_text_frame = True
        title_shape.text_frame.text = '제목'

        slide = MagicMock()
        slide.shapes.title = title_shape
        slide.shapes.__iter__ = MagicMock(return_value=iter([title_shape]))
        slide.has_notes_slide = True
        slide.notes_slide.notes_text_frame.text = '발표자 노트 내용'

        prs = MagicMock()
        prs.slides = _make_slides_mock([slide])
        MockPresentation.return_value = prs

        result = _extract_pptx('test.pptx')

        self.assertIn('노트: 발표자 노트 내용', result['content'])

    @patch('pptx.Presentation')
    def test_empty_pptx(self, MockPresentation):
        """빈 PPTX 파일"""
        slide = MagicMock()
        slide.shapes.title = None
        slide.shapes.__iter__ = MagicMock(return_value=iter([]))
        slide.has_notes_slide = False

        prs = MagicMock()
        prs.slides = _make_slides_mock([slide])
        MockPresentation.return_value = prs

        with self.assertRaises(ValueError) as ctx:
            _extract_pptx('empty.pptx')
        self.assertIn('추출할 수 없습니다', str(ctx.exception))

    @patch('pptx.Presentation')
    def test_invalid_file(self, MockPresentation):
        """손상된 PPTX 파일"""
        MockPresentation.side_effect = Exception('Invalid file')

        with self.assertRaises(ValueError) as ctx:
            _extract_pptx('invalid.pptx')
        self.assertIn('읽을 수 없습니다', str(ctx.exception))


class TestExtractTextPptxRouting(unittest.TestCase):

    @patch('services.document_ingest_service._extract_pptx')
    def test_routes_to_pptx(self, mock_extract):
        mock_extract.return_value = {
            'title': 'test', 'content': 'test content',
            'source_type': 'document', 'page_count': 1,
        }
        extract_text('test.pptx', PPTX_MIME)
        mock_extract.assert_called_once_with('test.pptx')


if __name__ == '__main__':
    unittest.main()
