"""image_alt_text_service 단위 테스트."""
import pytest

from services.content.image_alt_text_service import (
    audit_image_alt_texts,
    suggest_alt_from_url,
)


class TestAuditImageAltTexts:
    def test_empty_content(self):
        result = audit_image_alt_texts('')
        assert result['total'] == 0
        assert result['issues'] == []
        assert result['score'] == 100

    def test_no_images(self):
        result = audit_image_alt_texts('이미지가 전혀 없는 일반 텍스트')
        assert result['total'] == 0

    def test_missing_alt_detected(self):
        content = '![](https://example.com/photo.png)'
        result = audit_image_alt_texts(content)
        assert result['total'] == 1
        missing = [i for i in result['issues'] if i['type'] == 'missing_alt']
        assert len(missing) == 1
        assert missing[0]['severity'] == 'error'

    def test_proper_alt_passes(self):
        content = '![강아지가 풀밭을 뛰어노는 모습을 담은 사진](/dog.png)'
        result = audit_image_alt_texts(content)
        assert result['issues'] == []
        assert result['score'] == 100

    def test_too_short_alt(self):
        content = '![X](/x.png)'
        result = audit_image_alt_texts(content)
        short = [i for i in result['issues'] if i['type'] == 'too_short']
        assert len(short) == 1

    def test_too_long_alt(self):
        long_alt = '가' * 150
        content = f'![{long_alt}](/photo.png)'
        result = audit_image_alt_texts(content)
        long_issues = [i for i in result['issues'] if i['type'] == 'too_long']
        assert len(long_issues) == 1

    def test_filename_as_alt_detected(self):
        content = '![photo.jpg](/photo.jpg)'
        result = audit_image_alt_texts(content)
        fn = [i for i in result['issues'] if i['type'] == 'filename_as_alt']
        assert len(fn) == 1
        assert fn[0]['severity'] == 'error'

    def test_redundant_prefix_detected(self):
        content = '![Image of a cat playing](/cat.png)'
        result = audit_image_alt_texts(content)
        red = [i for i in result['issues'] if i['type'] == 'redundant_prefix']
        assert len(red) == 1

    def test_duplicate_alt_detected(self):
        content = (
            '![제품 사진](/a.png) 첫 번째\n\n'
            '![제품 사진](/b.png) 두 번째'
        )
        result = audit_image_alt_texts(content)
        dup = [i for i in result['issues'] if i['type'] == 'duplicate_alt']
        assert len(dup) == 1

    def test_html_img_with_alt(self):
        content = '<img src="/a.png" alt="설명이 충분한 이미지입니다" />'
        result = audit_image_alt_texts(content)
        assert result['total'] == 1
        assert result['issues'] == []

    def test_html_img_decorative_marked(self):
        content = '<img src="/deco.png" alt="" aria-hidden="true" />'
        result = audit_image_alt_texts(content)
        assert result['decorative_count'] == 1
        assert result['issues'] == []

    def test_html_img_decorative_text(self):
        content = '<img src="/deco.png" alt="decorative" />'
        result = audit_image_alt_texts(content)
        assert result['decorative_count'] == 1

    def test_html_img_missing_alt_attr(self):
        content = '<img src="/a.png" />'
        result = audit_image_alt_texts(content)
        missing = [i for i in result['issues'] if i['type'] == 'missing_alt']
        assert len(missing) == 1

    def test_score_reflects_issue_count(self):
        # 5개 이미지 중 3개 오류
        content = (
            '![](/a.png) ![](/b.png) ![](/c.png)'
            '![정상 설명 텍스트](/d.png) ![또 다른 정상 설명 텍스트](/e.png)'
        )
        result = audit_image_alt_texts(content)
        assert result['score'] < 100
        assert result['total'] == 5

    def test_mixed_md_and_html(self):
        content = '![MD alt text ok](/a.png)\n<img src="/b.png" alt="HTML alt ok" />'
        result = audit_image_alt_texts(content)
        assert result['total'] == 2
        assert result['issues'] == []


class TestSuggestAltFromUrl:
    def test_empty_returns_empty(self):
        assert suggest_alt_from_url('') == ''

    def test_strip_extension(self):
        assert 'photo' in suggest_alt_from_url('https://example.com/photo.png')

    def test_replace_hyphens_underscores(self):
        result = suggest_alt_from_url('/images/dog-in-park.jpg')
        assert 'dog in park' in result

    def test_strip_long_digit_sequences(self):
        result = suggest_alt_from_url('/IMG_20230615_sample.jpg')
        # 긴 숫자 시퀀스는 제거되고 'IMG sample' 정도만 남음
        assert 'sample' in result.lower()

    def test_handle_query_string(self):
        result = suggest_alt_from_url('https://cdn.com/photo.png?v=123&size=large')
        assert 'photo' in result

    def test_handle_fragment(self):
        result = suggest_alt_from_url('/image.png#anchor')
        assert 'image' in result
