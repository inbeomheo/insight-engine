"""copilot_service 단위 테스트"""
import unittest
from unittest.mock import patch, MagicMock

from services.copilot_service import CopilotService


class TestCopilotService(unittest.TestCase):

    def setUp(self):
        self.svc = CopilotService()

    @patch.object(CopilotService, '_call_ai', return_value='완성된 텍스트입니다.')
    def test_complete(self, mock_ai):
        """자동완성"""
        result = self.svc.complete('파이썬은 ')
        self.assertEqual(result, '완성된 텍스트입니다.')
        mock_ai.assert_called_once()

    @patch.object(CopilotService, '_call_ai', return_value='완성 결과')
    def test_complete_with_context(self, mock_ai):
        """컨텍스트가 있는 자동완성"""
        result = self.svc.complete('접두사', context='문서 전체')
        self.assertEqual(result, '완성 결과')

    @patch.object(CopilotService, '_call_ai', return_value='재작성된 텍스트')
    def test_rewrite(self, mock_ai):
        """재작성"""
        result = self.svc.rewrite('원본 텍스트', '더 간결하게')
        self.assertEqual(result, '재작성된 텍스트')

    @patch.object(CopilotService, '_call_ai', return_value='교정된 텍스트')
    def test_correct_grammar(self, mock_ai):
        """문법 교정"""
        result = self.svc.correct_grammar('틀린 문장입니다')
        self.assertEqual(result, '교정된 텍스트')

    @patch.object(CopilotService, '_call_ai', return_value='- 제안1\n- 제안2\n- 제안3')
    def test_suggest_improvements(self, mock_ai):
        """개선 제안"""
        suggestions = self.svc.suggest_improvements('텍스트')
        self.assertEqual(len(suggestions), 3)
        self.assertEqual(suggestions[0], '제안1')

    @patch.object(CopilotService, '_call_ai', return_value='확장된 텍스트입니다.')
    def test_expand(self, mock_ai):
        """텍스트 확장"""
        result = self.svc.expand('짧은 텍스트')
        self.assertEqual(result, '확장된 텍스트입니다.')

    @patch.object(CopilotService, '_call_ai', return_value='요약')
    def test_compress(self, mock_ai):
        """텍스트 압축"""
        result = self.svc.compress('긴 텍스트입니다 여러 문장이 있습니다')
        self.assertEqual(result, '요약')

    @patch.object(CopilotService, '_call_ai', side_effect=RuntimeError('AI 오류'))
    def test_complete_error(self, mock_ai):
        """AI 호출 실패"""
        with self.assertRaises(RuntimeError):
            self.svc.complete('입력')

    @patch.object(CopilotService, '_call_ai', return_value='결과 없음')
    def test_suggest_improvements_no_bullets(self, mock_ai):
        """제안이 '-'로 시작하지 않으면 빈 리스트"""
        suggestions = self.svc.suggest_improvements('텍스트')
        self.assertEqual(len(suggestions), 0)

    @patch.object(CopilotService, '_call_ai', return_value='교정 결과')
    def test_correct_grammar_english(self, mock_ai):
        """영어 문법 교정"""
        result = self.svc.correct_grammar('bad grammar', language='en')
        self.assertEqual(result, '교정 결과')
        # system_prompt에 '영어'가 포함되었는지 확인
        call_args = mock_ai.call_args[0]
        self.assertIn('영어', call_args[0])


if __name__ == '__main__':
    unittest.main()
