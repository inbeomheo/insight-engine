"""
멀티에이전트 파이프라인 통합 테스트

ResearchAgent, WriterAgent, EditorAgent, SEOAgent 및
Orchestrator의 동작을 검증합니다.
"""
import unittest
from unittest.mock import patch, MagicMock


# ──────────────────────────────────────────────────────────────────
# BaseAgent import 테스트
# ──────────────────────────────────────────────────────────────────

class TestBaseAgentImport(unittest.TestCase):
    """BaseAgent 클래스가 정상 import되는지 확인합니다."""

    def test_import_base_agent(self):
        from services.agents.base_agent import BaseAgent
        self.assertTrue(hasattr(BaseAgent, 'execute'))
        self.assertTrue(hasattr(BaseAgent, 'name'))
        self.assertTrue(hasattr(BaseAgent, 'role'))

    def test_import_all_agents(self):
        from services.agents import (
            BaseAgent, ResearchAgent, WriterAgent,
            EditorAgent, SEOAgent, Orchestrator
        )
        # 각 클래스가 BaseAgent를 상속하는지 확인
        self.assertTrue(issubclass(ResearchAgent, BaseAgent))
        self.assertTrue(issubclass(WriterAgent, BaseAgent))
        self.assertTrue(issubclass(EditorAgent, BaseAgent))
        self.assertTrue(issubclass(SEOAgent, BaseAgent))


# ──────────────────────────────────────────────────────────────────
# ResearchAgent 단위 테스트
# ──────────────────────────────────────────────────────────────────

class TestResearchAgent(unittest.TestCase):
    """ResearchAgent 동작을 검증합니다."""

    def setUp(self):
        from services.agents.research_agent import ResearchAgent
        self.agent = ResearchAgent()

    def test_name_and_role(self):
        self.assertEqual(self.agent.name, 'research')
        self.assertIsInstance(self.agent.role, str)
        self.assertTrue(len(self.agent.role) > 0)

    def test_empty_transcript_returns_empty(self):
        """자막이 없을 때 빈 결과 반환."""
        result = self.agent.execute({'transcript': '', 'style': 'blog_seo'})
        self.assertEqual(result['agent'], 'research')
        self.assertEqual(result['main_topic'], '')
        self.assertEqual(result['key_points'], [])

    @patch('services.agents.base_agent.BaseAgent._call_ai')
    @patch('services.web_search_service.search', return_value=[])
    def test_execute_with_transcript(self, mock_web_search, mock_call_ai):
        """자막이 있을 때 AI 호출 및 결과 파싱 검증."""
        mock_call_ai.return_value = '''{
            "main_topic": "파이썬 기초",
            "key_points": ["변수", "함수", "클래스"],
            "target_audience": "초보자",
            "tone": "교육적",
            "search_query": "Python basics tutorial",
            "summary": "파이썬 기초를 배우는 강의"
        }'''

        result = self.agent.execute({
            'transcript': '파이썬은 프로그래밍 언어입니다. ' * 50,
            'style': 'blog_seo'
        })

        self.assertEqual(result['agent'], 'research')
        self.assertEqual(result['main_topic'], '파이썬 기초')
        self.assertIn('변수', result['key_points'])
        self.assertEqual(result['tone'], '교육적')


# ──────────────────────────────────────────────────────────────────
# WriterAgent 단위 테스트
# ──────────────────────────────────────────────────────────────────

class TestWriterAgent(unittest.TestCase):
    """WriterAgent 동작을 검증합니다."""

    def setUp(self):
        from services.agents.writer_agent import WriterAgent
        self.agent = WriterAgent()

    def test_name_and_role(self):
        self.assertEqual(self.agent.name, 'writer')

    @patch('services.agents.base_agent.BaseAgent._call_ai')
    def test_execute_returns_draft(self, mock_call_ai):
        """콘텐츠 초안이 정상 반환되는지 확인."""
        mock_call_ai.return_value = '# 파이썬 기초 가이드\n\n파이썬은 강력한 언어입니다.'

        result = self.agent.execute({
            'transcript': '파이썬을 배워봅시다.',
            'style': 'blog_seo',
            'style_prompt': '블로그 형식으로 작성하세요.',
            'main_topic': '파이썬 기초',
            'key_points': ['변수', '함수'],
            'target_audience': '초보자',
            'tone': '교육적',
            'web_context': '',
            'modifiers': {'length': 'medium'},
        })

        self.assertEqual(result['agent'], 'writer')
        self.assertIn('파이썬', result['draft'])
        self.assertEqual(result['title'], '파이썬 기초 가이드')

    @patch('services.agents.base_agent.BaseAgent._call_ai')
    def test_extract_title_fallback(self, mock_call_ai):
        """H1 제목이 없을 때 기본 제목 반환."""
        mock_call_ai.return_value = '제목 없는 본문 내용입니다.'

        result = self.agent.execute({
            'transcript': '내용',
            'style': 'blog_seo',
            'style_prompt': '',
            'main_topic': '',
            'key_points': [],
            'target_audience': '',
            'tone': '',
            'web_context': '',
            'modifiers': {},
        })

        self.assertEqual(result['title'], 'AI 생성 콘텐츠')


