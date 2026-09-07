"""
AI 서비스 단위 테스트
프롬프트 빌드, 에러 변환, 결과 파싱
"""
import unittest
from unittest.mock import patch, MagicMock


class TestBuildModifierInstructions(unittest.TestCase):
    """모디파이어 지시사항 빌드 테스트"""

    def test_empty_modifiers_returns_default_language(self):
        """빈 모디파이어시 기본 언어 지시 반환"""
        from services.core.ai_service import _build_modifier_instructions, DEFAULT_LANGUAGE_INSTRUCTION

        result = _build_modifier_instructions(None, {})

        self.assertEqual(result, [DEFAULT_LANGUAGE_INSTRUCTION])

    def test_with_length_modifier(self):
        """분량 모디파이어 적용"""
        from services.core.ai_service import _build_modifier_instructions

        style_modifiers = {
            'length': {
                'short': '짧게 작성해주세요.',
                'long': '상세하게 작성해주세요.'
            },
            'language': {
                'ko': '한국어로 작성해주세요.'
            }
        }

        result = _build_modifier_instructions({'length': 'short'}, style_modifiers)

        self.assertIn('짧게 작성해주세요.', result)

    def test_with_writing_style_modifier(self):
        """문체 모디파이어 적용 (v3.0: language 대신 writing_style 사용)"""
        from services.core.ai_service import _build_modifier_instructions

        style_modifiers = {
            'writing_style': {
                'conversational': '대화체로 작성해주세요.',
                'expert': '전문가 톤으로 작성해주세요.'
            }
        }

        result = _build_modifier_instructions({'writing_style': 'expert'}, style_modifiers)

        self.assertIn('전문가 톤으로 작성해주세요.', result)


class TestExtractTitleAndContent(unittest.TestCase):
    """제목/본문 분리 테스트"""

    def test_extract_title_from_h1(self):
        """# 제목 추출"""
        from services.core.ai_service import _extract_title_and_content

        markdown = "# 테스트 제목\n\n본문 내용입니다."
        title, content = _extract_title_and_content(markdown)

        self.assertEqual(title, "테스트 제목")
        self.assertEqual(content, "본문 내용입니다.")

    def test_no_title_uses_default(self):
        """제목 없으면 기본값 사용"""
        from services.core.ai_service import _extract_title_and_content

        markdown = "본문만 있는 내용"
        title, content = _extract_title_and_content(markdown)

        self.assertEqual(title, "AI 생성 결과")

    def test_multiple_h1_only_first(self):
        """첫 번째 # 만 제목으로 추출"""
        from services.core.ai_service import _extract_title_and_content

        markdown = "# 첫 번째 제목\n## 두 번째\n내용"
        title, content = _extract_title_and_content(markdown)

        self.assertEqual(title, "첫 번째 제목")


class TestConvertErrorMessage(unittest.TestCase):
    """에러 메시지 변환 테스트"""

    def test_invalid_api_key_error(self):
        """API 키 오류 한국어 변환"""
        from services.core.ai_service import _convert_error_message

        result = _convert_error_message("invalid_api_key: The API key provided is invalid")

        self.assertIn("API 키", result)
        self.assertIn("유효하지 않", result)

    def test_rate_limit_error(self):
        """Rate limit 오류 변환"""
        from services.core.ai_service import _convert_error_message

        result = _convert_error_message("rate_limit_exceeded")

        self.assertIn("한도", result)

    def test_model_not_found_error(self):
        """모델 미발견 오류 변환"""
        from services.core.ai_service import _convert_error_message

        result = _convert_error_message("The model 'gpt-5' does not exist or not found")

        self.assertIn("모델", result)

    def test_unknown_error_preserves_message(self):
        """알 수 없는 오류는 원본 메시지 포함"""
        from services.core.ai_service import _convert_error_message

        original = "Some unknown error occurred"
        result = _convert_error_message(original)

        self.assertIn(original, result)


