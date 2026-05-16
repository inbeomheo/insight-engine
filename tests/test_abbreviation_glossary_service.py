"""abbreviation_glossary_service 단위 테스트."""
import pytest

from services.content.abbreviation_glossary_service import (
    extract_abbreviations,
    annotate_first_use,
    format_glossary_markdown,
)


class TestExtractAbbreviations:
    def test_empty_content(self):
        result = extract_abbreviations('')
        assert result['glossary'] == {}
        assert result['occurrences'] == {}
        assert result['undefined'] == []

    def test_detects_parenthetical_definition_korean(self):
        content = '자연어 처리(NLP)는 AI의 한 분야입니다. 이후 NLP 기법을 사용.'
        result = extract_abbreviations(content)
        assert 'NLP' in result['glossary']
        assert result['glossary']['NLP'] == '자연어 처리'

    def test_detects_parenthetical_definition_english(self):
        content = 'Machine Learning (ML) is a subset of AI. Later we use ML often.'
        result = extract_abbreviations(content)
        assert 'ML' in result['glossary']
        assert 'Machine Learning' in result['glossary']['ML']

    def test_user_glossary_takes_precedence(self):
        content = '잘못된 풀네임(NLP)가 본문에 있지만 사용자 정의를 우선. NLP를 사용.'
        user = {'NLP': '자연어 처리'}
        result = extract_abbreviations(content, user_glossary=user)
        assert result['glossary']['NLP'] == '자연어 처리'

    def test_occurrences_counted(self):
        content = 'API 설명. 이 API는 API와 같은 의미. 그리고 HTTP도 중요.'
        result = extract_abbreviations(content)
        assert result['occurrences'].get('API', 0) == 3
        assert result['occurrences'].get('HTTP', 0) == 1

    def test_first_position_tracked(self):
        content = '첫 부분. API가 처음 등장. 이후 API 재등장.'
        result = extract_abbreviations(content)
        assert 'API' in result['first_position']
        assert result['first_position']['API'] < 20  # 대략 '첫 부분. ' 이후

    def test_undefined_list_only_contains_unknown(self):
        content = '자연어 처리(NLP)를 설명. NLP와 XYZ를 사용.'
        result = extract_abbreviations(content)
        assert 'NLP' not in result['undefined']
        assert 'XYZ' in result['undefined']

    def test_min_occurrences_filter(self):
        content = '머신러닝(ML)은 중요. ML 기법을 여러 번 설명. ABC는 한 번만.'
        result = extract_abbreviations(content, min_occurrences=2)
        # ML은 2번 이상 등장 → 유지
        assert 'ML' in result['glossary']

    def test_code_blocks_ignored(self):
        content = '실제 텍스트(ABC)에 약어 정의.\n\n```\nCODE BLOCK with ABBR(XYZ)\n```'
        result = extract_abbreviations(content)
        # 코드 블록 안의 XYZ는 집계에서 제외
        assert 'ABC' in result['glossary']
        assert 'XYZ' not in result['glossary']
        assert result['occurrences'].get('XYZ', 0) == 0

    def test_short_fullname_rejected(self):
        content = 'AB(XY)는 너무 짧아서 정의로 간주하지 않음.'
        result = extract_abbreviations(content)
        assert 'XY' not in result['glossary']

    def test_lowercase_acronyms_ignored(self):
        content = '소문자(abc)는 약어로 취급하지 않음. Foo(bar)도 마찬가지.'
        result = extract_abbreviations(content)
        assert result['glossary'] == {}

    def test_abbr_with_digit_accepted(self):
        content = '하이퍼텍스트 전송 프로토콜(HTTP2)를 설명. HTTP2는 빠르다.'
        result = extract_abbreviations(content)
        assert 'HTTP2' in result['glossary']

    def test_english_initials_must_match(self):
        # 영문 2단어 이상 풀네임의 이니셜이 약어와 맞지 않으면 거부
        content = 'Random Words Here (NLP) appears but initials mismatch. NLP still used.'
        result = extract_abbreviations(content)
        # 이니셜 'RWH'가 'NLP'를 포함하지 않음 → 거부
        assert 'NLP' not in result['glossary']

    def test_english_initials_subsequence_accepted(self):
        # 이니셜의 부분 수열이면 허용 (예: Natural Language Processing → NLP)
        content = 'Natural Language Processing (NLP) is a field. Later NLP is used.'
        result = extract_abbreviations(content)
        assert 'NLP' in result['glossary']


class TestAnnotateFirstUse:
    def test_empty_inputs(self):
        assert annotate_first_use('', {}) == {'suggestions': [], 'already_defined': []}

    def test_suggests_definition_on_first_use(self):
        content = '본문에서 NLP가 처음 나옴. 이후 NLP 반복.'
        glossary = {'NLP': '자연어 처리'}
        result = annotate_first_use(content, glossary)
        assert len(result['suggestions']) == 1
        s = result['suggestions'][0]
        assert s['abbr'] == 'NLP'
        assert s['fullname'] == '자연어 처리'
        assert s['suggestion'] == '자연어 처리(NLP)'
        assert 'context' in s

    def test_skip_when_already_defined(self):
        content = '자연어 처리(NLP)로 정의. 이후 NLP.'
        glossary = {'NLP': '자연어 처리'}
        result = annotate_first_use(content, glossary, only_missing=True)
        assert result['suggestions'] == []
        assert 'NLP' in result['already_defined']

    def test_multiple_abbreviations(self):
        content = 'API와 HTTP와 REST를 소개합니다.'
        glossary = {
            'API': 'Application Programming Interface',
            'HTTP': 'HyperText Transfer Protocol',
            'REST': 'Representational State Transfer',
        }
        result = annotate_first_use(content, glossary)
        abbrs = {s['abbr'] for s in result['suggestions']}
        assert abbrs == {'API', 'HTTP', 'REST'}


class TestFormatGlossaryMarkdown:
    def test_empty_glossary_returns_empty(self):
        assert format_glossary_markdown({}) == ''

    def test_sorted_alphabetically(self):
        md = format_glossary_markdown({'NLP': '자연어', 'API': '인터페이스', 'HTTP': '프로토콜'})
        lines = md.split('\n')
        # '- **API**', '- **HTTP**', '- **NLP**' 순서
        api_line = next(i for i, l in enumerate(lines) if 'API' in l)
        http_line = next(i for i, l in enumerate(lines) if 'HTTP' in l)
        nlp_line = next(i for i, l in enumerate(lines) if 'NLP' in l)
        assert api_line < http_line < nlp_line

    def test_title_included(self):
        md = format_glossary_markdown({'API': '인터페이스'}, title='Terms')
        assert '## Terms' in md

    def test_items_formatted_correctly(self):
        md = format_glossary_markdown({'API': '인터페이스'})
        assert '- **API**: 인터페이스' in md
