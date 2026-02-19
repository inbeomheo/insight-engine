"""퓨전 오케스트레이터 서비스 테스트"""
import unittest
from unittest.mock import patch, MagicMock


class TestFusionService(unittest.TestCase):

    @patch('services.fusion_service.ai_service')
    @patch('services.fusion_service.comment_analyzer_service')
    @patch('services.fusion_service.web_research_service')
    @patch('services.fusion_service.content_service')
    def test_generate_fusion_full(self, mock_cs, mock_wr, mock_ca, mock_ai):
        mock_cs.get_video_id.return_value = 'vid1'
        mock_cs.get_transcript.return_value = {'text': '자막1', 'source': 'api'}
        mock_cs.get_top_comments.return_value = ['댓글1', '댓글2']

        mock_ai.create_content.return_value = {
            'title': '퓨전 제목',
            'content': '# 퓨전 본문\n내용',
            'html': '<h1>퓨전 본문</h1>',
            'usage': {'prompt_tokens': 100, 'completion_tokens': 200, 'total_tokens': 300}
        }
        mock_ca.analyze_comments.return_value = {
            'insights': ['인사이트1'], 'questions': ['질문1'],
            'fact_checks': [], 'sentiments': ['감상1'],
            'usage': {'total_tokens': 50}
        }
        mock_wr.research_topic.return_value = [
            {'title': 'Art1', 'url': 'http://ex.com', 'summary': '요약1'}
        ]

        from services.fusion_service import generate_fusion
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

    @patch('services.fusion_service.ai_service')
    @patch('services.fusion_service.content_service')
    def test_generate_fusion_without_optional(self, mock_cs, mock_ai):
        mock_cs.get_video_id.return_value = 'vid1'
        mock_cs.get_transcript.return_value = {'text': '자막1', 'source': 'api'}
        mock_cs.get_top_comments.return_value = []
        mock_ai.create_content.return_value = {
            'title': '제목', 'content': '내용', 'html': '<p>내용</p>',
            'usage': {'prompt_tokens': 50, 'completion_tokens': 100, 'total_tokens': 150}
        }

        from services.fusion_service import generate_fusion
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
        from services.fusion_service import generate_fusion
        with self.assertRaises(ValueError):
            generate_fusion(
                urls=['https://youtube.com/watch?v=vid1'],
                style_id='blog_seo', model='m', modifiers={},
                enable_web_research=False, enable_deep_comments=False
            )


if __name__ == '__main__':
    unittest.main()
