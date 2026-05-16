"""footnote_service 단위 테스트."""
import pytest

from services.content.footnote_service import (
    parse_footnotes,
    validate_footnotes,
    render_footnotes_html,
    renumber_footnotes,
)


class TestParseFootnotes:
    def test_empty_content(self):
        result = parse_footnotes('')
        assert result['references'] == []
        assert result['definitions'] == {}

    def test_simple_reference_and_definition(self):
        content = '본문에 각주[^1]가 있다.\n\n[^1]: 첫 번째 각주 설명'
        result = parse_footnotes(content)
        assert len(result['references']) == 1
        assert result['references'][0]['id'] == '1'
        assert result['definitions'] == {'1': '첫 번째 각주 설명'}

    def test_multiple_references_same_id(self):
        content = '첫 참조[^a]와 두번째 참조[^a]가 같다.\n\n[^a]: 설명'
        result = parse_footnotes(content)
        assert len(result['references']) == 2
        assert all(r['id'] == 'a' for r in result['references'])

    def test_reference_without_definition(self):
        content = '본문[^orphan]\n'
        result = parse_footnotes(content)
        assert result['references'][0]['id'] == 'orphan'
        assert 'orphan' not in result['definitions']

    def test_definition_without_reference(self):
        content = '일반 본문\n\n[^unused]: 사용되지 않은 정의'
        result = parse_footnotes(content)
        assert result['definitions'] == {'unused': '사용되지 않은 정의'}
        assert result['references'] == []

    def test_definition_not_mistaken_as_reference(self):
        content = '본문[^1]\n\n[^1]: 실제 정의'
        result = parse_footnotes(content)
        # 정의 라인의 [^1]은 참조로 잡히면 안 됨
        assert len(result['references']) == 1

    def test_definition_order_preserved(self):
        content = '본문\n\n[^b]: 두 번째\n\n[^a]: 첫 번째\n\n[^c]: 세 번째'
        result = parse_footnotes(content)
        assert result['definition_order'] == ['b', 'a', 'c']


class TestValidateFootnotes:
    def test_valid_content(self):
        content = '본문[^1]\n\n[^1]: 정의'
        result = validate_footnotes(content)
        assert result['valid'] is True
        assert result['reference_count'] == 1
        assert result['definition_count'] == 1

    def test_detects_missing_definition(self):
        content = '본문[^missing]'
        result = validate_footnotes(content)
        assert result['valid'] is False
        issue_types = [i['type'] for i in result['issues']]
        assert 'missing_definition' in issue_types

    def test_detects_unused_definition(self):
        content = '본문 내용\n\n[^unused]: 설명'
        result = validate_footnotes(content)
        unused = [i for i in result['issues'] if i['type'] == 'unused_definition']
        assert len(unused) == 1
        assert unused[0]['severity'] == 'warning'
        # warning 만 있으므로 valid=True
        assert result['valid'] is True

    def test_detects_duplicate_definition(self):
        content = '본문[^1]\n\n[^1]: 첫 정의\n\n[^1]: 중복 정의'
        result = validate_footnotes(content)
        dup = [i for i in result['issues'] if i['type'] == 'duplicate_definition']
        assert len(dup) == 1
        assert result['valid'] is False

    def test_detects_invalid_id(self):
        content = '본문[^잘못된 ID]\n\n[^잘못된 ID]: 내용'
        result = validate_footnotes(content)
        invalid = [i for i in result['issues'] if i['type'] == 'invalid_id']
        assert len(invalid) >= 1


class TestRenderFootnotesHtml:
    def test_empty_content_no_footnotes_section(self):
        result = render_footnotes_html('일반 본문만 있음.')
        assert result['count'] == 0
        assert result['footnotes_html'] == ''

    def test_reference_rendered_as_sup(self):
        content = '본문[^1]에 각주.\n\n[^1]: 설명'
        result = render_footnotes_html(content)
        assert '<sup class="footnote-ref">' in result['body_html']
        assert '>1</a>' in result['body_html']

    def test_footnotes_section_generated(self):
        content = '본문[^1]\n\n[^1]: 첫 번째 설명'
        result = render_footnotes_html(content)
        assert '<ol class="footnotes">' in result['footnotes_html']
        assert '첫 번째 설명' in result['footnotes_html']

    def test_definition_lines_removed_from_body(self):
        content = '본문[^a]\n\n[^a]: 숨겨져야 함'
        result = render_footnotes_html(content)
        assert '숨겨져야 함' not in result['body_html']

    def test_orphan_reference_unchanged(self):
        content = '본문[^orphan]만'
        result = render_footnotes_html(content)
        # 정의 없는 참조는 원문 유지
        assert '[^orphan]' in result['body_html']

    def test_numbering_by_order_of_appearance(self):
        content = '참조[^b] 참조[^a]\n\n[^a]: A\n\n[^b]: B'
        result = render_footnotes_html(content)
        # b가 먼저 등장 → 1번
        assert '>1</a>' in result['body_html']

    def test_html_escape_applied(self):
        content = '본문[^x]\n\n[^x]: <script>alert(1)</script>'
        result = render_footnotes_html(content)
        assert '<script>' not in result['footnotes_html']
        assert '&lt;script&gt;' in result['footnotes_html']

    def test_body_html_escapes_raw_html(self):
        content = '본문에 <script>evil()</script>가 포함.[^1]\n\n[^1]: 정의'
        result = render_footnotes_html(content)
        # 원시 HTML은 이스케이프되어야 함 (XSS 방지)
        assert '<script>' not in result['body_html']
        assert '&lt;script&gt;' in result['body_html']
        # 각주 참조 태그만 온전히 살아있어야 함
        assert '<sup class="footnote-ref">' in result['body_html']

    def test_multiline_definition_parsed(self):
        content = (
            '본문[^1]에 각주\n\n'
            '[^1]: 첫 줄 내용\n'
            '    계속되는 들여쓴 내용\n'
            '    또 다른 줄\n'
        )
        result = parse_footnotes(content)
        assert '1' in result['definitions']
        body_def = result['definitions']['1']
        assert '첫 줄 내용' in body_def
        assert '계속되는 들여쓴 내용' in body_def


class TestRenumberFootnotes:
    def test_empty_content(self):
        result = renumber_footnotes('')
        assert result['content'] == ''
        assert result['mapping'] == {}

    def test_sequential_renumbering(self):
        content = '참조[^alpha] 참조[^beta]\n\n[^alpha]: A\n\n[^beta]: B'
        result = renumber_footnotes(content)
        assert '[^1]' in result['content']
        assert '[^2]' in result['content']
        assert result['mapping'] == {'alpha': '1', 'beta': '2'}

    def test_orphan_reference_skipped(self):
        content = '참조[^x]\n본문만'  # 정의 없음
        result = renumber_footnotes(content)
        assert result['mapping'] == {}
        assert '[^x]' in result['content']

    def test_definitions_renumbered_too(self):
        content = '참조[^one]\n\n[^one]: 내용'
        result = renumber_footnotes(content)
        assert '[^1]: 내용' in result['content']
        assert '[^one]' not in result['content']
