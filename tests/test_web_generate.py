"""
웹 URL → /generate 엔드포인트 통합 테스트

검증 항목:
1. 웹 URL로 /generate 호출 시 성공 응답 반환
2. web_scraper_service 모킹으로 텍스트 추출 시뮬레이션
3. 잘못된 URL(본문 추출 실패) 시 400 에러 반환
4. source_type='webpage' 명시 시 웹페이지로 처리
5. 자동 감지로 웹페이지 URL 처리
"""
import unittest
from unittest.mock import patch, MagicMock


def _make_fake_result():
    return {
        'title': '웹페이지 콘텐츠 제목',
        'content': '생성된 본문 내용입니다.',
        'html': '<p>생성된 본문 내용입니다.</p>',
        'usage': {'prompt_tokens': 100, 'completion_tokens': 200, 'total_tokens': 300},
    }


class TestWebGenerate(unittest.TestCase):
    def setUp(self):
        from app import create_app
        self.app = create_app({'TESTING': True})
        self.client = self.app.test_client()

    def _post_generate(self, payload):
        return self.client.post('/generate', json=payload)

    # ── 1. 웹 URL 성공 ────────────────────────────────────────

    @patch('services.supabase_service.is_supabase_enabled', return_value=False)
    def test_generate_webpage_success(self, _mock_supabase):
        """일반 웹 URL로 /generate 호출 시 200 + 콘텐츠 반환"""
        fake_scraped = {
            'title': '테스트 블로그 포스트',
            'content': '충분히 긴 웹페이지 본문입니다. ' * 10,
            'url': 'https://example.com/blog/post',
            'source_type': 'webpage',
        }
        fake_result = _make_fake_result()

        def fake_create_content(content, model, style_prompt=None, return_prompt=False, **kwargs):
            if return_prompt:
                return fake_result, 'PROMPT_TEXT'
            return fake_result

        with patch('services.multi_source_collector._collect_webpage', return_value=fake_scraped), \
             patch('routes.blog_routes.ai_service.create_content', side_effect=fake_create_content), \
             patch('routes.blog_routes.content_service.truncate_text', side_effect=lambda t, _: t):

            res = self._post_generate({
                'url': 'https://example.com/blog/post',
                'model': 'zhipuai/GLM-4.5-Air',
                'style': 'blog_seo',
            })

        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('content', data)
        self.assertIn('html', data)
        self.assertEqual(data.get('source_type'), 'webpage')

    # ── 2. source_type 명시 ────────────────────────────────────

    @patch('services.supabase_service.is_supabase_enabled', return_value=False)
    def test_generate_with_explicit_source_type_webpage(self, _mock_supabase):
        """source_type='webpage' 명시 시 정상 처리"""
        fake_scraped = {
            'title': '명시 소스 타입 테스트',
            'content': '본문 내용입니다. ' * 10,
            'url': 'https://tech.example.com/article',
            'source_type': 'webpage',
        }
        fake_result = _make_fake_result()

        def fake_create_content(content, model, style_prompt=None, return_prompt=False, **kwargs):
            if return_prompt:
                return fake_result, 'PROMPT'
            return fake_result

        with patch('services.multi_source_collector._collect_webpage', return_value=fake_scraped), \
             patch('routes.blog_routes.ai_service.create_content', side_effect=fake_create_content), \
             patch('routes.blog_routes.content_service.truncate_text', side_effect=lambda t, _: t):

            res = self._post_generate({
                'url': 'https://tech.example.com/article',
                'model': 'zhipuai/GLM-4.5-Air',
                'style': 'summary',
                'source_type': 'webpage',
            })

        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('content', data)
        self.assertEqual(data.get('source_type'), 'webpage')

    # ── 3. 본문 추출 실패 → 400 ──────────────────────────────

    @patch('services.supabase_service.is_supabase_enabled', return_value=False)
    def test_generate_webpage_scraping_failure_returns_400(self, _mock_supabase):
        """웹 스크래핑 실패 시 400 에러 반환"""
        with patch('services.multi_source_collector._collect_webpage',
                   side_effect=ValueError("웹페이지에서 본문을 추출할 수 없습니다: https://empty.example.com")):

            res = self._post_generate({
                'url': 'https://empty.example.com',
                'model': 'zhipuai/GLM-4.5-Air',
                'style': 'blog_seo',
            })

        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn('error', data)

    # ── 4. 빈 URL → 400 ──────────────────────────────────────

    @patch('services.supabase_service.is_supabase_enabled', return_value=False)
    def test_generate_empty_url_returns_400(self, _mock_supabase):
        """URL 없이 호출 시 400 에러 반환"""
        res = self._post_generate({
            'url': '',
            'model': 'zhipuai/GLM-4.5-Air',
            'style': 'blog_seo',
        })

        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn('error', data)

    # ── 5. 자동 감지: 비유튜브 URL ────────────────────────────

    @patch('services.supabase_service.is_supabase_enabled', return_value=False)
    def test_generate_auto_detect_non_youtube_as_webpage(self, _mock_supabase):
        """비유튜브 URL은 자동으로 웹페이지로 처리됨"""
        fake_scraped = {
            'title': '뉴스 기사 제목',
            'content': '뉴스 기사 본문입니다. ' * 10,
            'url': 'https://news.example.com/article/12345',
            'source_type': 'webpage',
        }
        fake_result = _make_fake_result()

        def fake_create_content(content, model, style_prompt=None, return_prompt=False, **kwargs):
            if return_prompt:
                return fake_result, 'PROMPT'
            return fake_result

        with patch('services.multi_source_collector._collect_webpage', return_value=fake_scraped) as mock_scrape, \
             patch('routes.blog_routes.ai_service.create_content', side_effect=fake_create_content), \
             patch('routes.blog_routes.content_service.truncate_text', side_effect=lambda t, _: t):

            res = self._post_generate({
                'url': 'https://news.example.com/article/12345',
                'model': 'zhipuai/GLM-4.5-Air',
                'style': 'summary',
            })

        self.assertEqual(res.status_code, 200)
        # _collect_webpage가 호출됐는지 확인 (웹페이지로 자동 감지)
        mock_scrape.assert_called_once_with('https://news.example.com/article/12345')

    # ── 6. source_title이 응답에 포함됨 ──────────────────────

    @patch('services.supabase_service.is_supabase_enabled', return_value=False)
    def test_generate_webpage_includes_source_title(self, _mock_supabase):
        """응답에 스크래핑된 페이지 제목(source_title)이 포함됨"""
        fake_scraped = {
            'title': '원본 페이지 제목',
            'content': '원본 본문 내용입니다. ' * 10,
            'url': 'https://example.com/page',
            'source_type': 'webpage',
        }
        fake_result = _make_fake_result()

        def fake_create_content(content, model, style_prompt=None, return_prompt=False, **kwargs):
            if return_prompt:
                return fake_result, 'PROMPT'
            return fake_result

        with patch('services.multi_source_collector._collect_webpage', return_value=fake_scraped), \
             patch('routes.blog_routes.ai_service.create_content', side_effect=fake_create_content), \
             patch('routes.blog_routes.content_service.truncate_text', side_effect=lambda t, _: t):

            res = self._post_generate({
                'url': 'https://example.com/page',
                'model': 'zhipuai/GLM-4.5-Air',
                'style': 'blog_seo',
            })

        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get('source_title'), '원본 페이지 제목')


    # ── 7. Wikipedia URL → 제목 접미사 제거 ────────────────────

    @patch('services.supabase_service.is_supabase_enabled', return_value=False)
    def test_generate_wikipedia_url_success(self, _mock_supabase):
        """Wikipedia URL로 /generate 호출 시 200 + 콘텐츠 반환"""
        fake_scraped = {
            'title': '인공지능',  # 접미사 제거된 제목
            'content': '인공지능(AI)은 인간의 학습, 추론 능력을 모사하는 컴퓨터 시스템입니다. ' * 10,
            'url': 'https://ko.wikipedia.org/wiki/인공지능',
            'source_type': 'webpage',
        }
        fake_result = _make_fake_result()

        def fake_create_content(content, model, style_prompt=None, return_prompt=False, **kwargs):
            if return_prompt:
                return fake_result, 'PROMPT'
            return fake_result

        with patch('services.multi_source_collector._collect_webpage', return_value=fake_scraped), \
             patch('routes.blog_routes.ai_service.create_content', side_effect=fake_create_content), \
             patch('routes.blog_routes.content_service.truncate_text', side_effect=lambda t, _: t):

            res = self._post_generate({
                'url': 'https://ko.wikipedia.org/wiki/인공지능',
                'model': 'zhipuai/GLM-4.5-Air',
                'style': 'summary',
            })

        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('content', data)
        self.assertEqual(data.get('source_type'), 'webpage')


class TestWikipediaTitleCleaning(unittest.TestCase):
    """web_scraper_service의 Wikipedia 제목 정리 단위 테스트"""

    def test_clean_korean_suffix(self):
        from services.data.web_scraper_service import _clean_wikipedia_title
        self.assertEqual(
            _clean_wikipedia_title('인공지능 - 위키백과, 우리 모두의 백과사전'),
            '인공지능',
        )

    def test_clean_english_suffix(self):
        from services.data.web_scraper_service import _clean_wikipedia_title
        self.assertEqual(
            _clean_wikipedia_title('Artificial intelligence - Wikipedia'),
            'Artificial intelligence',
        )

    def test_clean_japanese_suffix(self):
        from services.data.web_scraper_service import _clean_wikipedia_title
        self.assertEqual(
            _clean_wikipedia_title('人工知能 - ウィキペディア'),
            '人工知能',
        )

    def test_no_suffix_unchanged(self):
        from services.data.web_scraper_service import _clean_wikipedia_title
        self.assertEqual(
            _clean_wikipedia_title('인공지능'),
            '인공지능',
        )


if __name__ == '__main__':
    unittest.main()
