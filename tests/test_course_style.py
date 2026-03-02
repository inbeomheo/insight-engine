"""
course 스타일 통합 테스트
P2-3F: 프롬프트 등록, 설정, 생성 엔드포인트 검증
"""
import unittest
from unittest.mock import patch


class TestCourseStylePrompt(unittest.TestCase):
    """P2-3A/3B: course 프롬프트 파일 및 등록 검증"""

    def test_course_prompt_importable(self):
        """course.py에서 COURSE_PROMPT가 임포트 가능해야 한다"""
        from prompts.styles.course import COURSE_PROMPT
        self.assertIsInstance(COURSE_PROMPT, str)
        self.assertGreater(len(COURSE_PROMPT), 100)

    def test_course_prompt_in_style_prompts(self):
        """STYLE_PROMPTS 딕셔너리에 'course' 키가 존재해야 한다"""
        from prompts.styles import STYLE_PROMPTS
        self.assertIn('course', STYLE_PROMPTS)

    def test_course_prompt_content(self):
        """course 프롬프트에 핵심 섹션 키워드가 포함되어야 한다"""
        from prompts.styles.course import COURSE_PROMPT
        required_keywords = ['학습 목표', '핵심 개념', '실습 과제', '복습 퀴즈']
        for kw in required_keywords:
            self.assertIn(kw, COURSE_PROMPT, f"'{kw}'가 프롬프트에 없습니다")

    def test_get_style_prompt_returns_course(self):
        """get_style_prompt('course')가 COURSE_PROMPT를 반환해야 한다"""
        from prompts.styles import get_style_prompt, STYLE_PROMPTS
        result = get_style_prompt('course')
        self.assertEqual(result, STYLE_PROMPTS['course'])


class TestCourseStyleConfig(unittest.TestCase):
    """P2-3C/3D: config.py 설정 검증"""

    def test_course_in_style_options(self):
        """STYLE_OPTIONS에 'course' 항목이 포함되어야 한다"""
        from config import STYLE_OPTIONS
        style_ids = [s[0] for s in STYLE_OPTIONS]
        self.assertIn('course', style_ids)

    def test_course_label(self):
        """course 스타일의 레이블이 'AI 코스'를 포함해야 한다"""
        from config import STYLE_OPTIONS
        course_entry = next((s for s in STYLE_OPTIONS if s[0] == 'course'), None)
        self.assertIsNotNone(course_entry, "'course' 항목이 STYLE_OPTIONS에 없습니다")
        self.assertIn('코스', course_entry[1])

    def test_course_temperature(self):
        """STYLE_TEMPERATURE에 'course'가 정밀형(0.5)으로 설정되어야 한다"""
        from config import STYLE_TEMPERATURE
        self.assertIn('course', STYLE_TEMPERATURE)
        self.assertEqual(STYLE_TEMPERATURE['course'], 0.5)


class TestCourseStyleGeneration(unittest.TestCase):
    """P2-3F: /generate 엔드포인트에서 course 스타일 처리 검증"""

    def setUp(self):
        from app import create_app
        self.app = create_app({'TESTING': True})
        self.client = self.app.test_client()

    def test_generate_with_course_style(self):
        """course 스타일로 /generate 호출 시 200 응답과 content를 반환해야 한다"""
        fake_result = {
            'title': '파이썬 입문 — 완전 정복 코스',
            'content': '## 학습 목표\n- ✅ 기초 문법 이해',
            'html': '<h2>학습 목표</h2>',
            'usage': {'prompt_tokens': 10, 'completion_tokens': 50, 'total_tokens': 60},
        }
        fake_transcript = {'text': '파이썬 기초를 배워봅시다', 'source': 'api'}

        def fake_create_content(content, model, style_prompt=None, return_prompt=False, modifiers=None,
                                style_id=None, user_id=None, segments=None, web_search=False, **kwargs):
            if return_prompt:
                return fake_result, 'COURSE_PROMPT_TEXT'
            return fake_result

        with patch('services.supabase_service.is_supabase_enabled', return_value=False), \
             patch('routes.blog_routes.content_service.is_youtube_url', return_value=True), \
             patch('routes.blog_routes.content_service.get_video_id', return_value='test_course'), \
             patch('routes.blog_routes.content_service.get_content_title', return_value='파이썬 입문 강의'), \
             patch('routes.blog_routes.content_service.get_transcript', return_value=fake_transcript), \
             patch('routes.blog_routes.content_service.get_top_comments', return_value=[]), \
             patch('routes.blog_routes.content_service.truncate_text', side_effect=lambda t, _max: t), \
             patch('routes.blog_routes.ai_service.create_content', side_effect=fake_create_content):
            res = self.client.post('/generate', json={
                'url': 'https://www.youtube.com/watch?v=test_course',
                'model': 'gemini/gemini-2.5-flash',
                'style': 'course',
                'apiKey': 'test-key',
            })
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertIn('content', data)
            self.assertIn('html', data)


if __name__ == '__main__':
    unittest.main()