class TestCreateContent(unittest.TestCase):
    """create_content 함수 테스트 (Flask 앱 컨텍스트 필요)"""

    def setUp(self):
        """테스트용 Flask 앱 컨텍스트 생성"""
        from app import create_app
        self.app = create_app({'TESTING': True})
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        """앱 컨텍스트 정리"""
        self.ctx.pop()

    @patch('litellm.completion')
    def test_create_content_success(self, mock_completion):
        """콘텐츠 생성 성공 케이스"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "# 생성된 제목\n\n생성된 내용입니다."
        mock_completion.return_value = mock_response

        from services.core.ai_service import create_content

        result = create_content(
            content="테스트 콘텐츠",
            model="gpt-4o-mini",
            style_prompt="블로그 스타일로 작성"
        )

        self.assertIn('title', result)
        self.assertIn('content', result)
        self.assertIn('html', result)

    @patch('litellm.completion')
    def test_create_content_returns_prompt(self, mock_completion):
        """프롬프트 반환 옵션 테스트"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "# 제목\n내용"
        mock_completion.return_value = mock_response

        from services.core.ai_service import create_content

        result, prompt = create_content(
            content="테스트",
            model="gpt-4o-mini",
            return_prompt=True
        )

        self.assertIsInstance(result, dict)
        self.assertIsInstance(prompt, str)
        self.assertIn("테스트", prompt)


class TestCompletionChargeBoundary(unittest.TestCase):
    def setUp(self):
        from flask import Flask

        self.app = Flask(__name__)

    def test_completion_is_loaded_before_charge_and_called_after_charge(self):
        from flask import g
        from services.core.ai_service import _call_completion_with_model_retry
        from services.usage.usage_decorator import UsageChargeState

        state = UsageChargeState()
        events = []

        def completion_factory():
            events.append(('load', state.committed))

            def completion(**kwargs):
                events.append(('call', state.committed, kwargs))
                return 'response'

            return completion

        with self.app.test_request_context():
            g.usage_charge_state = state
            with patch(
                'services.core.ai_service._get_completion',
                side_effect=completion_factory,
            ):
                result = _call_completion_with_model_retry(
                    'cliproxyapi/gpt-5.5',
                    {'model': 'gpt-5.4-mini'},
                )

        self.assertEqual(result, 'response')
        self.assertEqual(events[0], ('load', False))
        self.assertEqual(
            events[1],
            ('call', True, {'model': 'gpt-5.4-mini'}),
        )

    def test_explicit_callback_runs_at_actual_provider_boundary(self):
        from services.core.ai_service import _call_completion_with_model_retry

        events = []

        def completion_factory():
            events.append('load')

            def completion(**_kwargs):
                events.append('provider')
                return 'response'

            return completion

        with patch(
            'services.core.ai_service._get_completion',
            side_effect=completion_factory,
        ):
            result = _call_completion_with_model_retry(
                'cliproxyapi/gpt-5.5',
                {'model': 'gpt-5.4-mini'},
                on_cost_start=lambda: events.append('cost'),
            )

        self.assertEqual(result, 'response')
        self.assertEqual(events, ['load', 'cost', 'provider'])

    def test_legacy_call_litellm_uses_shared_cost_boundary(self):
        from services.core.ai_service import call_litellm

        events = []
        provider_response = MagicMock()

        def provider(**kwargs):
            events.append('provider')
            self.assertEqual(kwargs['messages'][0]['content'], 'translate')
            return provider_response

        with patch(
            'services.core.ai_service._get_completion',
            return_value=provider,
        ):
            result = call_litellm(
                [{'role': 'user', 'content': 'translate'}],
                model='cliproxyapi/gpt-5.5',
                on_cost_start=lambda: events.append('cost'),
            )

        self.assertIs(result, provider_response)
        self.assertEqual(events, ['cost', 'provider'])

    def test_create_content_rethrows_lock_loss_and_skips_provider(self):
        from services.core.ai_service import create_content
        from services.usage.usage_lock import UsageLockUnavailable

        provider = MagicMock()

        def reject_cost():
            raise UsageLockUnavailable('lease lost')

        with self.app.test_request_context(), patch(
            'services.core.ai_prompt_context.build_optional_prompt_contexts',
            return_value=(None, None, [], None, None),
        ), patch(
            'services.core.ai_service._get_completion',
            return_value=provider,
        ):
            with self.assertRaises(UsageLockUnavailable):
                create_content(
                    'content',
                    'cliproxyapi/gpt-5.5',
                    on_cost_start=reject_cost,
                )

        provider.assert_not_called()

    def test_preflight_failure_does_not_commit_explicit_callback(self):
        from services.core.ai_service import create_content

        on_cost_start = MagicMock()
        with self.app.test_request_context(), patch(
            'services.core.ai_prompt_context.build_optional_prompt_contexts',
            side_effect=RuntimeError('preflight failed'),
        ):
            with self.assertRaises(Exception):
                create_content(
                    'content',
                    'cliproxyapi/gpt-5.5',
                    on_cost_start=on_cost_start,
                )

        on_cost_start.assert_not_called()