# ──────────────────────────────────────────────────────────────────
# EditorAgent 단위 테스트
# ──────────────────────────────────────────────────────────────────

class TestEditorAgent(unittest.TestCase):
    """EditorAgent 동작을 검증합니다."""

    def setUp(self):
        from services.agents.editor_agent import EditorAgent
        self.agent = EditorAgent()

    def test_name_and_role(self):
        self.assertEqual(self.agent.name, 'editor')

    def test_empty_draft_returns_empty(self):
        result = self.agent.execute({'draft': '', 'summary': ''})
        self.assertEqual(result['agent'], 'editor')
        self.assertEqual(result['edited_content'], '')
        self.assertIn('grade', result['quality'])

    @patch('services.agents.base_agent.BaseAgent._call_ai')
    def test_execute_edits_draft(self, mock_call_ai):
        """교정 결과가 반환되는지 확인."""
        mock_call_ai.return_value = '# 교정된 제목\n\n교정된 내용입니다.'

        result = self.agent.execute({
            'draft': '# 원본 제목\n\n원본 내용.',
            'summary': '요약',
        })

        self.assertEqual(result['agent'], 'editor')
        self.assertIn('교정', result['edited_content'])
        self.assertEqual(result['title'], '교정된 제목')

    @patch('services.agents.base_agent.BaseAgent._call_ai')
    def test_quality_evaluation(self, mock_call_ai):
        """품질 평가가 수행되는지 확인 (2번 AI 호출)."""
        # 첫 번째 호출: 교정, 두 번째 호출: 품질 평가
        mock_call_ai.side_effect = [
            '# 교정 결과\n\n내용.',
            '{"grade": "A", "readability": 9, "accuracy": 8, "issues": [], "summary": "좋음"}',
        ]

        result = self.agent.execute({
            'draft': '# 테스트\n\n내용.',
            'summary': '요약',
        })

        self.assertIn('grade', result['quality'])


# ──────────────────────────────────────────────────────────────────
# SEOAgent 단위 테스트
# ──────────────────────────────────────────────────────────────────

class TestSEOAgent(unittest.TestCase):
    """SEOAgent 동작을 검증합니다."""

    def setUp(self):
        from services.agents.seo_agent import SEOAgent
        self.agent = SEOAgent()

    def test_name_and_role(self):
        self.assertEqual(self.agent.name, 'seo')

    def test_empty_content_returns_empty(self):
        result = self.agent.execute({'edited_content': '', 'title': ''})
        self.assertEqual(result['agent'], 'seo')
        self.assertEqual(result['keywords'], [])

    @patch('services.agents.base_agent.BaseAgent._call_ai')
    def test_execute_generates_seo(self, mock_call_ai):
        """SEO 메타데이터가 생성되는지 확인."""
        mock_call_ai.return_value = '''{
            "meta_title": "파이썬 기초 완전 가이드",
            "meta_description": "파이썬 초보자를 위한 기초 가이드입니다.",
            "keywords": ["파이썬", "Python", "프로그래밍"],
            "faq": [{"question": "파이썬이란?", "answer": "범용 프로그래밍 언어입니다."}],
            "og_title": "파이썬 기초",
            "og_description": "파이썬을 배워보세요."
        }'''

        result = self.agent.execute({
            'edited_content': '# 파이썬 기초\n\n내용.',
            'title': '파이썬 기초',
            'main_topic': '파이썬',
            'summary': '파이썬 강의',
            'url': '',
        })

        self.assertEqual(result['agent'], 'seo')
        self.assertIn('파이썬', result['keywords'])
        self.assertEqual(len(result['faq']), 1)
        self.assertIn('meta_title', result)


# ──────────────────────────────────────────────────────────────────
# Orchestrator 통합 테스트
# ──────────────────────────────────────────────────────────────────

