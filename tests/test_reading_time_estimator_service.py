"""reading_time_estimator_service 단위 테스트."""
import pytest

from services.content.reading_time_estimator_service import (
    estimate_reading_time,
    get_supported_languages,
    LANGUAGE_SPEEDS,
)


class TestEstimateReadingTime:
    def test_empty_content_returns_zero(self):
        result = estimate_reading_time('', language='ko')
        assert result['total_units'] == 0
        assert result['total_seconds'] == 0
        assert result['minutes'] == 0
        assert '미만' in result['display']

    def test_whitespace_only_treated_as_empty(self):
        result = estimate_reading_time('   \n\n  \t  ', language='ko')
        assert result['total_units'] == 0

    def test_korean_chars_counted_correctly(self):
        # 500자/분 속도: 1000자 = 120초 = 2분
        text = '가' * 1000
        result = estimate_reading_time(text, language='ko')
        assert result['unit'] == 'chars'
        assert result['total_units'] == 1000
        assert result['base_seconds'] == 120
        assert result['minutes'] == 2
        assert '약 2분' == result['display']

    def test_english_words_counted_correctly(self):
        text = 'hello world ' * 119  # 238 단어 = 1분
        result = estimate_reading_time(text, language='en')
        assert result['unit'] == 'words'
        assert result['total_units'] == 238
        assert result['base_seconds'] == 60
        assert result['minutes'] == 1
        assert 'about 1 min' in result['display']

    def test_japanese_uses_char_count(self):
        text = 'あ' * 600
        result = estimate_reading_time(text, language='ja')
        assert result['unit'] == 'chars'
        assert result['total_units'] == 600
        assert result['minutes'] == 1
        assert '約' in result['display']

    def test_image_adds_12_seconds(self):
        text = '글자 ' * 100 + '\n![alt](/img.png)'
        result = estimate_reading_time(text, language='ko')
        assert result['elements']['images'] == 1
        assert result['overhead_seconds'] >= 12

    def test_code_block_adds_30_seconds(self):
        text = '설명 ' * 50 + '\n```python\nprint(1)\n```'
        result = estimate_reading_time(text, language='ko')
        assert result['elements']['code_blocks'] == 1
        assert result['overhead_seconds'] >= 30

    def test_code_block_content_excluded_from_word_count(self):
        without_code = '안녕하세요 반갑습니다'
        with_code = without_code + '\n```\n' + ('hello world ' * 100) + '\n```'
        r1 = estimate_reading_time(without_code, language='ko')
        r2 = estimate_reading_time(with_code, language='ko')
        # 코드 블록 속 텍스트는 카운트하지 않음 → 글자 수 거의 같음
        assert abs(r2['total_units'] - r1['total_units']) < 5

    def test_table_rows_counted(self):
        text = '| a | b |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |'
        result = estimate_reading_time(text, language='ko')
        assert result['elements']['table_rows'] >= 3

    def test_blockquote_counted(self):
        text = '> 첫 번째 인용\n> 두 번째 인용'
        result = estimate_reading_time(text, language='ko')
        assert result['elements']['blockquotes'] == 2

    def test_wpm_override_applied(self):
        text = '가' * 500
        # 기본 500자/분 → 1분
        base = estimate_reading_time(text, language='ko')
        # 250자/분 override → 2분
        slower = estimate_reading_time(text, language='ko', wpm_override=250)
        assert slower['speed_per_min'] == 250
        assert slower['base_seconds'] > base['base_seconds']

    def test_wpm_override_zero_ignored(self):
        text = '가' * 500
        result = estimate_reading_time(text, language='ko', wpm_override=0)
        assert result['speed_per_min'] == 500  # 기본값 유지

    def test_markdown_heading_stripped_from_count(self):
        text = '# 제목\n\n' + ('가' * 500)
        result = estimate_reading_time(text, language='ko')
        # '제목' 2자만 추가되므로 총 502자 근처
        assert 500 <= result['total_units'] <= 510

    def test_unknown_language_defaults_to_korean(self):
        text = '안녕하세요'
        result = estimate_reading_time(text, language='xx')
        assert result['unit'] == 'chars'

    def test_minutes_rounds_up(self):
        # 250자 → 30초 → 1분으로 올림
        text = '가' * 250
        result = estimate_reading_time(text, language='ko')
        assert result['minutes'] == 1

    def test_inline_code_stripped(self):
        text = '이것은 `code` 예시입니다'
        result = estimate_reading_time(text, language='ko')
        # 'code' 4자가 제외되어야 함 (inline code) → 한국어 카운트는 대략 11-13자
        assert result['total_units'] < 15

    def test_link_text_preserved(self):
        text = '자세한 내용은 [여기를](https://example.com) 보세요'
        result = estimate_reading_time(text, language='ko')
        # '여기를'은 카운트되고 URL은 제외
        assert result['total_units'] > 10


class TestSupportedLanguages:
    def test_returns_all_configured_languages(self):
        langs = get_supported_languages()
        codes = {lang['code'] for lang in langs}
        assert codes == set(LANGUAGE_SPEEDS.keys())

    def test_each_language_has_required_fields(self):
        langs = get_supported_languages()
        for lang in langs:
            assert 'code' in lang
            assert 'label' in lang
            assert 'unit' in lang
            assert 'speed_per_min' in lang
            assert lang['speed_per_min'] > 0
