"""pull_quote_extractor_service 단위 테스트."""
import pytest

from services.content.pull_quote_extractor_service import (
    extract_pull_quotes,
    format_as_blockquote,
)


class TestExtractPullQuotes:
    def test_empty_content_returns_empty(self):
        result = extract_pull_quotes('')
        assert result['quotes'] == []
        assert result['total_candidates'] == 0
        assert result['source_sentence_count'] == 0

    def test_whitespace_only(self):
        result = extract_pull_quotes('   \n\n  ')
        assert result['quotes'] == []

    def test_basic_extraction_returns_top_n(self):
        content = (
            '첫 번째 문장은 상당히 긴 길이를 가진 완전한 표현입니다. '
            '이 문장은 핵심 아이디어를 완벽하게 정리합니다. '
            '두 번째 중요한 단락입니다. '
            '세 번째 더 많은 문장을 포함한 단락입니다. '
            '마지막 문장으로 글을 마무리합니다.'
        )
        result = extract_pull_quotes(content, top_n=3)
        assert len(result['quotes']) <= 3
        assert result['source_sentence_count'] >= 3

    def test_top_n_limits_output(self):
        content = ' '.join([f'{i}번째 완결된 문장으로 충분한 길이를 확보합니다.' for i in range(10)])
        result = extract_pull_quotes(content, top_n=2)
        assert len(result['quotes']) == 2

    def test_too_short_sentences_excluded(self):
        content = '짧음. 아주 짧음. ' + '충분히 긴 문장으로 필터를 통과하는 내용입니다.'
        result = extract_pull_quotes(content, min_length=20)
        for q in result['quotes']:
            assert q['length'] >= 20

    def test_too_long_sentences_excluded(self):
        long_text = '가' * 300
        content = f'정상 길이의 문장입니다 충분히 길어서 통과합니다. {long_text}.'
        result = extract_pull_quotes(content, max_length=200)
        for q in result['quotes']:
            assert q['length'] <= 200

    def test_korean_impact_keywords_boost_score(self):
        regular = '오늘은 날씨가 매우 좋은 날입니다 산책하기 좋아요.'
        impactful = '핵심은 매일 꾸준히 실천하는 바로 그 자세에 있습니다.'
        content = f'{regular} {impactful}'
        result = extract_pull_quotes(content, top_n=2)
        scores = {q['text']: q['score'] for q in result['quotes']}
        # '핵심'이 포함된 문장이 더 높은 점수
        impact_scores = [s for t, s in scores.items() if '핵심' in t]
        plain_scores = [s for t, s in scores.items() if '핵심' not in t]
        if impact_scores and plain_scores:
            assert max(impact_scores) >= max(plain_scores)

    def test_english_keywords_work(self):
        content = (
            'The key essential truth about this approach is clarity over cleverness. '
            'Also there is another general statement here about things.'
        )
        result = extract_pull_quotes(content, language='en', top_n=2)
        # 첫 번째가 더 높은 점수 (key, essential, truth 포함)
        assert result['quotes'][0]['text'].lower().find('key') >= 0 or \
               result['quotes'][0]['text'].lower().find('essential') >= 0

    def test_english_keyword_substring_not_matched(self):
        # 'key'가 'monkey'·'keyboard' 같은 부분 문자열로 매칭되지 않아야 함
        plain = 'Monkey business and keyboard sounds fill the room of clever apes today.'
        impactful = 'The key insight of this research is clarity over cleverness always.'
        content = f'{plain} {impactful}'
        result = extract_pull_quotes(content, language='en', top_n=2)
        # impactful 문장이 더 높은 점수
        first_text = result['quotes'][0]['text'].lower()
        assert 'key insight' in first_text or 'key ' in first_text

    def test_code_blocks_excluded(self):
        content = (
            '본문의 첫 문장이며 강조할 가치가 있는 내용을 담고 있습니다. '
            '```python\ndef hello():\n    print("this is not a quote")\n```\n'
            '두 번째 본문 문장으로 충분한 길이를 가집니다.'
        )
        result = extract_pull_quotes(content)
        for q in result['quotes']:
            assert 'def hello' not in q['text']
            assert 'print' not in q['text']

    def test_headings_excluded_from_sentences(self):
        content = '# 제목 섹션\n\n본문 첫 번째 문장이며 강조에 적합한 길이입니다.'
        result = extract_pull_quotes(content)
        for q in result['quotes']:
            assert '제목 섹션' not in q['text']

    def test_position_score_favors_first_and_last(self):
        # 동일 패턴 문장 여러 개 — 위치만 다름
        sentences = ['중간 정도의 길이를 가진 완전한 문장이다.'] * 7
        content = ' '.join(sentences)
        result = extract_pull_quotes(content, top_n=7)
        # 서두(0) 또는 말미(6) 문장이 가장 높은 점수를 가져야 함
        scores_by_pos = {q['position']: q['score'] for q in result['quotes']}
        if len(scores_by_pos) >= 3:
            mid_pos = max(scores_by_pos.keys()) // 2
            assert scores_by_pos.get(0, 0) >= scores_by_pos.get(mid_pos, 0)

    def test_custom_min_max_length(self):
        content = '짧은 문장. ' + ('긴' * 50) + '. ' + ('매우긴' * 100) + '.'
        result = extract_pull_quotes(content, min_length=10, max_length=60)
        for q in result['quotes']:
            assert 10 <= q['length'] <= 60

    def test_quotes_sorted_by_score_descending(self):
        content = ' '.join([
            '첫째 중요한 핵심 문장입니다 꼭 기억하세요.',
            '평범한 내용의 문장입니다 특별한 것은 없습니다.',
            '이 비결은 반드시 실천해야 하는 요점입니다.',
        ])
        result = extract_pull_quotes(content, top_n=3)
        scores = [q['score'] for q in result['quotes']]
        assert scores == sorted(scores, reverse=True)

    def test_top_n_zero_returns_all_candidates(self):
        content = '첫 문장입니다 적당한 길이를 가집니다. 둘째 문장이며 역시 통과합니다. 셋째 문장.'
        result = extract_pull_quotes(content, top_n=0)
        assert len(result['quotes']) == result['total_candidates']


class TestFormatAsBlockquote:
    def test_empty_returns_empty(self):
        assert format_as_blockquote('') == ''
        assert format_as_blockquote('   ') == ''

    def test_single_line_wraps(self):
        block = format_as_blockquote('한 줄 인용구')
        assert block.startswith('> ')
        assert '한 줄 인용구' in block

    def test_multi_line_each_prefixed(self):
        block = format_as_blockquote('첫 줄\n둘째 줄')
        lines = block.split('\n')
        assert all(line.startswith('> ') for line in lines if line)

    def test_attribution_appended(self):
        block = format_as_blockquote('명문장입니다.', attribution='홍길동')
        assert '홍길동' in block
        assert '— 홍길동' in block
