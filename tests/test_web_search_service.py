"""web_search_service 단위 테스트"""
import unittest
from unittest.mock import patch, MagicMock

from services.data.web_search_service import search, extract_grounding_context, TAVILY_API_URL


class TestSearch(unittest.TestCase):

    @patch.dict('os.environ', {'TAVILY_API_KEY': ''}, clear=False)
    def test_no_api_key(self):
        """API 키 없음 → 빈 리스트"""
        result = search('test query')
        self.assertEqual(result, [])

    @patch('services.data.web_search_service.requests.post')
    @patch.dict('os.environ', {'TAVILY_API_KEY': 'test-key'}, clear=False)
    def test_success(self, mock_post):
        """정상 검색"""
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            'results': [
                {'title': '결과1', 'url': 'https://a.com', 'content': '내용1', 'score': 0.9},
                {'title': '결과2', 'url': 'https://b.com', 'content': '내용2', 'score': 0.7},
            ]
        }
        mock_post.return_value = mock_resp

        result = search('AI 트렌드', max_results=5)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['title'], '결과1')
        self.assertEqual(result[0]['url'], 'https://a.com')

    @patch('services.data.web_search_service.requests.post')
    @patch.dict('os.environ', {'TAVILY_API_KEY': 'test-key'}, clear=False)
    def test_excludes_no_url(self, mock_post):
        """URL 없는 결과 제외"""
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            'results': [
                {'title': 'OK', 'url': 'https://ok.com', 'content': 'c', 'score': 0.5},
                {'title': 'No URL', 'url': '', 'content': 'c', 'score': 0.3},
            ]
        }
        mock_post.return_value = mock_resp

        result = search('test')
        self.assertEqual(len(result), 1)

    @patch('services.data.web_search_service.requests.post', side_effect=Exception('network'))
    @patch.dict('os.environ', {'TAVILY_API_KEY': 'test-key'}, clear=False)
    def test_request_error(self, mock_post):
        """네트워크 오류 → 빈 리스트"""
        result = search('test')
        self.assertEqual(result, [])

    def test_api_url_constant(self):
        """API URL 상수"""
        self.assertEqual(TAVILY_API_URL, 'https://api.tavily.com/search')


class TestExtractGroundingContext(unittest.TestCase):

    @patch('services.data.web_search_service.search', return_value=[])
    def test_no_results(self, mock_search):
        """검색 결과 없음 → enabled=False"""
        result = extract_grounding_context('요약 텍스트')
        self.assertFalse(result['enabled'])
        self.assertEqual(result['results'], [])
        self.assertEqual(result['context_text'], '')

    @patch('services.data.web_search_service.search')
    def test_with_results(self, mock_search):
        """검색 결과 있음 → context_text 생성"""
        mock_search.return_value = [
            {'title': '웹 결과', 'url': 'https://x.com', 'content': '내용입니다', 'score': 0.8}
        ]
        result = extract_grounding_context('AI 기술 요약')
        self.assertTrue(result['enabled'])
        self.assertEqual(len(result['results']), 1)
        self.assertIn('웹 결과', result['context_text'])
        self.assertIn('https://x.com', result['context_text'])

    @patch('services.data.web_search_service.search')
    def test_context_text_format(self, mock_search):
        """context_text 번호 매기기"""
        mock_search.return_value = [
            {'title': 'A', 'url': 'https://a.com', 'content': 'aa', 'score': 0.9},
            {'title': 'B', 'url': 'https://b.com', 'content': 'bb', 'score': 0.7},
        ]
        result = extract_grounding_context('테스트')
        self.assertIn('1.', result['context_text'])
        self.assertIn('2.', result['context_text'])


if __name__ == '__main__':
    unittest.main()
