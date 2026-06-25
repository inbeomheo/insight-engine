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

    def test_chatmock_connection_error_is_friendly(self):
        """ChatMock 연결 실패는 실행 상태 확인 안내로 변환"""
        from services.core.ai_service import _convert_error_message

        result = _convert_error_message(
            "Connection refused by upstream",
            model="chatmock/gpt-5.3-codex-spark",
        )

        self.assertIn("ChatMock Spark 서버에 연결할 수 없습니다", result)
        self.assertIn("CHATMOCK_BASE_URL", result)

    def test_glm_missing_key_is_friendly(self):
        """GLM 키 누락은 지원 env 이름을 안내"""
        from services.core.ai_service import _convert_error_message

        result = _convert_error_message(
            "ZAI_API_KEY 또는 ZHIPUAI_API_KEY 환경변수가 설정되지 않았습니다.",
            model="zhipuai/GLM-4.7",
        )

        self.assertIn("GLM API 키", result)
        self.assertIn("ZAI_API_KEY", result)
        self.assertIn("ZHIPUAI_API_KEY", result)

    def test_unknown_error_redacts_secret_values(self):
        """원본 오류에 키처럼 보이는 값이 있으면 마스킹"""
        from services.core.ai_service import _convert_error_message

        result = _convert_error_message("upstream failed api_key=sk-secret123")

        self.assertIn("[REDACTED]", result)
        self.assertNotIn("sk-secret123", result)


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


if __name__ == '__main__':
    unittest.main()
