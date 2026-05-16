"""agents/orchestrator 단위 테스트

각 에이전트(Research/Writer/Editor/SEO)를 모의하여 파이프라인 흐름을 검증.
실 에이전트는 LLM 호출이 있어서 무거우므로 모의로 빠른 단위 테스트.
"""
import unittest
from unittest.mock import patch, MagicMock


def _make_orchestrator_with_mocks(
    research_result=None, writer_result=None,
    editor_result=None, seo_result=None,
    research_raise=None, writer_raise=None,
    editor_raise=None, seo_raise=None,
):
    """4개 에이전트를 모의한 Orchestrator 인스턴스 반환"""
    from services.agents.orchestrator import Orchestrator

    research = MagicMock()
    writer = MagicMock()
    editor = MagicMock()
    seo = MagicMock()

    research.execute = MagicMock(
        side_effect=research_raise,
        return_value=research_result or {
            'main_topic': 'AI', 'key_points': ['a', 'b'],
            'target_audience': '개발자', 'tone': '친근', 'summary': '요약',
            'web_results': [], 'web_context': '',
        }
    ) if research_raise is None else MagicMock(side_effect=research_raise)

    writer.execute = MagicMock(
        return_value=writer_result or {
            'draft': '# 제목\n\n본문 내용입니다.',
            'title': '제목',
        }
    ) if writer_raise is None else MagicMock(side_effect=writer_raise)

    editor.execute = MagicMock(
        return_value=editor_result or {
            'edited_content': '# 제목\n\n다듬어진 본문',
            'title': '제목',
            'quality': {'grade': 'A', 'score': 90},
        }
    ) if editor_raise is None else MagicMock(side_effect=editor_raise)

    seo.execute = MagicMock(
        return_value=seo_result or {
            'meta_title': '메타 제목', 'meta_description': '메타 설명',
            'keywords': ['k1'], 'faq': [], 'json_ld': {},
        }
    ) if seo_raise is None else MagicMock(side_effect=seo_raise)

    with patch('services.agents.orchestrator.ResearchAgent', return_value=research), \
         patch('services.agents.orchestrator.WriterAgent', return_value=writer), \
         patch('services.agents.orchestrator.EditorAgent', return_value=editor), \
         patch('services.agents.orchestrator.SEOAgent', return_value=seo):
        orch = Orchestrator(model='test-model')
    return orch, research, writer, editor, seo


class TestOrchestratorHappyPath(unittest.TestCase):
    """정상 파이프라인 — 4단계 모두 성공"""

    def test_returns_combined_result(self):
        orch, *_ = _make_orchestrator_with_mocks()
        result = orch.run(
            transcript='자막', style='blog_seo', style_prompt='블로그',
            url='https://youtu.be/abc', modifiers={'length': 'medium'},
        )
        self.assertEqual(result['title'], '제목')
        self.assertIn('다듬어진 본문', result['content'])
        self.assertIn('<', result['html'])  # markdown → html 변환됨
        self.assertEqual(result['quality']['grade'], 'A')
        self.assertEqual(result['seo']['meta_title'], '메타 제목')
        self.assertIn('elapsed_time', result)
        self.assertGreaterEqual(result['elapsed_time'], 0)

    def test_all_agents_called_with_growing_context(self):
        """각 에이전트에 누적된 context가 전달되는지"""
        orch, research, writer, editor, seo = _make_orchestrator_with_mocks()
        orch.run('자막', 'blog_seo', '블로그', url='https://yt/x')

        # 4개 에이전트 모두 한 번씩 호출됨
        self.assertEqual(research.execute.call_count, 1)
        self.assertEqual(writer.execute.call_count, 1)
        self.assertEqual(editor.execute.call_count, 1)
        self.assertEqual(seo.execute.call_count, 1)

        # writer는 research 결과(main_topic)를 포함한 context를 받음
        writer_ctx = writer.execute.call_args[0][0]
        self.assertEqual(writer_ctx.get('main_topic'), 'AI')
        # seo는 edited_content를 포함한 context를 받음
        seo_ctx = seo.execute.call_args[0][0]
        self.assertIn('edited_content', seo_ctx)

    def test_agent_results_section_present(self):
        orch, *_ = _make_orchestrator_with_mocks()
        result = orch.run('자막', 'blog_seo', '블로그')
        self.assertEqual(
            set(result['agent_results'].keys()),
            {'research', 'writer', 'editor', 'seo'}
        )


