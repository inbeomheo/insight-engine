"""ai_citation_map_service 단위 테스트"""
import pytest
from services.ai_citation_map_service import (
    CitationEntry,
    CitationMap,
    map_citations,
    get_citation_summary,
    _extract_domain,
    _classify_citation_type,
    _extract_citations_from_text,
    _get_context,
)


# ──────────────────────────────────────────────────
# CitationEntry / CitationMap 데이터클래스 테스트
# ──────────────────────────────────────────────────

class TestDataClasses:
    def test_citation_entry_fields(self):
        """CitationEntry 필드가 올바르게 생성된다"""
        entry = CitationEntry(
            domain='example.com',
            url='https://example.com/page',
            citation_type='direct',
            context='some context',
            frequency=3,
        )
        assert entry.domain == 'example.com'
        assert entry.url == 'https://example.com/page'
        assert entry.citation_type == 'direct'
        assert entry.frequency == 3

    def test_citation_entry_none_url(self):
        """URL이 None인 CitationEntry도 유효하다"""
        entry = CitationEntry(
            domain='test.org', url=None, citation_type='indirect',
            context='ctx', frequency=1,
        )
        assert entry.url is None

    def test_citation_map_defaults(self):
        """CitationMap 기본값이 빈 리스트이다"""
        cm = CitationMap(total_citations=0, by_domain={}, by_type={})
        assert cm.entries == []
        assert cm.top_domains == []


# ──────────────────────────────────────────────────
# _extract_domain 테스트
# ──────────────────────────────────────────────────

class TestExtractDomain:
    def test_basic_url(self):
        """기본 URL에서 도메인 추출"""
        assert _extract_domain('https://www.example.com/page') == 'example.com'

    def test_no_www(self):
        """www 없는 URL"""
        assert _extract_domain('https://github.com/repo') == 'github.com'

    def test_subdomain(self):
        """서브도메인 포함 URL"""
        assert _extract_domain('https://docs.python.org/3/') == 'docs.python.org'

    def test_invalid_url(self):
        """잘못된 URL은 빈 문자열 반환"""
        assert _extract_domain('not-a-url') == ''


# ──────────────────────────────────────────────────
# _classify_citation_type 테스트
# ──────────────────────────────────────────────────

class TestClassifyCitationType:
    def test_direct_quote_double(self):
        """큰따옴표 직접 인용 감지"""
        ctx = 'According to the paper, "this is a direct quote from the source" and more.'
        assert _classify_citation_type(ctx) == 'direct'

    def test_indirect_according_to(self):
        """'according to' 간접 인용 감지"""
        ctx = 'According to researchers, the data shows...'
        assert _classify_citation_type(ctx) == 'indirect'

    def test_indirect_korean(self):
        """한국어 간접 인용 감지"""
        ctx = '연구에 따르면 이 결과는 유의미하다'
        assert _classify_citation_type(ctx) == 'indirect'

    def test_paraphrase_reference(self):
        """패러프레이즈 감지"""
        ctx = '이 데이터는 해당 출처를 참조하였습니다'
        assert _classify_citation_type(ctx) == 'paraphrase'

    def test_default_indirect(self):
        """분류 불가 시 기본값은 indirect"""
        ctx = 'some generic text without any markers'
        assert _classify_citation_type(ctx) == 'indirect'


# ──────────────────────────────────────────────────
# _get_context 테스트
# ──────────────────────────────────────────────────

class TestGetContext:
    def test_normal_context(self):
        """정상 범위 문맥 추출"""
        text = 'A' * 100 + 'TARGET' + 'B' * 100
        ctx = _get_context(text, 100, 106, window=10)
        assert 'TARGET' in ctx
        assert len(ctx) <= 30  # 10 + 6 + 10 + 약간의 여유

    def test_start_boundary(self):
        """텍스트 시작 부분 경계 처리"""
        text = 'SHORT text here'
        ctx = _get_context(text, 0, 5, window=100)
        assert 'SHORT' in ctx

    def test_end_boundary(self):
        """텍스트 끝 부분 경계 처리"""
        text = 'text at END'
        ctx = _get_context(text, 8, 11, window=100)
        assert 'END' in ctx


# ──────────────────────────────────────────────────
# _extract_citations_from_text 테스트
# ──────────────────────────────────────────────────

class TestExtractCitationsFromText:
    def test_url_extraction(self):
        """URL이 포함된 텍스트에서 인용을 추출한다"""
        text = 'Visit https://example.com/article for more info.'
        citations = _extract_citations_from_text(text)

        assert len(citations) >= 1
        assert citations[0]['domain'] == 'example.com'
        assert citations[0]['url'] == 'https://example.com/article'

    def test_multiple_urls(self):
        """여러 URL을 모두 추출한다"""
        text = (
            'See https://github.com/repo and '
            'also https://stackoverflow.com/q/123'
        )
        citations = _extract_citations_from_text(text)
        domains = [c['domain'] for c in citations]

        assert 'github.com' in domains
        assert 'stackoverflow.com' in domains

    def test_domain_without_url(self):
        """URL 없이 도메인만 언급된 경우도 감지한다"""
        text = 'wikipedia.org에 따르면 이 정보는 정확합니다.'
        citations = _extract_citations_from_text(text)

        assert len(citations) >= 1
        assert any(c['domain'] == 'wikipedia.org' for c in citations)

    def test_duplicate_url_skipped(self):
        """동일 URL 중복은 제거한다"""
        text = (
            'https://example.com/page is here. '
            'And https://example.com/page again.'
        )
        citations = _extract_citations_from_text(text)
        urls = [c['url'] for c in citations if c['url']]

        assert urls.count('https://example.com/page') == 1

    def test_no_citations(self):
        """인용이 없는 텍스트는 빈 리스트 반환"""
        text = 'This is a plain text without any references.'
        citations = _extract_citations_from_text(text)
        assert citations == []


