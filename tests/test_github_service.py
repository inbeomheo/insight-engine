"""
GitHub README 추출 서비스 단위 테스트
"""
import base64
import unittest
from unittest.mock import patch, MagicMock

import requests


class TestExtractGithubReadme(unittest.TestCase):
    """extract_github_readme 단위 테스트"""

    @patch("services.platform.github_service._get_repo_metadata", return_value={"description": "테스트 설명", "stars": 1500, "forks": 200})
    @patch("services.platform.github_service.requests.get")
    def test_extracts_readme_successfully(self, mock_get, mock_desc):
        """README를 정상적으로 추출"""
        readme_content = "# My Project\n\nThis is a test README."
        encoded = base64.b64encode(readme_content.encode()).decode()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "content": encoded,
            "encoding": "base64",
        }
        mock_get.return_value = mock_resp

        from services.platform.github_service import extract_github_readme

        result = extract_github_readme("https://github.com/testowner/testrepo")

        self.assertEqual(result["title"], "testowner/testrepo")
        self.assertIn("# My Project", result["content"])
        self.assertIn("테스트 설명", result["content"])
        self.assertEqual(result["source_type"], "github")
        self.assertEqual(result["stars"], 1500)
        self.assertEqual(result["forks"], 200)

    def test_raises_on_invalid_url(self):
        """유효하지 않은 GitHub URL에서 ValueError 발생"""
        from services.platform.github_service import extract_github_readme

        with self.assertRaises(ValueError):
            extract_github_readme("https://example.com/not-github")

    @patch("services.platform.github_service.requests.get")
    def test_raises_on_404(self, mock_get):
        """README가 없는 리포지토리에서 ValueError 발생"""
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.raise_for_status.side_effect = requests.HTTPError(
            response=mock_resp
        )
        mock_get.return_value = mock_resp

        from services.platform.github_service import extract_github_readme

        with self.assertRaises(ValueError):
            extract_github_readme("https://github.com/owner/norepo")

    @patch("services.platform.github_service._get_repo_metadata", return_value={"description": "", "stars": 0, "forks": 0})
    @patch("services.platform.github_service.requests.get")
    def test_strips_git_suffix(self, mock_get, mock_desc):
        """.git 접미사가 자동으로 제거됨"""
        encoded = base64.b64encode(b"# README content here").decode()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"content": encoded, "encoding": "base64"}
        mock_get.return_value = mock_resp

        from services.platform.github_service import extract_github_readme

        result = extract_github_readme("https://github.com/owner/repo.git")

        self.assertEqual(result["title"], "owner/repo")

    @patch("services.platform.github_service._get_repo_metadata", return_value={"description": "", "stars": 0, "forks": 0})
    @patch("services.platform.github_service.requests.get")
    def test_raises_on_empty_readme(self, mock_get, mock_desc):
        """빈 README에서 ValueError 발생"""
        encoded = base64.b64encode(b"").decode()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"content": encoded, "encoding": "base64"}
        mock_get.return_value = mock_resp

        from services.platform.github_service import extract_github_readme

        with self.assertRaises(ValueError):
            extract_github_readme("https://github.com/owner/emptyrepo")


class TestParseGithubUrl(unittest.TestCase):
    """_parse_github_url 단위 테스트"""

    def test_parses_standard_url(self):
        from services.platform.github_service import _parse_github_url
        owner, repo = _parse_github_url("https://github.com/facebook/react")
        self.assertEqual(owner, "facebook")
        self.assertEqual(repo, "react")

    def test_parses_url_with_git_suffix(self):
        from services.platform.github_service import _parse_github_url
        owner, repo = _parse_github_url("https://github.com/user/repo.git")
        self.assertEqual(repo, "repo")

    def test_raises_on_non_github(self):
        from services.platform.github_service import _parse_github_url
        with self.assertRaises(ValueError):
            _parse_github_url("https://gitlab.com/user/repo")


if __name__ == "__main__":
    unittest.main()
