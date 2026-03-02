"""
웹 검색 보강 서비스 통합 테스트
Tavily API 호출, 컨텍스트 주입, 응답 포맷 검증
"""
import unittest
from unittest.mock import patch, MagicMock


class TestWebSearchService(unittest.TestCase):
    """웹 검색 서비스 단위 테스트"""

    def test_search_returns_empty_list_when_api_key_missing(self):
        """TAVILY_API_KEY 미설정 시 빈 리스트 반환"""
        with patch.dict('os.environ', {}, clear=True):
            import importlib
            import services.web_search_service as ws
            importlib.reload(ws)
            result = ws.search("테스트 쿼리")
            self.assertEqual(result, [])

    @patch('services.web_search_service.requests.post')
    def test_search_returns_results_on_success(self, mock_post):
        """API 성공 시 파싱된 결과 반환"""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            'results': [
                {
                    'title': '테스트 제목',
                    'url': 'https://example.com',
                    'content': '본문 내용',
                    'score': 0.9,
                }
            ]
        }
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        with patch.dict('os.environ', {'TAVILY_API_KEY': 'test-key'}):
            from services.web_search_service import search
            results = search("Python 튜토리얼")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], '테스트 제목')
        self.assertEqual(results[0]['url'], 'https://example.com')
        self.assertIn('content', results[0])
        self.assertIn('score', results[0])

    @patch('services.web_search_service.requests.post')
    def test_search_returns_empty_on_request_error(self, mock_post):
        """네트워크 오류 시 빈 리스트 반환 (graceful degradation)"""
        import requests as req_lib
        mock_post.side_effect = req_lib.exceptions.ConnectionError("연결 실패")

        with patch.dict('os.environ', {'TAVILY_API_KEY': 'test-key'}):
            from services.web_search_service import search
            result = search("쿼리")

        self.assertEqual(result, [])

    @patch('services.web_search_service.requests.post')
    def test_search_filters_results_without_url(self, mock_post):
        """URL이 없는 결과 항목 필터링"""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            'results': [
                {'title': '유효 결과', 'url': 'https://valid.com', 'content': '내용', 'score': 0.8},
                {'title': '무효 결과', 'url': '', 'content': '내용', 'score': 0.5},
                {'title': 'URL 없음', 'content': '내용', 'score': 0.3},
            ]
        }
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        with patch.dict('os.environ', {'TAVILY_API_KEY': 'test-key'}):
            from services.web_search_service import search
            results = search("쿼리")

        # URL이 있는 항목만 반환
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['url'], 'https://valid.com')

    @patch('services.web_search_service.search')
    def test_extract_grounding_context_enabled(self, mock_search):
        """검색 결과가 있을 때 context_text 생성 및 enabled=True 반환"""
        mock_search.return_value = [
            {'title': 'Python 기초', 'url': 'https://python.org', 'content': 'Python은 프로그래밍 언어입니다.', 'score': 0.9},
        ]

        with patch.dict('os.environ', {'TAVILY_API_KEY': 'test-key', 'WEB_SEARCH_MAX_RESULTS': '5'}):
            from services.web_search_service import extract_grounding_context
            result = extract_grounding_context("Python 프로그래밍 기초 강좌")

        self.assertTrue(result['enabled'])
        self.assertIsInstance(result['results'], list)
        self.assertEqual(len(result['results']), 1)
        self.assertIn('Python 기초', result['context_text'])
        self.assertIn('https://python.org', result['context_text'])

    @patch('services.web_search_service.search')
    def test_extract_grounding_context_disabled_when_no_results(self, mock_search):
        """검색 결과 없을 때 enabled=False 반환"""
        mock_search.return_value = []

        from services.web_search_service import extract_grounding_context
        result = extract_grounding_context("쿼리")

        self.assertFalse(result['enabled'])
        self.assertEqual(result['results'], [])
        self.assertEqual(result['context_text'], '')


class TestAiServiceWebSearchIntegration(unittest.TestCase):
    """ai_service에서 웹 검색 컨텍스트 주입 테스트"""

    def setUp(self):
        """테스트용 Flask 앱 컨텍스트 생성"""
        from app import create_app
        self.app = create_app({'TESTING': True})
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        """앱 컨텍스트 정리"""
        self.ctx.pop()

    def test_build_prompt_includes_web_context(self):
        """_build_prompt에 web_context 전달 시 프롬프트에 포함"""
        from services.ai_service import _build_prompt
        prompt = _build_prompt(
            content="자막 내용입니다.",
            style_prompt="블로그 스타일",
            modifiers=None,
            web_context="1. [테스트 기사](https://example.com)\n   테스트 내용입니다.",
        )

        self.assertIn('[웹 참고 자료]', prompt)
        self.assertIn('테스트 기사', prompt)

    def test_build_prompt_without_web_context(self):
        """web_context 미전달 시 [웹 참고 자료] 섹션 없음"""
        from services.ai_service import _build_prompt
        prompt = _build_prompt(
            content="자막 내용입니다.",
            style_prompt="블로그 스타일",
            modifiers=None,
        )

        self.assertNotIn('[웹 참고 자료]', prompt)


class TestConfigWebSearch(unittest.TestCase):
    """config.py 웹 검색 설정 로드 테스트"""

    def test_tavily_api_key_default_empty(self):
        """TAVILY_API_KEY 기본값 빈 문자열"""
        with patch.dict('os.environ', {}, clear=True):
            import importlib
            import config as cfg
            importlib.reload(cfg)
            self.assertEqual(cfg.TAVILY_API_KEY, '')

    def test_web_search_enabled_false_by_default(self):
        """WEB_SEARCH_ENABLED 기본값 False"""
        with patch.dict('os.environ', {}, clear=True):
            import importlib
            import config as cfg
            importlib.reload(cfg)
            self.assertFalse(cfg.WEB_SEARCH_ENABLED)

    def test_web_search_enabled_true_when_env_set(self):
        """WEB_SEARCH_ENABLED=true 환경변수 설정 시 True"""
        with patch.dict('os.environ', {'WEB_SEARCH_ENABLED': 'true'}):
            import importlib
            import config as cfg
            importlib.reload(cfg)
            self.assertTrue(cfg.WEB_SEARCH_ENABLED)

    def test_web_search_max_results_default(self):
        """WEB_SEARCH_MAX_RESULTS 기본값 5"""
        with patch.dict('os.environ', {}, clear=True):
            import importlib
            import config as cfg
            importlib.reload(cfg)
            self.assertEqual(cfg.WEB_SEARCH_MAX_RESULTS, 5)

    def test_web_search_max_results_custom(self):
        """WEB_SEARCH_MAX_RESULTS 커스텀 값 파싱"""
        with patch.dict('os.environ', {'WEB_SEARCH_MAX_RESULTS': '3'}):
            import importlib
            import config as cfg
            importlib.reload(cfg)
            self.assertEqual(cfg.WEB_SEARCH_MAX_RESULTS, 3)

    def test_web_search_in_all_list(self):
        """__all__ 리스트에 웹 검색 설정 포함"""
        from config import __all__ as all_exports
        self.assertIn('TAVILY_API_KEY', all_exports)
        self.assertIn('WEB_SEARCH_ENABLED', all_exports)
        self.assertIn('WEB_SEARCH_MAX_RESULTS', all_exports)


if __name__ == '__main__':
    unittest.main()
