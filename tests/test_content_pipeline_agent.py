"""
content_pipeline_agent (WriterAgent, EditorAgent, SeoAgent — plan/execute/reflect 패턴) 단위 테스트
"""
import json
import unittest
from unittest.mock import patch, MagicMock


class TestContentPipelineWriterAgent(unittest.TestCase):
    """services.agents.content_pipeline_agent.WriterAgent 테스트"""

    def _make_agent(self):
        from services.agents.content_pipeline_agent import WriterAgent
        return WriterAgent(model='gemini/test', style_id='blog_seo')

    @patch('services.agents.content_pipeline_agent.ai_service.create_content',
           return_value={"content": "# 초안 제목\n초안 본문", "title": "초안 제목"})
    def test_execute_returns_draft(self, mock_ai):
        agent = self._make_agent()
        plan = agent.plan("AI 기술", {"sources": [{"title": "A", "summary": "요약A"}]})
        result = agent.execute(plan)

        self.assertIn("draft", result)
        self.assertIn("초안", result["draft"])

    def test_plan_formats_sources(self):
        agent = self._make_agent()
        plan = agent.plan("주제", {
            "sources": [
                {"title": "소스1", "summary": "요약1"},
                {"title": "소스2", "summary": "요약2"},
            ]
        })
        self.assertIn("source_text", plan)
        self.assertIn("소스1", plan["source_text"])

    def test_reflect_short_draft(self):
        agent = self._make_agent()
        result = agent.reflect({"draft": "짧음"})
        self.assertFalse(result["done"])

    def test_reflect_long_draft(self):
        agent = self._make_agent()
        result = agent.reflect({"draft": "x" * 300})
        self.assertTrue(result["done"])

    def test_init(self):
        agent = self._make_agent()
        self.assertEqual(agent.name, "WriterAgent")
        self.assertEqual(agent.style_id, "blog_seo")
        self.assertEqual(agent.max_iterations, 2)


class TestContentPipelineEditorAgent(unittest.TestCase):
    """services.agents.content_pipeline_agent.EditorAgent 테스트"""

    def _make_agent(self):
        from services.agents.content_pipeline_agent import EditorAgent
        return EditorAgent(model='gemini/test')

    @patch('services.agents.content_pipeline_agent.ai_service.create_content',
           return_value={"content": "편집된 글"})
    def test_execute_returns_edited(self, mock_ai):
        agent = self._make_agent()
        plan = agent.plan("편집", {"draft": "원본 초안"})
        result = agent.execute(plan)

        self.assertIn("edited", result)
        self.assertEqual(result["edited"], "편집된 글")

    def test_execute_empty_draft(self):
        agent = self._make_agent()
        result = agent.execute({"draft": ""})
        self.assertEqual(result["edited"], "")
        self.assertEqual(result["changes"], [])

    def test_reflect_always_done(self):
        agent = self._make_agent()
        result = agent.reflect({})
        self.assertTrue(result["done"])

    def test_init(self):
        agent = self._make_agent()
        self.assertEqual(agent.name, "EditorAgent")
        self.assertEqual(agent.max_iterations, 1)


class TestContentPipelineSeoAgent(unittest.TestCase):
    """services.agents.content_pipeline_agent.SeoAgent 테스트"""

    def _make_agent(self):
        from services.agents.content_pipeline_agent import SeoAgent
        return SeoAgent(model='gemini/test')

    @patch('services.agents.content_pipeline_agent.ai_service.create_content',
           return_value={"content": '{"meta_description": "설명", "keywords": ["AI"]}'})
    def test_execute_returns_seo(self, mock_ai):
        agent = self._make_agent()
        plan = agent.plan("SEO", {"edited": "편집된 콘텐츠"})
        result = agent.execute(plan)

        self.assertIn("seo", result)
        self.assertEqual(result["seo"]["meta_description"], "설명")

    def test_execute_empty_content(self):
        agent = self._make_agent()
        result = agent.execute({"content": ""})
        self.assertEqual(result["seo"], {})

    @patch('services.agents.content_pipeline_agent.ai_service.create_content',
           return_value={"content": "유효하지 않은 JSON"})
    def test_execute_invalid_json(self, mock_ai):
        agent = self._make_agent()
        result = agent.execute({"content": "콘텐츠"})
        self.assertEqual(result["seo"], {})

    def test_plan_prefers_edited(self):
        agent = self._make_agent()
        plan = agent.plan("SEO", {"edited": "편집본", "draft": "초안"})
        self.assertEqual(plan["content"], "편집본")

    def test_plan_falls_back_to_draft(self):
        agent = self._make_agent()
        plan = agent.plan("SEO", {"draft": "초안"})
        self.assertEqual(plan["content"], "초안")

    def test_reflect_always_done(self):
        agent = self._make_agent()
        result = agent.reflect({})
        self.assertTrue(result["done"])

    def test_init(self):
        agent = self._make_agent()
        self.assertEqual(agent.name, "SeoAgent")
        self.assertEqual(agent.max_iterations, 1)


if __name__ == '__main__':
    unittest.main()