class TestOrchestratorFailureModes(unittest.TestCase):
    """에이전트 실패 시 graceful degradation"""

    def test_research_failure_does_not_stop_pipeline(self):
        """Research 실패 → 빈 결과로 계속, Writer/Editor/SEO 정상 실행"""
        orch, research, writer, editor, seo = _make_orchestrator_with_mocks(
            research_raise=RuntimeError('웹 검색 실패'),
        )
        result = orch.run('자막', 'blog_seo', '블로그')
        # Research 실패해도 최종 결과는 반환됨
        self.assertEqual(result['title'], '제목')
        self.assertEqual(writer.execute.call_count, 1)
        self.assertEqual(seo.execute.call_count, 1)

    def test_writer_failure_raises_runtime_error(self):
        """Writer 실패는 critical — RuntimeError로 전파"""
        orch, *_ = _make_orchestrator_with_mocks(
            writer_raise=RuntimeError('LLM 호출 실패'),
        )
        with self.assertRaises(RuntimeError) as ctx:
            orch.run('자막', 'blog_seo', '블로그')
        self.assertIn('콘텐츠 작성 실패', str(ctx.exception))

    def test_editor_failure_falls_back_to_draft(self):
        """Editor 실패 → 원본 draft를 final_content로 사용"""
        orch, *_ = _make_orchestrator_with_mocks(
            editor_raise=RuntimeError('편집 실패'),
        )
        result = orch.run('자막', 'blog_seo', '블로그')
        # draft 그대로 사용됨
        self.assertIn('본문 내용입니다', result['content'])
        self.assertEqual(result['quality'], {})

    def test_seo_failure_returns_empty_seo(self):
        """SEO 실패 → 메타데이터 빈 값으로 반환"""
        orch, *_ = _make_orchestrator_with_mocks(
            seo_raise=RuntimeError('SEO 실패'),
        )
        result = orch.run('자막', 'blog_seo', '블로그')
        self.assertEqual(result['seo']['meta_title'], '')
        self.assertEqual(result['seo']['keywords'], [])


class TestOrchestratorHTMLConversion(unittest.TestCase):
    """마크다운 → HTML 변환 + 실패 폴백"""

    def test_html_contains_markdown_tags(self):
        orch, *_ = _make_orchestrator_with_mocks(
            editor_result={
                'edited_content': '# 제목\n\n**굵게**',
                'title': '제목', 'quality': {},
            }
        )
        result = orch.run('자막', 'blog_seo', '블로그')
        self.assertIn('<h1>', result['html'])
        self.assertIn('<strong>', result['html'])

    def test_markdown_conversion_failure_falls_back_to_pre(self):
        """markdown 변환이 실패하면 escaped pre로 감쌈"""
        orch, *_ = _make_orchestrator_with_mocks(
            editor_result={
                'edited_content': '본문 <script>alert(1)</script>',
                'title': '제목', 'quality': {},
            }
        )
        with patch('services.agents.orchestrator.markdown.markdown', side_effect=RuntimeError('md 깨짐')):
            result = orch.run('자막', 'blog_seo', '블로그')
        self.assertIn('<pre>', result['html'])
        # XSS 방어 — script 태그가 이스케이프됨
        self.assertNotIn('<script>', result['html'])
        self.assertIn('&lt;script&gt;', result['html'])


if __name__ == '__main__':
    unittest.main()