# ──────────────────────────────────────────────────
# map_citations 핵심 함수 테스트
# ──────────────────────────────────────────────────

class TestMapCitations:
    def test_basic_mapping(self):
        """기본 인용 맵 생성이 동작한다"""
        responses = [
            'According to https://arxiv.org/abs/123, the model works well.',
            'Based on https://arxiv.org/abs/456, the results are confirmed. '
            'Also see https://github.com/repo.',
        ]
        result = map_citations(responses)

        assert isinstance(result, CitationMap)
        assert result.total_citations >= 2
        assert 'arxiv.org' in result.by_domain
        assert result.by_domain['arxiv.org'] == 2
        assert len(result.top_domains) > 0

    def test_empty_responses(self):
        """빈 응답 리스트는 빈 맵 반환"""
        result = map_citations([])

        assert result.total_citations == 0
        assert result.by_domain == {}
        assert result.by_type == {}
        assert result.entries == []
        assert result.top_domains == []

    def test_none_raises(self):
        """None 입력은 ValueError"""
        with pytest.raises(ValueError, match="ai_responses는 None"):
            map_citations(None)

    def test_blank_responses_skipped(self):
        """빈 문자열 응답은 건너뛴다"""
        result = map_citations(['', '   ', '\n'])

        assert result.total_citations == 0

    def test_entries_sorted_by_frequency(self):
        """entries가 빈도 내림차순으로 정렬된다"""
        responses = [
            'https://a.com/1 and https://b.com/1',
            'https://a.com/2 and https://a.com/3',
        ]
        result = map_citations(responses)

        if len(result.entries) >= 2:
            assert result.entries[0].frequency >= result.entries[1].frequency

    def test_by_type_populated(self):
        """인용 유형별 집계가 수행된다"""
        responses = [
            'According to https://example.com, the data shows this.',
            '"This is a direct quote" from https://source.org/article.',
        ]
        result = map_citations(responses)

        assert len(result.by_type) > 0
        # 유효한 유형만 존재
        for t in result.by_type:
            assert t in ('direct', 'indirect', 'paraphrase')

    def test_top_n_limit(self):
        """top_n 파라미터로 상위 도메인 수를 제한한다"""
        responses = [
            'https://a.com/x https://b.com/x https://c.com/x '
            'https://d.com/x https://e.com/x',
        ]
        result = map_citations(responses, top_n=3)

        assert len(result.top_domains) <= 3

    def test_korean_context_indirect(self):
        """한국어 간접 인용이 올바르게 분류된다"""
        responses = [
            'https://naver.com 에 따르면 검색 품질이 향상되었습니다.',
        ]
        result = map_citations(responses)

        assert result.total_citations >= 1
        # 간접 인용으로 분류
        naver_entries = [e for e in result.entries if e.domain == 'naver.com']
        if naver_entries:
            assert naver_entries[0].citation_type == 'indirect'

    def test_mixed_url_and_domain(self):
        """URL과 도메인만 언급이 혼합된 경우"""
        responses = [
            'See https://example.com/page for details. '
            'Also check wikipedia.org for background.',
        ]
        result = map_citations(responses)

        domains = [e.domain for e in result.entries]
        assert 'example.com' in domains
        assert 'wikipedia.org' in domains

    def test_url_trailing_period_stripped(self):
        """URL 끝의 마침표가 제거된다"""
        responses = ['Visit https://example.com/page.']
        result = map_citations(responses)

        if result.entries:
            url = result.entries[0].url
            assert url is None or not url.endswith('.')


# ──────────────────────────────────────────────────
# get_citation_summary 테스트
# ──────────────────────────────────────────────────

class TestGetCitationSummary:
    def test_summary_with_data(self):
        """데이터가 있을 때 요약 통계를 반환한다"""
        cm = CitationMap(
            total_citations=10,
            by_domain={'a.com': 5, 'b.com': 3, 'c.com': 2},
            by_type={'indirect': 6, 'direct': 4},
            entries=[],
            top_domains=['a.com', 'b.com', 'c.com'],
        )
        summary = get_citation_summary(cm)

        assert summary['total'] == 10
        assert summary['unique_domains'] == 3
        assert summary['primary_type'] == 'indirect'
        assert summary['top_domain'] == 'a.com'

    def test_summary_empty(self):
        """빈 맵에서 요약은 기본값을 반환한다"""
        cm = CitationMap(
            total_citations=0, by_domain={}, by_type={},
        )
        summary = get_citation_summary(cm)

        assert summary['total'] == 0
        assert summary['unique_domains'] == 0
        assert summary['primary_type'] == ''
        assert summary['top_domain'] == ''

    def test_summary_single_type(self):
        """단일 유형만 있을 때 primary_type이 올바르다"""
        cm = CitationMap(
            total_citations=3,
            by_domain={'x.com': 3},
            by_type={'paraphrase': 3},
            top_domains=['x.com'],
        )
        summary = get_citation_summary(cm)

        assert summary['primary_type'] == 'paraphrase'
