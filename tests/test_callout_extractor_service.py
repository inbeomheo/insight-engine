"""callout_extractor_service 단위 테스트."""
import pytest

from services.content.callout_extractor_service import (
    extract_callouts,
    render_callouts_html,
    suggest_callout_for_paragraph,
)


class TestExtractCallouts:
    def test_empty_content(self):
        result = extract_callouts('')
        assert result['callouts'] == []
        assert result['count'] == 0

    def test_github_style_note(self):
        content = '> [!NOTE]\n> 간단한 안내입니다.'
        result = extract_callouts(content)
        assert result['count'] == 1
        c = result['callouts'][0]
        assert c['type'] == 'note'
        assert c['style'] == 'github'
        assert '간단한 안내' in c['body']

    def test_github_style_with_title(self):
        content = '> [!WARNING] 꼭 읽어주세요\n> 본문 내용'
        result = extract_callouts(content)
        assert result['callouts'][0]['type'] == 'warning'
        assert '꼭 읽어주세요' in result['callouts'][0]['title']

    def test_docusaurus_style(self):
        content = ':::tip 프로 팁\n여기 본문이 들어갑니다.\n:::'
        result = extract_callouts(content)
        assert result['count'] == 1
        c = result['callouts'][0]
        assert c['type'] == 'tip'
        assert c['style'] == 'docusaurus'
        assert '여기 본문' in c['body']

    def test_docusaurus_without_title(self):
        content = ':::caution\n경고 내용입니다.\n:::'
        result = extract_callouts(content)
        assert result['callouts'][0]['type'] == 'caution'
        assert result['callouts'][0]['title'] == ''

    def test_bold_header_style(self):
        content = '> **Note:** 이것은 노트입니다.\n> 계속되는 본문.'
        result = extract_callouts(content)
        assert result['count'] == 1
        c = result['callouts'][0]
        assert c['type'] == 'note'
        assert c['style'] == 'bold'
        assert '이것은 노트' in c['body']

    def test_multiple_callouts(self):
        content = (
            '> [!NOTE]\n> 첫 번째 노트\n\n'
            ':::tip\n두 번째 팁\n:::\n\n'
            '> **Warning:** 세 번째 경고'
        )
        result = extract_callouts(content)
        assert result['count'] == 3
        types = {c['type'] for c in result['callouts']}
        assert types == {'note', 'tip', 'warning'}

    def test_by_type_aggregation(self):
        content = '> [!NOTE]\n> A\n\n> [!NOTE]\n> B\n\n:::tip\nC\n:::'
        result = extract_callouts(content)
        assert result['by_type']['note'] == 2
        assert result['by_type']['tip'] == 1

    def test_code_block_ignored(self):
        content = (
            '```\n> [!NOTE]\n> 이것은 코드 안이라 무시\n```\n\n'
            '> [!TIP]\n> 이것만 진짜 콜아웃'
        )
        result = extract_callouts(content)
        assert result['count'] == 1
        assert result['callouts'][0]['type'] == 'tip'

    def test_line_numbers_tracked(self):
        content = '\n\n\n> [!NOTE]\n> 네 번째 라인에서 시작'
        result = extract_callouts(content)
        assert result['callouts'][0]['line'] == 4

    def test_unknown_bold_type_defaults_to_note(self):
        content = '> **Random:** 낯선 헤더'
        result = extract_callouts(content)
        # 알 수 없는 타입은 note로 fallback
        assert result['callouts'][0]['type'] == 'note'


class TestRenderCalloutsHtml:
    def test_empty_content(self):
        result = render_callouts_html('')
        assert result['count'] == 0
        assert result['blocks_html'] == []

    def test_github_style_rendered(self):
        content = '> [!WARNING] 경고 제목\n> 경고 본문'
        result = render_callouts_html(content)
        html = result['blocks_html'][0]
        assert 'callout-warning' in html
        assert '경고 제목' in html
        assert '경고 본문' in html

    def test_xss_escaped_in_body(self):
        content = '> [!NOTE]\n> <script>alert(1)</script>'
        result = render_callouts_html(content)
        html = result['blocks_html'][0]
        assert '<script>' not in html
        assert '&lt;script&gt;' in html

    def test_xss_escaped_in_title(self):
        content = '> [!TIP] <img onerror="x">\n> 본문'
        result = render_callouts_html(content)
        html = result['blocks_html'][0]
        assert '<img' not in html
        assert '&lt;img' in html

    def test_type_escaped_in_class(self):
        # 이상한 type이 들어와도 class 속성이 깨지지 않아야 함 (이론적 케이스)
        content = ':::tip\n본문\n:::'
        result = render_callouts_html(content)
        assert 'callout-tip' in result['blocks_html'][0]


class TestSuggestCallout:
    def test_none_for_empty(self):
        assert suggest_callout_for_paragraph('') is None

    def test_detects_note_keyword(self):
        assert suggest_callout_for_paragraph('참고: 이 부분은 중요') == 'note'

    def test_detects_warning(self):
        assert suggest_callout_for_paragraph('경고! 데이터가 삭제됩니다') == 'warning'

    def test_detects_tip(self):
        assert suggest_callout_for_paragraph('Tip: faster is better') == 'tip'

    def test_no_match_returns_none(self):
        assert suggest_callout_for_paragraph('일반 문단 내용입니다') is None
