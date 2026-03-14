"""
다국어 출력 모디파이어 테스트
_build_modifier_instructions의 language 처리 검증
"""
import unittest


class TestLanguageModifier(unittest.TestCase):
    """language 모디파이어 테스트"""

    def _get_style_modifiers(self):
        """config.py의 STYLE_MODIFIERS와 동일한 구조"""
        return {
            'length': {
                'short': '총 분량은 약 500~800자로 핵심만 간결하게 작성하세요.',
                'medium': '총 분량은 약 1000~1500자로 적절히 작성하세요.',
                'long': '총 분량은 약 2000~3000자로 상세하고 풍부하게 작성하세요.',
            },
            'writing_style': {
                'conversational': '대화체(~요, ~해요)로 친근하게 작성하세요.',
                'explanatory': '설명체(~입니다, ~합니다)로 객관적으로 작성하세요.',
            },
            'language': {
                'ko': '결과는 반드시 한국어로 작성해주세요.',
                'en': 'You MUST write the entire result in English.',
                'ja': '結果は必ず日本語で書いてください。',
            },
        }

    def test_default_korean_when_no_modifiers(self):
        """modifiers가 None이면 기본 한국어 instruction 반환"""
        from services.core.ai_service import _build_modifier_instructions, DEFAULT_LANGUAGE_INSTRUCTION

        result = _build_modifier_instructions(None, self._get_style_modifiers())

        self.assertEqual(result, [DEFAULT_LANGUAGE_INSTRUCTION])

    def test_default_korean_when_language_not_specified(self):
        """language 키 미지정 시 기본 한국어 instruction 사용"""
        from services.core.ai_service import _build_modifier_instructions

        modifiers = {'length': 'short'}
        result = _build_modifier_instructions(modifiers, self._get_style_modifiers())

        self.assertEqual(result[0], '결과는 반드시 한국어로 작성해주세요.')

    def test_korean_explicit(self):
        """language='ko' 명시 시 한국어 instruction"""
        from services.core.ai_service import _build_modifier_instructions

        modifiers = {'language': 'ko'}
        result = _build_modifier_instructions(modifiers, self._get_style_modifiers())

        self.assertEqual(result[0], '결과는 반드시 한국어로 작성해주세요.')

    def test_english_language(self):
        """language='en' 시 영어 instruction"""
        from services.core.ai_service import _build_modifier_instructions

        modifiers = {'language': 'en', 'length': 'medium'}
        result = _build_modifier_instructions(modifiers, self._get_style_modifiers())

        self.assertEqual(result[0], 'You MUST write the entire result in English.')

    def test_japanese_language(self):
        """language='ja' 시 일본어 instruction"""
        from services.core.ai_service import _build_modifier_instructions

        modifiers = {'language': 'ja'}
        result = _build_modifier_instructions(modifiers, self._get_style_modifiers())

        self.assertEqual(result[0], '結果は必ず日本語で書いてください。')

    def test_language_with_other_modifiers(self):
        """language + length + writing_style 모두 포함"""
        from services.core.ai_service import _build_modifier_instructions

        modifiers = {'language': 'en', 'length': 'long', 'writing_style': 'explanatory'}
        result = _build_modifier_instructions(modifiers, self._get_style_modifiers())

        # language가 첫 번째
        self.assertEqual(result[0], 'You MUST write the entire result in English.')
        # length, writing_style도 포함
        self.assertIn('총 분량은 약 2000~3000자로 상세하고 풍부하게 작성하세요.', result)
        self.assertIn('설명체(~입니다, ~합니다)로 객관적으로 작성하세요.', result)

    def test_unknown_language_falls_back_to_default(self):
        """알 수 없는 language 값이면 기본 한국어 fallback"""
        from services.core.ai_service import _build_modifier_instructions, DEFAULT_LANGUAGE_INSTRUCTION

        modifiers = {'language': 'fr'}
        result = _build_modifier_instructions(modifiers, self._get_style_modifiers())

        self.assertEqual(result[0], DEFAULT_LANGUAGE_INSTRUCTION)


if __name__ == '__main__':
    unittest.main()
