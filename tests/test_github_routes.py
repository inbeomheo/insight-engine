"""GitHub README 추출 라우트 테스트."""
import unittest
from unittest.mock import patch

from app import create_app

_HEADERS = {'Origin': 'http://localhost:3000'}


class TestGitHubRoutes(unittest.TestCase):
    """POST /api/github/readme 테스트."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.platform.github_service.extract_github_readme')
    def test_readme_returns_content(self, mock_extract, _mock_sb):
        """유효한 URL로 README 반환."""
        mock_extract.return_value = {
            'title': 'facebook/react',
            'content': 'A JavaScript library for building UIs',
            'url': 'https://github.com/facebook/react',
            'source_type': 'github',
            'stars': 230000,
            'forks': 47000,
        }
        resp = self.client.post('/api/github/readme',
                                json={'url': 'https://github.com/facebook/react'},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['source_type'], 'github')
        self.assertIn('content', data)
        self.assertEqual(data['stars'], 230000)
        self.assertEqual(data['forks'], 47000)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_empty_url_returns_400(self, _mock_sb):
        """빈 URL은 400."""
        resp = self.client.post('/api/github/readme',
                                json={'url': ''},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.platform.github_service.extract_github_readme',
           side_effect=ValueError('유효하지 않은 GitHub URL'))
    def test_invalid_url_returns_400(self, mock_extract, _mock_sb):
        """잘못된 URL은 400."""
        resp = self.client.post('/api/github/readme',
                                json={'url': 'https://not-github.com/foo'},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 400)


if __name__ == '__main__':
    unittest.main()
