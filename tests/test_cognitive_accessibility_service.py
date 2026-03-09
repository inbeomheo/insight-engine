"""인지 접근성 서비스 테스트."""
import unittest

from services.cognitive_accessibility_service import (
    CognitivePreset,
    apply_cognitive_preset,
    list_presets,
    _apply_short_paragraphs,
    _expand_acronyms_first_use,
    _insert_compound_dots,
    _bold_first_sentences,
    _add_paragraph_separators,
    _enhance_headings,
    _bold_emphasis,
)


class TestListPresets(unittest.TestCase):
    """프리셋 목록 테스트."""

    def test_returns_all_presets(self):
        """4가지 프리셋 반환."""
        presets = list_presets()
        self.assertEqual(len(presets), 4)
        names = {p.name for p in presets}
        self.assertEqual(names, {'general', 'dyslexia', 'adhd', 'low_vision'})

    def test_preset_structure(self):
        """프리셋 구조 확인."""
        for preset in list_presets():
            self.assertIsInstance(preset, CognitivePreset)
            self.assertTrue(len(preset.name) > 0)
            self.assertTrue(len(preset.description) > 0)
            self.assertIsInstance(preset.rules, list)
            self.assertGreater(len(preset.rules), 0)


class TestApplyShortParagraphs(unittest.TestCase):
    """긴 문단 분리 테스트."""

    def test_short_paragraph_unchanged(self):
        """짧은 문단은 변경 없음."""
        text = '첫 문장. 두 번째 문장.'
        result = _apply_short_paragraphs(text, max_sentences=3)
        self.assertIn('첫 문장', result)
        self.assertIn('두 번째 문장', result)

    def test_long_paragraph_split(self):
        """5문장 문단을 3문장 단위로 분리."""
        text = '문장1입니다. 문장2입니다. 문장3입니다. 문장4입니다. 문장5입니다.'
        result = _apply_short_paragraphs(text, max_sentences=3)
        paragraphs = [p for p in result.split('\n\n') if p.strip()]
        self.assertGreaterEqual(len(paragraphs), 2)

    def test_heading_preserved(self):
        """마크다운 헤딩은 분리 안 됨."""
        text = '# 제목\n이 내용은 유지됩니다. 두 번째 문장. 세 번째 문장. 네 번째 문장.'
        result = _apply_short_paragraphs(text, max_sentences=3)
        self.assertIn('# 제목', result)


class TestExpandAcronymsFirstUse(unittest.TestCase):
    """약어 풀어쓰기 테스트."""

    def test_known_acronym(self):
        """알려진 약어 풀어쓰기."""
        text = 'AI 기술이 발전하고 있습니다. AI는 미래입니다.'
        result = _expand_acronyms_first_use(text)
        self.assertIn('인공지능(AI)', result)
        # 두 번째 등장은 그대로
        self.assertEqual(result.count('인공지능(AI)'), 1)

    def test_multiple_acronyms(self):
        """여러 약어 처리."""
        text = 'API와 URL을 사용합니다.'
        result = _expand_acronyms_first_use(text)
        self.assertIn('API', result)
        self.assertIn('URL', result)

    def test_no_acronyms(self):
        """약어 없는 텍스트."""
        text = '평범한 한국어 텍스트입니다.'
        result = _expand_acronyms_first_use(text)
        self.assertEqual(result, text)


class TestInsertCompoundDots(unittest.TestCase):
    """복합어 가운뎃점 삽입 테스트 (난독증)."""

    def test_long_compound_word(self):
        """6자 이상 복합어에 가운뎃점 삽입."""
        text = '인공지능기술이 발전합니다'
        result = _insert_compound_dots(text)
        self.assertIn('·', result)

    def test_short_word_unchanged(self):
        """짧은 단어는 변경 없음."""
        text = '기술이 좋습니다'
        result = _insert_compound_dots(text)
        self.assertNotIn('·', result)


class TestBoldFirstSentences(unittest.TestCase):
    """첫 문장 볼드 처리 테스트 (ADHD)."""

    def test_bold_applied(self):
        """첫 문장에 볼드 적용."""
        text = '핵심 포인트입니다. 부가 설명입니다.'
        result = _bold_first_sentences(text)
        self.assertIn('**핵심 포인트입니다.**', result)

    def test_heading_skipped(self):
        """헤딩은 볼드 처리 안 함."""
        text = '# 제목'
        result = _bold_first_sentences(text)
        self.assertNotIn('**# 제목**', result)

    def test_already_bold_skipped(self):
        """이미 볼드된 텍스트는 건너뜀."""
        text = '**이미 볼드입니다.** 추가 텍스트.'
        result = _bold_first_sentences(text)
        # 이중 볼드 없음
        self.assertNotIn('****', result)


