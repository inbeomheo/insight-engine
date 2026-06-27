"""Google Docs 서비스 단위 테스트"""
import unittest
from unittest.mock import patch, MagicMock

from services.export.gdocs_service import extract_google_doc, _extract_doc_id


class TestExtractDocId(unittest.TestCase):
    """Google Docs URL에서 문서 ID 추출 테스트"""

    def test_standard_url(self):
        url = 'https://docs.google.com/document/d/1aBcDeFgHiJkLmNoPqRsTuVwXyZ/edit'
        self.assertEqual(_extract_doc_id(url), '1aBcDeFgHiJkLmNoPqRsTuVwXyZ')

    def test_url_with_params(self):
        url = 'https://docs.google.com/document/d/abc123_-XYZ/edit?usp=sharing'
        self.assertEqual(_extract_doc_id(url), 'abc123_-XYZ')

    def test_invalid_url(self):
        with self.assertRaises(ValueError):
            _extract_doc_id('https://google.com/not-docs')


class TestExtractGoogleDoc(unittest.TestCase):
    """Google Docs 추출 통합 테스트"""

    @patch('services.export.gdocs_service.requests.get')
    def test_public_export_success(self, mock_get):
        resp = MagicMock()
        resp.status_code = 200
        resp.text = '문서 제목\n\n본문 내용이 여기에 있습니다. 충분히 긴 텍스트입니다. 50자 이상을 확보하기 위해 더 긴 문장을 추가합니다.'
        mock_get.return_value = resp

        result = extract_google_doc(
            'https://docs.google.com/document/d/test123/edit'
        )

        self.assertEqual(result['title'], '문서 제목')
        self.assertIn('본문 내용', result['content'])
        self.assertEqual(result['source_type'], 'gdocs')
        self.assertFalse(mock_get.call_args.kwargs['allow_redirects'])

    @patch('services.export.gdocs_service.requests.get')
    def test_fallback_to_api(self, mock_get):
        # 공개 export 실패
        export_resp = MagicMock()
        export_resp.status_code = 403
        export_resp.text = ''

        # API 성공
        api_resp = MagicMock()
        api_resp.status_code = 200
        api_resp.json.return_value = {
            'title': 'API 문서 제목',
            'body': {
                'content': [
                    {
                        'paragraph': {
                            'elements': [
                                {'textRun': {'content': 'API로 가져온 본문 내용입니다.\n'}},
                            ],
                        },
                    },
                ],
            },
        }

        mock_get.side_effect = [export_resp, api_resp]

        result = extract_google_doc(
            'https://docs.google.com/document/d/test123/edit',
            api_key='test_api_key',
        )

        self.assertEqual(result['title'], 'API 문서 제목')
        self.assertIn('API로 가져온', result['content'])
        self.assertEqual(result['source_type'], 'gdocs')
        self.assertFalse(mock_get.call_args_list[0].kwargs['allow_redirects'])
        self.assertFalse(mock_get.call_args_list[1].kwargs['allow_redirects'])

    @patch('services.export.gdocs_service.requests.get')
    def test_no_access_no_key(self, mock_get):
        resp = MagicMock()
        resp.status_code = 403
        resp.text = ''
        mock_get.return_value = resp

        with self.assertRaises(ValueError) as ctx:
            extract_google_doc(
                'https://docs.google.com/document/d/test123/edit'
            )
        self.assertIn('접근할 수 없습니다', str(ctx.exception))

    @patch('services.export.gdocs_service.requests.get')
    def test_export_short_content_fallback(self, mock_get):
        """본문이 50자 미만이면 유효하지 않은 것으로 간주"""
        export_resp = MagicMock()
        export_resp.status_code = 200
        export_resp.text = 'Too short'  # 50자 미만

        mock_get.return_value = export_resp

        with self.assertRaises(ValueError):
            extract_google_doc(
                'https://docs.google.com/document/d/test123/edit'
            )

    @patch('services.export.gdocs_service.requests.get')
    def test_api_redirect_blocked(self, mock_get):
        export_resp = MagicMock()
        export_resp.status_code = 403
        export_resp.text = ''
        api_resp = MagicMock(status_code=302)
        mock_get.side_effect = [export_resp, api_resp]

        with self.assertRaises(ValueError) as ctx:
            extract_google_doc(
                'https://docs.google.com/document/d/test123/edit',
                api_key='test_api_key',
            )

        self.assertIn('리다이렉트 차단', str(ctx.exception))
        self.assertFalse(mock_get.call_args_list[1].kwargs['allow_redirects'])


if __name__ == '__main__':
    unittest.main()
