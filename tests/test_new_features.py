"""
Feature Scout 기능 테스트
F1: DOCX 생성, F2: SEO 파싱, F3: URL 감지, F4: 새 스타일
"""
import unittest
from unittest.mock import patch


class TestDocxExport(unittest.TestCase):
    """F1: DOCX 내보내기 테스트"""

    @patch('services.supabase_service.is_supabase_enabled', return_value=False)
    def test_docx_endpoint_requires_content(self, mock_enabled):
        """콘텐츠 없이 DOCX 요청 시 400 반환"""
        from app import create_app
        app = create_app()
        with app.test_client() as client:
            resp = client.post('/api/export/docx',
                             json={'title': 'Test', 'content': ''},
                             content_type='application/json')
            self.assertEqual(resp.status_code, 400)

    @patch('services.supabase_service.is_supabase_enabled', return_value=False)
    def test_docx_endpoint_returns_docx(self, mock_enabled):
        """정상 요청 시 DOCX 파일 반환"""
        from app import create_app
        app = create_app()
        with app.test_client() as client:
            resp = client.post('/api/export/docx',
                             json={
                                 'title': '테스트 제목',
                                 'content': '## 소제목\n\n본문 텍스트입니다.\n\n- 목록 1\n- 목록 2'
                             },
                             content_type='application/json')
            self.assertEqual(resp.status_code, 200)
            self.assertIn('application/vnd.openxmlformats', resp.content_type)


class TestSeoExtraction(unittest.TestCase):
    """F2: SEO 메타데이터 추출 테스트"""

    def test_extract_meta_description(self):
        """메타 설명 파싱 테스트"""
        from services.core.ai_service import extract_seo_metadata

        content = '| **메타 설명** | AI 기술의 미래를 살펴봅니다 |\n'
        seo = extract_seo_metadata(content)
        self.assertIsNotNone(seo)
        self.assertEqual(seo['meta_description'], 'AI 기술의 미래를 살펴봅니다')

    def test_extract_keywords(self):
        """키워드 파싱 테스트"""
        from services.core.ai_service import extract_seo_metadata

        content = '| **타겟 키워드** | 메인: AI 기술, 연관: 머신러닝, 딥러닝 |\n'
        seo = extract_seo_metadata(content)
        self.assertIsNotNone(seo)
        self.assertIn('AI 기술', seo['keywords'])

    def test_extract_slug(self):
        """슬러그 파싱 테스트"""
        from services.core.ai_service import extract_seo_metadata

        content = '| **추천 URL** | /ai-technology-future |\n'
        seo = extract_seo_metadata(content)
        self.assertIsNotNone(seo)
        self.assertEqual(seo['slug'], 'ai-technology-future')

    def test_no_seo_data_returns_none(self):
        """SEO 데이터 없으면 None 반환"""
        from services.core.ai_service import extract_seo_metadata

        seo = extract_seo_metadata('일반 텍스트입니다.')
        self.assertIsNone(seo)

    def test_empty_content_returns_none(self):
        """빈 콘텐츠 None 반환"""
        from services.core.ai_service import extract_seo_metadata

        self.assertIsNone(extract_seo_metadata(''))
        self.assertIsNone(extract_seo_metadata(None))


class TestPlaylistUrlDetection(unittest.TestCase):
    """F3: 채널/재생목록 URL 감지 테스트"""

    def test_playlist_url_detected(self):
        """재생목록 URL 감지"""
        from services.core.content_service import is_playlist_url

        self.assertTrue(is_playlist_url('https://www.youtube.com/playlist?list=PLxxxxxx'))
        self.assertTrue(is_playlist_url('https://www.youtube.com/watch?v=abc&list=PLxxxxxx'))

    def test_channel_url_detected(self):
        """채널 URL 감지"""
        from services.core.content_service import is_channel_url

        self.assertTrue(is_channel_url('https://www.youtube.com/@channelname'))
        self.assertTrue(is_channel_url('https://www.youtube.com/channel/UCxxxxxxx'))
        self.assertTrue(is_channel_url('https://www.youtube.com/c/channelname'))

    def test_normal_video_url_not_playlist(self):
        """일반 영상 URL은 재생목록/채널이 아님"""
        from services.core.content_service import is_playlist_url, is_channel_url

        normal_url = 'https://www.youtube.com/watch?v=abc12345678'
        self.assertFalse(is_playlist_url(normal_url))
        self.assertFalse(is_channel_url(normal_url))


class TestNewStyles(unittest.TestCase):
    """F4: 새 스타일 프롬프트 테스트"""

    def test_new_styles_in_style_prompts(self):
        """3개 새 스타일이 STYLE_PROMPTS에 등록되어 있는지 확인"""
        from prompts.styles import STYLE_PROMPTS

        self.assertIn('sns_post', STYLE_PROMPTS)
        self.assertIn('newsletter', STYLE_PROMPTS)
        self.assertIn('show_notes', STYLE_PROMPTS)

    def test_new_styles_in_config(self):
        """3개 새 스타일이 config에 등록되어 있는지 확인"""
        from config import STYLE_OPTIONS, STYLE_TEMPERATURE

        style_ids = [s[0] for s in STYLE_OPTIONS]
        self.assertIn('sns_post', style_ids)
        self.assertIn('newsletter', style_ids)
        self.assertIn('show_notes', style_ids)

        self.assertIn('sns_post', STYLE_TEMPERATURE)
        self.assertIn('newsletter', STYLE_TEMPERATURE)
        self.assertIn('show_notes', STYLE_TEMPERATURE)

    def test_new_style_prompts_not_empty(self):
        """새 스타일 프롬프트가 비어있지 않은지 확인"""
        from prompts.styles import SNS_POST_PROMPT, NEWSLETTER_PROMPT, SHOW_NOTES_PROMPT

        self.assertGreater(len(SNS_POST_PROMPT), 100)
        self.assertGreater(len(NEWSLETTER_PROMPT), 100)
        self.assertGreater(len(SHOW_NOTES_PROMPT), 100)


if __name__ == '__main__':
    unittest.main()
