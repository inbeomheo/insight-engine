"""퓨전 오케스트레이터 서비스 테스트"""
import unittest
from unittest.mock import patch, MagicMock

from services.usage.usage_lock import UsageLockUnavailable


class TestFusionService(unittest.TestCase):

    @patch('services.core.fusion_service.ai_service')
    @patch('services.core.fusion_service.web_research_service')
    @patch('services.core.fusion_service.content_service')
    def test_generate_fusion_full(self, mock_cs, mock_wr, mock_ai):
        mock_cs.get_video_id.return_value = 'vid1'
        mock_cs.get_transcript.return_value = {'text': '자막1', 'source': 'api'}
        mock_cs.get_top_comments.return_value = ['댓글1', '댓글2']

        mock_ai.create_content.return_value = {
            'title': '퓨전 제목',
            'content': '# 퓨전 본문\n내용',
            'html': '<h1>퓨전 본문</h1>',
            'usage': {'prompt_tokens': 100, 'completion_tokens': 200, 'total_tokens': 300}
        }
        mock_wr.research_topic.return_value = [
            {'title': 'Art1', 'url': 'http://ex.com', 'summary': '요약1'}
        ]

        from services.core.fusion_service import generate_fusion
        result = generate_fusion(
            urls=['https://youtube.com/watch?v=vid1', 'https://youtube.com/watch?v=vid2'],
            style_id='blog_seo',
            model='gemini/gemini-3-flash-preview',
            modifiers={'length': 'long'},
            enable_web_research=True,
            enable_deep_comments=True
        )
        self.assertIn('title', result)
        self.assertIn('content', result)
        self.assertIn('fusion_meta', result)
        self.assertIn('videos_analyzed', result['fusion_meta'])

    @patch('services.core.fusion_service.ai_service')
    @patch('services.core.fusion_service.content_service')
    def test_generate_fusion_without_optional(self, mock_cs, mock_ai):
        mock_cs.get_video_id.return_value = 'vid1'
        mock_cs.get_transcript.return_value = {'text': '자막1', 'source': 'api'}
        mock_cs.get_top_comments.return_value = []
        mock_ai.create_content.return_value = {
            'title': '제목', 'content': '내용', 'html': '<p>내용</p>',
            'usage': {'prompt_tokens': 50, 'completion_tokens': 100, 'total_tokens': 150}
        }

        from services.core.fusion_service import generate_fusion
        result = generate_fusion(
            urls=['https://youtube.com/watch?v=vid1', 'https://youtube.com/watch?v=vid2'],
            style_id='blog_seo',
            model='gemini/gemini-3-flash-preview',
            modifiers={},
            enable_web_research=False,
            enable_deep_comments=False
        )
        self.assertIn('title', result)

    def test_generate_fusion_too_few_urls(self):
        from services.core.fusion_service import generate_fusion
        with self.assertRaises(ValueError):
            generate_fusion(
                urls=['https://youtube.com/watch?v=vid1'],
                style_id='blog_seo', model='m', modifiers={},
                enable_web_research=False, enable_deep_comments=False
            )

    @patch('services.core.fusion_service.ai_service')
    @patch('services.core.fusion_service.web_research_service')
    @patch('services.core.fusion_service.content_service')
    def test_cost_callback_runs_for_each_phase2_and_final_boundary(
        self,
        mock_cs,
        mock_wr,
        mock_ai,
    ):
        """요약·댓글·웹 리서치·최종 AI 호출이 각각 비용을 확정한다."""
        mock_cs.get_video_id.return_value = 'vid1'
        mock_cs.get_transcript.return_value = {'text': '자막', 'source': 'api'}
        mock_cs.get_top_comments.return_value = ['댓글']
        def create_content(*args, **kwargs):
            callback = kwargs.get('on_cost_start')
            if callback is not None:
                callback()
            return {
                'title': '제목',
                'content': '내용',
                'html': '<p>내용</p>',
                'usage': {'total_tokens': 1},
            }

        mock_ai.create_content.side_effect = create_content
        mock_wr.research_topic.side_effect = (
            lambda *args, on_cost_start=None, **kwargs:
            (on_cost_start(), [])[1]
        )
        on_cost_start = MagicMock()

        from services.core.fusion_service import generate_fusion

        generate_fusion(
            urls=['https://example.com/1', 'https://example.com/2'],
            style_id='summary',
            model='model',
            modifiers={},
            on_cost_start=on_cost_start,
        )

        # 자막 요약 2회 + 댓글 1회 + 웹 리서치 1회 + 최종 AI 1회
        self.assertEqual(on_cost_start.call_count, 5)

    @patch('services.core.fusion_service._phase1_collect')
    def test_all_transcript_failures_do_not_commit_cost(
        self,
        mock_phase1,
    ):
        """Phase 1에서 자막을 하나도 얻지 못하면 비용 콜백을 호출하지 않는다."""
        mock_phase1.return_value = ([], [], 0, ['url-1', 'url-2'])
        on_cost_start = MagicMock()

        from services.core.fusion_service import generate_fusion

        with self.assertRaisesRegex(ValueError, '모든 영상의 자막'):
            generate_fusion(
                urls=['url-1', 'url-2'],
                style_id='summary',
                model='model',
                modifiers={},
                on_cost_start=on_cost_start,
            )

        on_cost_start.assert_not_called()

    def test_helper_callbacks_are_forwarded_to_the_actual_ai_boundary(self):
        """스레드 worker도 실제 AI 경계에 콜백을 명시 전달한다."""
        from services.core import fusion_service

        for helper, args, target in (
            (
                fusion_service._summarize_transcript,
                ('text', 'video', 'model'),
                fusion_service.ai_service,
            ),
            (
                fusion_service._analyze_comments,
                (['comment'], 'model'),
                fusion_service.ai_service,
            ),
        ):
            events = []
            def create_content(*args, **kwargs):
                kwargs['on_cost_start']()
                events.append('cost')
                return {}

            with patch.object(target, 'create_content', side_effect=create_content):
                helper(*args, on_cost_start=lambda: events.append('callback'))
            self.assertEqual(events, ['callback', 'cost'])

    @patch('services.core.fusion_service.web_research_service.research_topic')
    def test_web_research_receives_cost_callback(self, mock_research):
        from services.core import fusion_service

        on_cost_start = MagicMock()

        fusion_service._research_topic(
            ['text'],
            'model',
            on_cost_start=on_cost_start,
        )

        mock_research.assert_called_once_with(
            ['text'],
            'model',
            on_cost_start=on_cost_start,
        )
        on_cost_start.assert_not_called()

    @patch('services.core.fusion_service._summarize_transcript')
    def test_phase2_propagates_usage_lock_failure(self, mock_summary):
        from services.core import fusion_service

        mock_summary.side_effect = UsageLockUnavailable('lease lost')

        with self.assertRaises(UsageLockUnavailable):
            fusion_service._phase2_analyze(
                [{'text': 'text', 'video_id': 'video', 'url': 'url'}],
                [],
                'model',
                False,
                False,
                MagicMock(),
            )

    @patch('services.core.fusion_service.content_service')
    def test_phase1_forwards_callback_to_comments_and_applies_limit(
        self,
        mock_content_service,
    ):
        from services.core import fusion_service

        callback = MagicMock()
        mock_content_service.get_video_id.return_value = 'video-id'
        mock_content_service.get_transcript.return_value = {
            'text': '자막',
            'source': 'cache',
        }
        mock_content_service.get_top_comments.return_value = [
            f'댓글-{index}'
            for index in range(fusion_service.MAX_COMMENTS_PER_VIDEO + 10)
        ]

        _, comments, total_comments, _ = fusion_service._phase1_collect(
            ['https://example.com/video'],
            on_cost_start=callback,
        )

        self.assertEqual(
            total_comments,
            fusion_service.MAX_COMMENTS_PER_VIDEO,
        )
        self.assertEqual(
            len(comments),
            fusion_service.MAX_COMMENTS_PER_VIDEO,
        )
        mock_content_service.get_top_comments.assert_called_once_with(
            'video-id',
            on_cost_start=callback,
        )

    @patch('services.core.fusion_service.content_service')
    def test_phase1_does_not_swallow_comment_usage_lock_loss(
        self,
        mock_content_service,
    ):
        from services.core import fusion_service

        mock_content_service.get_video_id.return_value = 'video-id'
        mock_content_service.get_transcript.return_value = {
            'text': '자막',
            'source': 'cache',
        }
        mock_content_service.get_top_comments.side_effect = (
            UsageLockUnavailable('lease lost')
        )

        with self.assertRaises(UsageLockUnavailable):
            fusion_service._phase1_collect(
                ['https://example.com/video'],
                on_cost_start=MagicMock(),
            )


if __name__ == '__main__':
    unittest.main()
