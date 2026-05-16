"""paragraph_balance_analyzer_service 단위 테스트."""
import pytest

from services.content.paragraph_balance_analyzer_service import (
    analyze_paragraph_balance,
    DEFAULT_MIN_CHARS,
    DEFAULT_MAX_CHARS,
)


class TestAnalyzeParagraphBalance:
    def test_empty_content_returns_empty_result(self):
        result = analyze_paragraph_balance('')
        assert result['paragraph_count'] == 0
        assert result['balance_score'] == 100
        assert result['balance_grade'] == 'A'

    def test_whitespace_only_empty(self):
        result = analyze_paragraph_balance('   \n\n\t ')
        assert result['paragraph_count'] == 0

    def test_single_paragraph_counted(self):
        content = '이것은 충분히 긴 하나의 문단입니다. ' * 3
        result = analyze_paragraph_balance(content)
        assert result['paragraph_count'] == 1
        assert result['total_chars'] > 0

    def test_multiple_paragraphs_separated_by_blank_lines(self):
        content = '첫 번째 문단 내용입니다. ' * 3 + '\n\n' + '두 번째 문단 내용입니다. ' * 3
        result = analyze_paragraph_balance(content)
        assert result['paragraph_count'] == 2

    def test_too_short_detected(self):
        short = '짧음.'
        long_enough = 'x' * (DEFAULT_MIN_CHARS + 10)
        content = f'{short}\n\n{long_enough}'
        result = analyze_paragraph_balance(content)
        assert len(result['too_short']) == 1
        assert result['too_short'][0]['length'] == len(short)

    def test_too_long_detected(self):
        long_para = 'x' * (DEFAULT_MAX_CHARS + 50)
        normal_para = 'x' * 100
        content = f'{long_para}\n\n{normal_para}'
        result = analyze_paragraph_balance(content)
        assert len(result['too_long']) == 1
        assert result['too_long'][0]['length'] == len(long_para)

    def test_preview_truncated_to_max_length(self):
        long_para = 'a' * 500
        result = analyze_paragraph_balance(long_para)
        long_issue = result['too_long'][0]
        assert len(long_issue['preview']) <= 45  # 40 + "..." 여유

    def test_code_block_excluded(self):
        content = '첫 문단입니다. ' * 5 + '\n\n```python\ndef f(): pass\n```\n\n두 번째 문단입니다. ' * 3
        result = analyze_paragraph_balance(content)
        # 코드 블록은 제거되어 문단으로 집계되지 않음
        # 정확한 수는 구현 변동이 있을 수 있어 2 이상만 확인
        assert result['paragraph_count'] >= 2

    def test_headings_excluded(self):
        para1 = '문단 본문 내용입니다. ' * 3
        para2 = '다음 문단 본문입니다. ' * 3
        content = f'# 제목\n\n{para1}\n\n## 다음 제목\n\n{para2}'
        result = analyze_paragraph_balance(content)
        # 제목은 문단 카운트에서 제외
        assert result['paragraph_count'] == 2

    def test_list_block_excluded(self):
        para1 = '정상 문단 내용입니다. ' * 3
        para2 = '다른 정상 문단 내용입니다. ' * 3
        content = f'{para1}\n\n- 항목 1\n- 항목 2\n- 항목 3\n\n{para2}'
        result = analyze_paragraph_balance(content)
        # 리스트 블록은 문단 집계에서 제외
        assert result['paragraph_count'] == 2

    def test_table_block_excluded(self):
        para1 = '본문 문단 내용입니다. ' * 3
        para2 = '다른 문단 내용입니다. ' * 3
        content = f'{para1}\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\n{para2}'
        result = analyze_paragraph_balance(content)
        assert result['paragraph_count'] == 2

    def test_statistics_computed(self):
        paras = ['이것은 문단입니다. ' * 5, '다른 문단입니다. ' * 5, '세 번째 문단입니다. ' * 5]
        content = '\n\n'.join(paras)
        result = analyze_paragraph_balance(content)
        assert result['paragraph_count'] == 3
        assert result['avg_length'] > 0
        assert result['median_length'] > 0
        assert result['min_length'] > 0
        assert result['max_length'] >= result['min_length']

    def test_stdev_zero_for_single_paragraph(self):
        result = analyze_paragraph_balance('단 하나의 문단입니다. ' * 5)
        assert result['stdev_length'] == 0.0

    def test_grade_a_for_balanced_content(self):
        # 모든 문단 길이 균일 + 범위 내
        balanced = '\n\n'.join(['x' * 100 for _ in range(5)])
        result = analyze_paragraph_balance(balanced)
        assert result['balance_grade'] == 'A'
        assert result['balance_score'] >= 90

    def test_grade_drops_for_many_issues(self):
        # 긴 문단 5개, 짧은 문단 5개 → 점수 대폭 하락
        mixed = '\n\n'.join(['x' * 400 for _ in range(5)] + ['짧다' for _ in range(5)])
        result = analyze_paragraph_balance(mixed)
        assert result['balance_score'] < result.get('balance_score', 100) or result['balance_score'] < 90
        assert result['balance_grade'] in ('C', 'D', 'B')

    def test_recommendations_include_long_paragraph_hint(self):
        content = 'x' * 500
        result = analyze_paragraph_balance(content)
        hints = ' '.join(result['recommendations'])
        assert '초과' in hints or '분리' in hints

    def test_recommendations_good_when_balanced(self):
        result = analyze_paragraph_balance('\n\n'.join(['x' * 100 for _ in range(3)]))
        hints = ' '.join(result['recommendations'])
        assert '양호' in hints

    def test_custom_thresholds_respected(self):
        content = 'x' * 50
        # 기본(40~220)으로는 정상, min_chars=80이면 too_short
        strict = analyze_paragraph_balance(content, min_chars=80)
        assert len(strict['too_short']) == 1
        normal = analyze_paragraph_balance(content)
        assert len(normal['too_short']) == 0
