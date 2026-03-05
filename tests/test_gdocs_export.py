"""Google Docs 내보내기 서비스 단위 테스트"""
import unittest
from unittest.mock import patch, MagicMock

from services.gdocs_export_service import export_to_gdocs, _markdown_to_docs_requests


class TestGDocsExport(unittest.TestCase):
    """Google Docs 내보내기 테스트"""

    @patch('services.gdocs_export_service.requests.post')
    def test_successful_export(self, mock_post):
        """성공적인 문서 생성"""
        # 1차: 문서 생성, 2차: 콘텐츠 삽입
        create_resp = MagicMock()
        create_resp.status_code = 200
        create_resp.json.return_value = {'documentId': 'doc-123'}

        update_resp = MagicMock()
        update_resp.status_code = 200

        mock_post.side_effect = [create_resp, update_resp]

        result = export_to_gdocs('제목', '# 헤딩\n본문', 'fake-token')
        self.assertTrue(result['success'])
        self.assertIn('doc-123', result['url'])

    @patch('services.gdocs_export_service.requests.post')
    def test_create_failure(self, mock_post):
        """문서 생성 실패"""
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.json.return_value = {'error': {'message': 'Forbidden'}}
        mock_post.return_value = mock_resp

        result = export_to_gdocs('제목', '내용', 'fake-token')
        self.assertFalse(result['success'])

    @patch('services.gdocs_export_service.requests.post')
    def test_connection_error(self, mock_post):
        """연결 오류"""
        import requests
        mock_post.side_effect = requests.RequestException('timeout')

        result = export_to_gdocs('제목', '내용', 'fake-token')
        self.assertFalse(result['success'])
        self.assertIn('연결 실패', result['message'])

    def test_markdown_to_requests_heading(self):
        """헤딩이 insertText + updateParagraphStyle 생성"""
        reqs = _markdown_to_docs_requests('# 제목')
        # insertText + updateParagraphStyle
        self.assertEqual(len(reqs), 2)
        self.assertIn('insertText', reqs[0])
        self.assertIn('updateParagraphStyle', reqs[1])
        self.assertEqual(
            reqs[1]['updateParagraphStyle']['paragraphStyle']['namedStyleType'],
            'HEADING_1'
        )

    def test_markdown_to_requests_plain(self):
        """일반 텍스트는 insertText만"""
        reqs = _markdown_to_docs_requests('일반 텍스트')
        self.assertEqual(len(reqs), 1)
        self.assertIn('insertText', reqs[0])

    def test_markdown_to_requests_bullet(self):
        """비순서 목록에 불릿 기호 추가"""
        reqs = _markdown_to_docs_requests('- 항목')
        self.assertIn('•', reqs[0]['insertText']['text'])


if __name__ == '__main__':
    unittest.main()