class TestOrchestrator(unittest.TestCase):
    """Orchestrator 전체 파이프라인을 검증합니다."""

    def setUp(self):
        from services.agents.orchestrator import Orchestrator
        self.orchestrator = Orchestrator(model='gemini/gemini-3-flash-preview')

    @patch('services.agents.seo_agent.SEOAgent.execute')
    @patch('services.agents.editor_agent.EditorAgent.execute')
    @patch('services.agents.writer_agent.WriterAgent.execute')
    @patch('services.agents.research_agent.ResearchAgent.execute')
    def test_pipeline_runs_all_agents(
        self, mock_research, mock_writer, mock_editor, mock_seo
    ):
        """파이프라인이 4단계 에이전트를 모두 실행하는지 확인."""
        mock_research.return_value = {
            'agent': 'research', 'main_topic': '파이썬', 'key_points': ['변수'],
            'target_audience': '초보자', 'tone': '교육적',
            'summary': '요약', 'web_results': [], 'web_context': '',
        }
        mock_writer.return_value = {
            'agent': 'writer', 'draft': '# 제목\n\n내용.', 'title': '제목',
        }
        mock_editor.return_value = {
            'agent': 'editor', 'edited_content': '# 제목\n\n교정된 내용.',
            'title': '제목', 'quality': {'grade': 'A'},
        }
        mock_seo.return_value = {
            'agent': 'seo', 'meta_title': '제목', 'meta_description': '설명',
            'keywords': ['파이썬'], 'faq': [], 'og_title': '제목',
            'og_description': '설명', 'json_ld': {},
        }

        result = self.orchestrator.run(
            transcript='파이썬을 배워봅시다.' * 20,
            style='blog_seo',
            style_prompt='블로그 형식으로 작성하세요.',
        )

        # 모든 에이전트가 실행됐는지 확인
        mock_research.assert_called_once()
        mock_writer.assert_called_once()
        mock_editor.assert_called_once()
        mock_seo.assert_called_once()

        # 결과 구조 검증
        self.assertIn('title', result)
        self.assertIn('content', result)
        self.assertIn('html', result)
        self.assertIn('seo', result)
        self.assertIn('quality', result)
        self.assertIn('elapsed_time', result)
        self.assertGreater(result['elapsed_time'], 0)

    @patch('services.agents.seo_agent.SEOAgent.execute')
    @patch('services.agents.editor_agent.EditorAgent.execute')
    @patch('services.agents.writer_agent.WriterAgent.execute')
    @patch('services.agents.research_agent.ResearchAgent.execute')
    def test_pipeline_continues_on_research_failure(
        self, mock_research, mock_writer, mock_editor, mock_seo
    ):
        """Research 실패 시 나머지 파이프라인이 계속 실행되는지 확인."""
        mock_research.side_effect = Exception('Research 실패')
        mock_writer.return_value = {
            'agent': 'writer', 'draft': '# 제목\n\n내용.', 'title': '제목',
        }
        mock_editor.return_value = {
            'agent': 'editor', 'edited_content': '# 제목\n\n내용.',
            'title': '제목', 'quality': {'grade': 'B'},
        }
        mock_seo.return_value = {
            'agent': 'seo', 'meta_title': '', 'meta_description': '',
            'keywords': [], 'faq': [], 'og_title': '', 'og_description': '',
            'json_ld': {},
        }

        # Research 실패해도 RuntimeError 발생하지 않아야 함
        result = self.orchestrator.run(
            transcript='내용',
            style='blog_seo',
            style_prompt='',
        )

        self.assertIn('content', result)
        mock_writer.assert_called_once()

    @patch('services.agents.seo_agent.SEOAgent.execute')
    @patch('services.agents.editor_agent.EditorAgent.execute')
    @patch('services.agents.writer_agent.WriterAgent.execute')
    @patch('services.agents.research_agent.ResearchAgent.execute')
    def test_pipeline_raises_on_writer_failure(
        self, mock_research, mock_writer, mock_editor, mock_seo
    ):
        """Writer 실패 시 RuntimeError가 발생하는지 확인."""
        mock_research.return_value = {
            'agent': 'research', 'main_topic': '', 'key_points': [],
            'target_audience': '', 'tone': '', 'summary': '',
            'web_results': [], 'web_context': '',
        }
        mock_writer.side_effect = RuntimeError('Writer 실패')

        with self.assertRaises(RuntimeError):
            self.orchestrator.run(
                transcript='내용',
                style='blog_seo',
                style_prompt='',
            )


# ──────────────────────────────────────────────────────────────────
# /generate 엔드포인트 + agent_mode 통합 테스트
# ──────────────────────────────────────────────────────────────────