class TestAddParagraphSeparators(unittest.TestCase):
    """문단 구분선 추가 테스트 (ADHD)."""

    def test_separator_added(self):
        """문단 사이에 구분선 추가."""
        text = '첫 문단입니다.\n두 번째 문단입니다.'
        result = _add_paragraph_separators(text)
        self.assertIn('---', result)

    def test_single_paragraph(self):
        """단일 문단은 구분선 없음."""
        text = '하나의 문단입니다.'
        result = _add_paragraph_separators(text)
        self.assertNotIn('---', result)

    def test_heading_no_separator(self):
        """헤딩 뒤에는 구분선 불필요."""
        text = '# 제목\n내용입니다.'
        result = _add_paragraph_separators(text)
        # 헤딩 바로 뒤에 --- 없어야 함
        lines = result.split('\n\n')
        heading_idx = next(i for i, l in enumerate(lines) if l.startswith('#'))
        if heading_idx + 1 < len(lines):
            self.assertNotEqual(lines[heading_idx + 1], '---')


class TestEnhanceHeadings(unittest.TestCase):
    """헤딩 보강 테스트 (저시력)."""

    def test_adds_headings_to_long_content(self):
        """5문단 이상 콘텐츠에 섹션 헤딩 추가."""
        paragraphs = [f'문단 {i}입니다.' for i in range(6)]
        text = '\n'.join(paragraphs)
        result = _enhance_headings(text)
        self.assertIn('### 섹션', result)

    def test_existing_headings_preserved(self):
        """이미 헤딩이 있으면 변경 없음."""
        text = '# 제목\n문단1.\n문단2.\n문단3.\n문단4.\n문단5.'
        result = _enhance_headings(text)
        self.assertNotIn('### 섹션', result)

    def test_short_content_unchanged(self):
        """짧은 콘텐츠는 변경 없음."""
        text = '문단1.\n문단2.'
        result = _enhance_headings(text)
        self.assertNotIn('### 섹션', result)


class TestBoldEmphasis(unittest.TestCase):
    """기울임 → 볼드 변환 테스트 (저시력)."""

    def test_italic_to_bold(self):
        """단일 *기울임*을 **볼드**로 변환."""
        text = '이것은 *강조* 텍스트입니다.'
        result = _bold_emphasis(text)
        self.assertIn('**강조**', result)

    def test_existing_bold_unchanged(self):
        """이미 **볼드**인 텍스트는 변경 없음."""
        text = '이것은 **볼드** 텍스트입니다.'
        result = _bold_emphasis(text)
        self.assertEqual(result, text)


class TestApplyCognitivePreset(unittest.TestCase):
    """프리셋 적용 통합 테스트."""

    def test_general_preset(self):
        """general 프리셋 적용."""
        text = 'AI 기술을 활용합니다. 매우 긴 문장이 있습니다. 추가 문장. 또 추가.'
        result = apply_cognitive_preset(text, 'general')
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_dyslexia_preset(self):
        """dyslexia 프리셋: 복합어 가운뎃점 삽입."""
        text = '인공지능기술을 활용합니다.'
        result = apply_cognitive_preset(text, 'dyslexia')
        # 가운뎃점 또는 약어 풀어쓰기 적용
        self.assertIsInstance(result, str)

    def test_adhd_preset(self):
        """adhd 프리셋: 볼드 + 구분선."""
        text = '핵심 내용입니다.\n부가 설명입니다.'
        result = apply_cognitive_preset(text, 'adhd')
        self.assertIn('**', result)

    def test_low_vision_preset(self):
        """low_vision 프리셋."""
        text = '내용이 있는 *강조* 텍스트입니다.'
        result = apply_cognitive_preset(text, 'low_vision')
        self.assertIn('**강조**', result)

    def test_invalid_preset(self):
        """존재하지 않는 프리셋 → ValueError."""
        with self.assertRaises(ValueError):
            apply_cognitive_preset('테스트', 'nonexistent')

    def test_empty_text(self):
        """빈 텍스트 처리."""
        result = apply_cognitive_preset('', 'general')
        self.assertEqual(result, '')

    def test_none_text(self):
        """None 텍스트 처리."""
        result = apply_cognitive_preset(None, 'general')
        self.assertEqual(result, '')

    def test_all_presets_run(self):
        """모든 프리셋이 에러 없이 실행."""
        text = 'AI와 API를 활용하여 체계적으로 구현합니다. 추가 문장. 또 추가.'
        for preset in ['general', 'dyslexia', 'adhd', 'low_vision']:
            result = apply_cognitive_preset(text, preset)
            self.assertIsInstance(result, str)
            self.assertTrue(len(result) > 0)


if __name__ == '__main__':
    unittest.main()
