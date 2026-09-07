"""repurpose_service 단위 테스트"""
import unittest
from unittest.mock import patch, MagicMock

from services.export.repurpose_service import RepurposeService, REPURPOSE_PROMPTS
from services.usage.usage_lock import UsageLockUnavailable


class TestRepurposePrompts(unittest.TestCase):

    def test_all_formats_defined(self):
        """7개 포맷 프롬프트 정의"""
        expected = {
            'twitter_thread', 'linkedin_post', 'youtube_shorts_script',
            'email_newsletter', 'podcast_outline', 'infographic_points', 'quiz',
        }
        self.assertEqual(set(REPURPOSE_PROMPTS.keys()), expected)

    def test_prompts_not_empty(self):
        """모든 프롬프트가 비어있지 않음"""
        for key, prompt in REPURPOSE_PROMPTS.items():
            self.assertGreater(len(prompt), 10, f"{key} 프롬프트가 너무 짧음")


class TestGetAvailableFormats(unittest.TestCase):

    def test_returns_list(self):
        """리스트 반환"""
        formats = RepurposeService.get_available_formats()
        self.assertIsInstance(formats, list)

    def test_format_structure(self):
        """각 항목에 format, label 키"""
        formats = RepurposeService.get_available_formats()
        for item in formats:
            self.assertIn('format', item)
            self.assertIn('label', item)

    def test_all_formats_included(self):
        """7개 포맷 전부 포함"""
        formats = RepurposeService.get_available_formats()
        format_ids = {f['format'] for f in formats}
        self.assertEqual(len(format_ids), 7)

    def test_labels_are_korean(self):
        """라벨이 한국어"""
        formats = RepurposeService.get_available_formats()
        # 최소 하나의 한국어 라벨 확인
        korean_count = sum(1 for f in formats if any('\uac00' <= c <= '\ud7a3' for c in f['label']))
        self.assertGreater(korean_count, 0)


class TestRepurpose(unittest.TestCase):

    def setUp(self):
        self.svc = RepurposeService()

    def test_invalid_format(self):
        """지원하지 않는 포맷 → ValueError"""
        with self.assertRaises(ValueError) as ctx:
            self.svc.repurpose('콘텐츠', 'invalid_format')
        self.assertIn('지원하지 않는', str(ctx.exception))

    @patch.object(RepurposeService, 'repurpose', wraps=None)
    def test_repurpose_returns_correct_keys(self, mock_rep):
        """repurpose 반환값 키 검증"""
        mock_rep.return_value = {
            'format': 'twitter_thread',
            'content': '변환 결과',
            'character_count': 5,
            'language': 'ko',
        }
        result = self.svc.repurpose('원본', 'twitter_thread')
        self.assertIn('format', result)
        self.assertIn('content', result)
        self.assertIn('character_count', result)

    def test_all_format_keys_in_prompts(self):
        """get_available_formats의 모든 format이 REPURPOSE_PROMPTS에 존재"""
        formats = RepurposeService.get_available_formats()
        for f in formats:
            self.assertIn(f['format'], REPURPOSE_PROMPTS)

    @patch('services.core.ai_service.call_litellm')
    def test_trusted_callback_is_forwarded_to_shared_provider_boundary(
        self,
        mock_call,
    ):
        callback = MagicMock()
        response = MagicMock()
        response.choices[0].message.content = '변환 결과'
        mock_call.return_value = response

        result = self.svc.repurpose(
            '원본',
            'twitter_thread',
            on_cost_start=callback,
        )

        self.assertEqual(result['content'], '변환 결과')
        self.assertIs(mock_call.call_args.kwargs['on_cost_start'], callback)

    @patch('services.core.ai_service.call_litellm')
    def test_usage_lock_loss_is_not_wrapped(self, mock_call):
        mock_call.side_effect = UsageLockUnavailable('lease lost')

        with self.assertRaises(UsageLockUnavailable):
            self.svc.repurpose(
                '원본',
                'twitter_thread',
                on_cost_start=MagicMock(),
            )


class TestRepurposeAll(unittest.TestCase):

    def setUp(self):
        self.svc = RepurposeService()

    @patch.object(RepurposeService, 'repurpose')
    def test_success_count(self, mock_repurpose):
        """성공 카운트"""
        mock_repurpose.return_value = {'format': 'test', 'content': 'ok', 'character_count': 2}
        result = self.svc.repurpose_all('콘텐츠', formats=['twitter_thread', 'quiz'])
        self.assertEqual(result['success_count'], 2)
        self.assertEqual(result['total_formats'], 2)

    @patch.object(RepurposeService, 'repurpose')
    def test_partial_failure(self, mock_repurpose):
        """일부 실패"""
        def side_effect(content, fmt, language='ko'):
            if fmt == 'quiz':
                raise RuntimeError("AI 오류")
            return {'format': fmt, 'content': 'ok', 'character_count': 2, 'language': language}

        mock_repurpose.side_effect = side_effect
        result = self.svc.repurpose_all('콘텐츠', formats=['twitter_thread', 'quiz'])
        self.assertEqual(result['success_count'], 1)
        self.assertIn('quiz', result['errors'])


if __name__ == '__main__':
    unittest.main()