class TestStreamingUsage(unittest.TestCase):
    """스트리밍 final chunk usage 추출 테스트"""

    def test_stream_kwargs_include_usage_option(self):
        from services.core.ai_service import _build_completion_kwargs

        kwargs = _build_completion_kwargs(
            'gpt-4o-mini',
            '프롬프트',
            stream=True,
        )

        self.assertTrue(kwargs['stream'])
        self.assertEqual(kwargs['stream_options'], {'include_usage': True})

    def test_stream_callback_runs_at_provider_boundary(self):
        from flask import Flask
        from services.core.ai_streaming import create_content_stream

        app = Flask(__name__)
        events = []

        def completion_factory():
            events.append('load')

            def completion(**_kwargs):
                events.append('provider')
                return []

            return completion

        with app.test_request_context(), patch(
            'services.core.ai_streaming.build_optional_prompt_contexts',
            return_value=(None, None, [], None, None),
        ), patch(
            'services.core.ai_service._get_completion',
            side_effect=completion_factory,
        ):
            self.assertEqual(list(create_content_stream(
                'content',
                'cliproxyapi/gpt-5.5',
                on_cost_start=lambda: events.append('cost'),
            )), [])

        self.assertEqual(events, ['load', 'cost', 'provider'])

    def test_stream_lock_loss_is_not_wrapped(self):
        from flask import Flask
        from services.core.ai_streaming import create_content_stream
        from services.usage.usage_lock import UsageLockUnavailable

        app = Flask(__name__)
        provider = MagicMock()

        def reject_cost():
            raise UsageLockUnavailable('lease lost')

        with app.test_request_context(), patch(
            'services.core.ai_streaming.build_optional_prompt_contexts',
            return_value=(None, None, [], None, None),
        ), patch(
            'services.core.ai_service._get_completion',
            return_value=provider,
        ):
            with self.assertRaises(UsageLockUnavailable):
                list(create_content_stream(
                    'content',
                    'cliproxyapi/gpt-5.5',
                    on_cost_start=reject_cost,
                ))

        provider.assert_not_called()

    def test_stream_preflight_failure_does_not_commit_callback(self):
        from flask import Flask
        from services.core.ai_streaming import create_content_stream

        app = Flask(__name__)
        on_cost_start = MagicMock()
        with app.test_request_context(), patch(
            'services.core.ai_streaming.build_optional_prompt_contexts',
            side_effect=RuntimeError('preflight failed'),
        ):
            with self.assertRaises(Exception):
                list(create_content_stream(
                    'content',
                    'cliproxyapi/gpt-5.5',
                    on_cost_start=on_cost_start,
                ))

        on_cost_start.assert_not_called()

    def test_extract_stream_usage_from_include_usage_chunk(self):
        from services.core.ai_streaming import _extract_stream_usage

        chunk = {
            'choices': [],
            'usage': {
                'prompt_tokens': 12,
                'completion_tokens': 8,
                'total_tokens': 20,
            },
        }

        self.assertEqual(
            _extract_stream_usage(chunk),
            {'prompt_tokens': 12, 'completion_tokens': 8, 'total_tokens': 20},
        )


if __name__ == '__main__':
    unittest.main()