class TestGenerateEndpointAgentMode(unittest.TestCase):
    """agent_mode=true 요청이 Orchestrator를 실행하는지 확인합니다."""

    def setUp(self):
        from app import create_app
        self.app = create_app({'TESTING': True})
        self.client = self.app.test_client()

    @patch('services.supabase_service.is_supabase_enabled', return_value=False)
    @patch('routes.blog_routes.content_service.is_youtube_url', return_value=True)
    @patch('routes.blog_routes.content_service.get_video_id', return_value='agt_test_1')
    @patch('routes.blog_routes.content_service.get_content_title', return_value='테스트 영상')
    @patch('routes.generation_helpers.content_service.get_transcript')
    @patch('routes.generation_helpers.content_service.get_top_comments', return_value=[])
    @patch('routes.blog_routes.content_service.truncate_text', side_effect=lambda t, _: t)
    @patch('routes.generation_helpers.content_service.truncate_text', side_effect=lambda t, _: t)
    @patch('services.agents.orchestrator.Orchestrator.run')
    def test_agent_mode_calls_orchestrator(
        self, mock_orch_run, mock_gen_truncate, mock_truncate, mock_comments,
        mock_transcript, mock_title, mock_video_id, mock_is_yt, mock_supabase
    ):
        """agent_mode=true 시 Orchestrator.run()이 호출되는지 확인."""
        mock_transcript.return_value = {'text': '테스트 자막 내용 ' * 30, 'source': 'api'}
        mock_orch_run.return_value = {
            'title': '에이전트 생성 제목',
            'content': '에이전트 생성 내용',
            'html': '<p>에이전트 생성 내용</p>',
            'usage': {'total_tokens': 1000, 'prompt_tokens': 800, 'completion_tokens': 200},
            'quality': {'grade': 'A'},
            'seo': {'meta_title': '에이전트 제목'},
            'elapsed_time': 5.5,
        }

        res = self.client.post('/generate', json={
            'url': 'https://www.youtube.com/watch?v=agt_test_1',
            'model': 'gemini/gemini-3-flash-preview',
            'style': 'blog_seo',
            'agent_mode': True,
            'force': True,  # 캐시 무시
        })

        self.assertEqual(res.status_code, 200)
        mock_orch_run.assert_called_once()
        data = res.get_json()
        self.assertIn('content', data)

    @patch('services.supabase_service.is_supabase_enabled', return_value=False)
    @patch('routes.blog_routes.content_service.is_youtube_url', return_value=True)
    @patch('routes.blog_routes.content_service.get_video_id', return_value='agt_test_2')
    @patch('routes.blog_routes.content_service.get_content_title', return_value='테스트 영상')
    @patch('routes.generation_helpers.content_service.get_transcript')
    @patch('routes.generation_helpers.content_service.get_top_comments', return_value=[])
    @patch('routes.blog_routes.content_service.truncate_text', side_effect=lambda t, _: t)
    @patch('routes.generation_helpers.content_service.truncate_text', side_effect=lambda t, _: t)
    @patch('services.agents.orchestrator.Orchestrator.run')
    @patch('routes.generation_helpers.ai_service.create_content')
    def test_agent_mode_fallback_on_error(
        self, mock_create, mock_orch_run, mock_gen_truncate, mock_truncate,
        mock_comments, mock_transcript, mock_title, mock_video_id, mock_is_yt, mock_supabase
    ):
        """Orchestrator 실패 시 일반 모드로 폴백하는지 확인."""
        mock_transcript.return_value = {'text': '테스트 자막 내용 ' * 30, 'source': 'api'}
        mock_orch_run.side_effect = RuntimeError('Orchestrator 오류')

        fake_result = {'title': '폴백 제목', 'content': '폴백 내용', 'html': '<p>폴백</p>',
                       'usage': {'total_tokens': 100, 'prompt_tokens': 80, 'completion_tokens': 20}}
        mock_create.return_value = (fake_result, 'PROMPT')

        res = self.client.post('/generate', json={
            'url': 'https://www.youtube.com/watch?v=agt_test_2',
            'model': 'gemini/gemini-3-flash-preview',
            'style': 'blog_seo',
            'agent_mode': True,
            'force': True,  # 캐시 무시
        })

        self.assertEqual(res.status_code, 200)
        # 폴백으로 ai_service.create_content가 호출됐는지 확인
        mock_create.assert_called()
        data = res.get_json()
        self.assertIn('content', data)


if __name__ == '__main__':
    unittest.main()
