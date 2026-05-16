"""heading_hierarchy_validator_service 단위 테스트."""
import pytest

from services.content.heading_hierarchy_validator_service import (
    validate_heading_hierarchy,
    get_outline_markdown,
)


class TestValidateHeadingHierarchy:
    def test_empty_content_is_valid(self):
        result = validate_heading_hierarchy('')
        assert result['valid'] is True
        assert result['score'] == 100
        assert result['heading_count'] == 0
        assert result['issues'] == []

    def test_no_headings_is_valid(self):
        result = validate_heading_hierarchy('이것은 본문 문단입니다.\n\n여러 문단이 있습니다.')
        assert result['valid'] is True
        assert result['heading_count'] == 0

    def test_well_formed_hierarchy_passes(self):
        content = '# 메인 제목\n\n## 소제목 하나\n\n### 세부 내용\n\n## 소제목 둘'
        result = validate_heading_hierarchy(content)
        assert result['valid'] is True
        assert result['score'] == 100
        assert result['heading_count'] == 4
        assert result['by_level']['h1'] == 1
        assert result['by_level']['h2'] == 2
        assert result['by_level']['h3'] == 1

    def test_detects_multiple_h1(self):
        content = '# 제목 하나 텍스트\n\n## 소제목\n\n# 제목 둘 텍스트'
        result = validate_heading_hierarchy(content)
        assert result['valid'] is False  # error
        issue_types = [i['type'] for i in result['issues']]
        assert 'multiple_h1' in issue_types
        multiple_h1 = [i for i in result['issues'] if i['type'] == 'multiple_h1']
        assert all(i['severity'] == 'error' for i in multiple_h1)

    def test_detects_level_jump(self):
        content = '# 메인 제목\n\n### 세부 내용 (H2 건너뜀)'
        result = validate_heading_hierarchy(content)
        jump_issues = [i for i in result['issues'] if i['type'] == 'level_jump']
        assert len(jump_issues) == 1
        assert jump_issues[0]['level'] == 3
        assert jump_issues[0]['severity'] == 'warning'

    def test_detects_missing_h1(self):
        content = '## 소제목으로 시작\n\n### 세부'
        result = validate_heading_hierarchy(content)
        missing = [i for i in result['issues'] if i['type'] == 'missing_h1']
        assert len(missing) == 1

    def test_detects_empty_heading(self):
        content = '# \n\n## 소제목 내용'
        result = validate_heading_hierarchy(content)
        empty = [i for i in result['issues'] if i['type'] == 'empty_heading']
        assert len(empty) == 1
        assert empty[0]['severity'] == 'error'
        assert result['valid'] is False

    def test_detects_too_short_title(self):
        content = '# 짧\n\n## 정상적인 제목'
        result = validate_heading_hierarchy(content, min_title_length=3)
        short = [i for i in result['issues'] if i['type'] == 'too_short']
        assert len(short) >= 1

    def test_detects_too_long_title(self):
        long_title = '정' * 90
        content = f'# {long_title}\n\n## 정상 제목'
        result = validate_heading_hierarchy(content, max_title_length=80)
        long_issues = [i for i in result['issues'] if i['type'] == 'too_long']
        assert len(long_issues) == 1

    def test_detects_duplicate_headings(self):
        content = '# 메인 제목\n\n## 같은 이름\n\n### 내부 항목\n\n## 같은 이름'
        result = validate_heading_hierarchy(content)
        dups = [i for i in result['issues'] if i['type'] == 'duplicate']
        assert len(dups) == 1

    def test_ignores_headings_inside_code_block(self):
        content = '# 진짜 제목 텍스트\n\n```\n# 이것은 코드 주석\n## 이것도 코드\n```\n\n## 다음 제목 텍스트'
        result = validate_heading_hierarchy(content)
        assert result['heading_count'] == 2  # 코드 블록 안은 제외

    def test_outline_returns_full_list(self):
        content = '# 메인 제목\n\n## 소제목 A\n\n## 소제목 B'
        result = validate_heading_hierarchy(content)
        assert len(result['outline']) == 3
        assert result['outline'][0]['level'] == 1
        assert '메인 제목' == result['outline'][0]['text']

    def test_score_decreases_with_errors(self):
        bad = '# One\n\n# Two\n\n### Jump'  # multiple_h1 + level_jump + short titles
        result = validate_heading_hierarchy(bad, min_title_length=5)
        assert result['score'] < 100
        assert result['valid'] is False

    def test_score_only_warnings_stays_valid(self):
        content = '## H2로 시작\n\n### 건너뛰지 않음'
        result = validate_heading_hierarchy(content)
        # error 없음, valid=True
        assert result['valid'] is True
        assert result['score'] < 100  # 경고로 인한 감점

    def test_h1_limit_configurable(self):
        content = '# 첫\n\n# 둘\n\n# 셋'
        result = validate_heading_hierarchy(content, max_h1=3)
        multiple = [i for i in result['issues'] if i['type'] == 'multiple_h1']
        assert len(multiple) == 0


class TestGetOutlineMarkdown:
    def test_empty_content_returns_empty_string(self):
        assert get_outline_markdown('') == ''

    def test_indentation_matches_level(self):
        content = '# 메인 제목\n\n## 소제목\n\n### 세부 항목'
        outline = get_outline_markdown(content)
        lines = outline.split('\n')
        assert lines[0] == '- 메인 제목'
        assert lines[1] == '  - 소제목'
        assert lines[2] == '    - 세부 항목'

    def test_starts_from_lowest_level_found(self):
        content = '## 시작\n\n### 세부'
        outline = get_outline_markdown(content)
        # 최소 레벨이 H2면 H2를 기준(indent 0)으로 삼음
        assert outline.startswith('- 시작')
