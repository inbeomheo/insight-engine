"""snippet_generator_service 단위 테스트"""
import unittest

from services.content.snippet_generator_service import (
    generate_snippet,
    generate_multi_snippets,
    get_snippet_presets,
    _clean_markdown,
    _truncate_at_sentence,
    SNIPPET_PRESETS,
)


class TestGenerateSnippet(unittest.TestCase):

    def test_empty_content(self):
        result = generate_snippet('')
        self.assertEqual(result['snippet'], '')
        self.assertEqual(result['char_count'], 0)

    def test_none_content(self):
        result = generate_snippet(None)
        self.assertEqual(result['snippet'], '')

    def test_short_content(self):
        text = '짧은 콘텐츠입니다.'
        result = generate_snippet(text)
        self.assertEqual(result['snippet'], text)
        self.assertFalse(result['truncated'])

    def test_long_content_truncated(self):
        text = '긴 문장입니다. ' * 50
        result = generate_snippet(text, preset='meta')
        self.assertLessEqual(result['char_count'], 160)
        self.assertTrue(result['truncated'])

    def test_preset_meta(self):
        text = '메타 디스크립션 테스트입니다. ' * 30
        result = generate_snippet(text, preset='meta')
        self.assertLessEqual(result['char_count'], 160)
        self.assertEqual(result['preset'], 'meta')

    def test_preset_twitter(self):
        text = '트위터 미리보기 테스트입니다. ' * 30
        result = generate_snippet(text, preset='twitter')
        self.assertLessEqual(result['char_count'], 250)

    def test_custom_max_chars(self):
        text = '커스텀 길이 테스트입니다. ' * 20
        result = generate_snippet(text, max_chars=50)
        self.assertLessEqual(result['char_count'], 50)

    def test_markdown_removed(self):
        text = '# 제목\n**볼드** 텍스트와 [링크](url)가 있습니다.'
        result = generate_snippet(text)
        self.assertNotIn('#', result['snippet'])
        self.assertNotIn('**', result['snippet'])
        self.assertNotIn('[', result['snippet'])

    def test_preset_field_included(self):
        result = generate_snippet('테스트', preset='og')
        self.assertEqual(result['preset'], 'og')

    def test_invalid_preset_fallback(self):
        result = generate_snippet('테스트', preset='nonexistent')
        self.assertIn('snippet', result)


class TestGenerateMultiSnippets(unittest.TestCase):

    def test_empty_content(self):
        result = generate_multi_snippets('')
        self.assertEqual(result['total'], 0)

    def test_all_presets_generated(self):
        text = '충분히 긴 콘텐츠입니다. ' * 30
        result = generate_multi_snippets(text)
        self.assertEqual(result['total'], len(SNIPPET_PRESETS))
        for preset_id in SNIPPET_PRESETS:
            self.assertIn(preset_id, result['snippets'])

    def test_each_snippet_has_structure(self):
        text = '테스트 콘텐츠입니다. ' * 20
        result = generate_multi_snippets(text)
        for preset_id, snippet in result['snippets'].items():
            self.assertIn('snippet', snippet)
            self.assertIn('char_count', snippet)
            self.assertIn('max_chars', snippet)


class TestCleanMarkdown(unittest.TestCase):

    def test_removes_headings(self):
        result = _clean_markdown('# 제목\n본문')
        self.assertNotIn('#', result)
        self.assertIn('본문', result)

    def test_removes_bold(self):
        result = _clean_markdown('**볼드** 텍스트')
        self.assertNotIn('**', result)
        self.assertIn('볼드', result)

    def test_removes_images(self):
        result = _clean_markdown('![alt](img.png) 텍스트')
        self.assertNotIn('![', result)

    def test_preserves_link_text(self):
        result = _clean_markdown('[링크텍스트](url)')
        self.assertIn('링크텍스트', result)
        self.assertNotIn('url', result)

    def test_empty(self):
        self.assertEqual(_clean_markdown(''), '')


class TestTruncateAtSentence(unittest.TestCase):

    def test_short_text(self):
        result = _truncate_at_sentence('짧은 텍스트', 100)
        self.assertEqual(result, '짧은 텍스트')

    def test_truncates_at_sentence_boundary(self):
        text = '첫 번째 문장입니다. 두 번째 문장은 매우 길어서 잘려야 합니다.'
        result = _truncate_at_sentence(text, 25)
        self.assertLessEqual(len(result), 30)  # 약간의 여유

    def test_empty(self):
        self.assertEqual(_truncate_at_sentence('', 100), '')


class TestGetSnippetPresets(unittest.TestCase):

    def test_returns_list(self):
        presets = get_snippet_presets()
        self.assertIsInstance(presets, list)
        self.assertGreater(len(presets), 0)

    def test_preset_structure(self):
        presets = get_snippet_presets()
        for p in presets:
            self.assertIn('id', p)
            self.assertIn('label', p)
            self.assertIn('max_chars', p)


if __name__ == '__main__':
    unittest.main()
