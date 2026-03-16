"""
SEOAgent 단위 테스트
"""
import json
import unittest
from unittest.mock import patch, MagicMock


class TestSEOAgent(unittest.TestCase):
    """services.agents.seo_agent.SEOAgent 테스트"""

    def _mock_completion(self, content: str):
        mock = MagicMock()
        mock.choices[0].message.content = content
        return mock

    def _make_agent(self):
        from services.agents.seo_agent import SEOAgent
        return SEOAgent(model='gemini/gemini-3-flash-preview')

    # --- 초기화 ---

    @patch('services.agents.base_agent.BaseAgent._get_default_model',
           return_value='gemini/gemini-3-flash-preview')
    def test_init_properties(self, _):
        agent = self._make_agent()
        self.assertEqual(agent.name, 'seo')
        self.assertEqual(agent.role, 'SEO 최적화 및 메타데이터 생성')

    # --- execute: 정상 ---

    @patch('services.agents.base_agent.BaseAgent._get_default_model',
           return_value='gemini/gemini-3-flash-preview')
    @patch('litellm.completion')
    def test_execute_returns_seo_metadata(self, mock_llm, _):
        seo_json = json.dumps({
            "meta_title": "AI 활용 가이드",
            "meta_description": "AI를 활용하는 실전 가이드입니다.",
            "keywords": ["AI", "활용", "가이드"],
            "faq": [{"question": "AI란?", "answer": "인공지능입니다."}],
            "og_title": "AI 활용법",
            "og_description": "AI 실전 가이드",
        })
        mock_llm.return_value = self._mock_completion(seo_json)

        agent = self._make_agent()
        result = agent.execute({
            'edited_content': '# AI 활용 가이드\n본문 내용입니다.',
            'title': 'AI 활용 가이드',
            'main_topic': 'AI 활용',
            'summary': 'AI 활용 요약',
        })

        self.assertEqual(result['agent'], 'seo')
        self.assertEqual(result['meta_title'], 'AI 활용 가이드')
        self.assertEqual(len(result['keywords']), 3)
        self.assertEqual(len(result['faq']), 1)

    # --- execute: 빈 콘텐츠 ---

    @patch('services.agents.base_agent.BaseAgent._get_default_model',
           return_value='gemini/gemini-3-flash-preview')
    def test_execute_empty_content_returns_empty(self, _):
        agent = self._make_agent()
        result = agent.execute({'edited_content': ''})

        self.assertEqual(result['agent'], 'seo')
        self.assertEqual(result['meta_title'], '')
        self.assertEqual(result['keywords'], [])
        self.assertEqual(result['json_ld'], {})

    # --- execute: AI 실패 시 fallback ---

    @patch('services.agents.base_agent.BaseAgent._get_default_model',
           return_value='gemini/gemini-3-flash-preview')
    @patch('litellm.completion', side_effect=Exception('API error'))
    def test_execute_ai_failure_uses_fallback(self, mock_llm, _):
        agent = self._make_agent()
        result = agent.execute({
            'edited_content': '콘텐츠 내용',
            'title': '테스트 제목',
            'summary': '테스트 요약',
        })

        self.assertEqual(result['agent'], 'seo')
        self.assertEqual(result['meta_title'], '테스트 제목')

    # --- _parse_json ---

    @patch('services.agents.base_agent.BaseAgent._get_default_model',
           return_value='gemini/gemini-3-flash-preview')
    def test_parse_json_with_code_block(self, _):
        agent = self._make_agent()
        raw = '```json\n{"meta_title": "제목"}\n```'
        result = agent._parse_json(raw)
        self.assertEqual(result['meta_title'], '제목')

    @patch('services.agents.base_agent.BaseAgent._get_default_model',
           return_value='gemini/gemini-3-flash-preview')
    def test_parse_json_invalid_returns_empty(self, _):
        agent = self._make_agent()
        result = agent._parse_json('이것은 JSON이 아닙니다')
        self.assertEqual(result, {})

    # --- _fallback_seo ---

    @patch('services.agents.base_agent.BaseAgent._get_default_model',
           return_value='gemini/gemini-3-flash-preview')
    def test_fallback_seo(self, _):
        agent = self._make_agent()
        result = agent._fallback_seo('제목', '요약 텍스트')
        self.assertEqual(result['meta_title'], '제목')
        self.assertEqual(result['keywords'], [])

    # --- JSON-LD 생성 ---

    @patch('services.agents.base_agent.BaseAgent._get_default_model',
           return_value='gemini/gemini-3-flash-preview')
    @patch('litellm.completion')
    @patch('services.seo.seo_metadata_service.generate_video_object_schema',
           return_value={'@type': 'VideoObject'})
    def test_execute_with_url_generates_json_ld(self, mock_schema, mock_llm, _):
        seo_json = json.dumps({
            "meta_title": "제목",
            "meta_description": "설명",
            "keywords": [],
            "faq": [],
            "og_title": "OG제목",
            "og_description": "OG설명",
        })
        mock_llm.return_value = self._mock_completion(seo_json)

        agent = self._make_agent()
        result = agent.execute({
            'edited_content': '콘텐츠',
            'title': '제목',
            'url': 'https://youtube.com/watch?v=test',
        })

        self.assertEqual(result['json_ld']['@type'], 'VideoObject')
        mock_schema.assert_called_once()


if __name__ == '__main__':
    unittest.main()
