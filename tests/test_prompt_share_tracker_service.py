"""prompt_share_tracker_service 단위 테스트"""
import pytest
from services.prompt_share_tracker_service import (
    ShareReport,
    track_prompt_share,
    compare_brands,
    get_top_mentioned_terms,
    _count_mentions,
    _find_matching_prompts,
    _calculate_share,
)


# ──────────────────────────────────────────────────
# ShareReport 데이터클래스 테스트
# ──────────────────────────────────────────────────

class TestShareReport:
    def test_dataclass_fields(self):
        """ShareReport 필드가 올바르게 생성된다"""
        report = ShareReport(
            brand='TestBrand',
            total_prompts=100,
            brand_mentions=25,
            share_percent=25.0,
            competitor_shares={'CompA': 10.0},
            trending_prompts=['prompt1'],
        )
        assert report.brand == 'TestBrand'
        assert report.total_prompts == 100
        assert report.brand_mentions == 25
        assert report.share_percent == 25.0
        assert report.competitor_shares == {'CompA': 10.0}
        assert report.trending_prompts == ['prompt1']

    def test_default_trending_prompts(self):
        """trending_prompts 기본값은 빈 리스트이다"""
        report = ShareReport(
            brand='X', total_prompts=0, brand_mentions=0,
            share_percent=0.0, competitor_shares={},
        )
        assert report.trending_prompts == []


# ──────────────────────────────────────────────────
# _count_mentions 내부 함수 테스트
# ──────────────────────────────────────────────────

class TestCountMentions:
    def test_basic_count(self):
        """기본 키워드 언급 수를 정확히 센다"""
        prompts = ['I love Google', 'Google is great', 'No mention here']
        assert _count_mentions(prompts, 'Google') == 2

    def test_case_insensitive(self):
        """대소문자를 무시하고 카운트한다"""
        prompts = ['APPLE is good', 'apple pie', 'Apples are tasty']
        # 'Apples'는 단어 경계에서 'Apple'과 다르므로 매칭되지 않음
        assert _count_mentions(prompts, 'apple') == 2

    def test_no_partial_match(self):
        """부분 일치는 카운트하지 않는다"""
        prompts = ['I use an application', 'This app is great']
        assert _count_mentions(prompts, 'app') == 1

    def test_empty_keyword(self):
        """빈 키워드는 0을 반환한다"""
        assert _count_mentions(['hello'], '') == 0
        assert _count_mentions(['hello'], '   ') == 0

    def test_empty_prompts(self):
        """빈 프롬프트 리스트는 0을 반환한다"""
        assert _count_mentions([], 'test') == 0

    def test_special_characters_in_keyword(self):
        """특수문자가 포함된 키워드도 정확히 매칭한다"""
        prompts = ['C++ is fast', 'I prefer C#', 'Use C++ compiler']
        assert _count_mentions(prompts, 'C++') == 2


# ──────────────────────────────────────────────────
# _find_matching_prompts 테스트
# ──────────────────────────────────────────────────

class TestFindMatchingPrompts:
    def test_finds_matching(self):
        """매칭되는 프롬프트만 반환한다"""
        prompts = ['Samsung phone', 'Apple watch', 'Samsung TV']
        result = _find_matching_prompts(prompts, 'Samsung')
        assert result == ['Samsung phone', 'Samsung TV']

    def test_empty_keyword_returns_empty(self):
        """빈 키워드는 빈 리스트를 반환한다"""
        assert _find_matching_prompts(['test'], '') == []


# ──────────────────────────────────────────────────
# _calculate_share 테스트
# ──────────────────────────────────────────────────

class TestCalculateShare:
    def test_normal_share(self):
        """정상 점유율 계산"""
        assert _calculate_share(25, 100) == 25.0

    def test_zero_total(self):
        """전체가 0이면 0.0 반환"""
        assert _calculate_share(5, 0) == 0.0

    def test_rounding(self):
        """소수점 둘째 자리 반올림"""
        assert _calculate_share(1, 3) == 33.33

    def test_full_share(self):
        """100% 점유율"""
        assert _calculate_share(10, 10) == 100.0


# ──────────────────────────────────────────────────
# track_prompt_share 핵심 함수 테스트
# ──────────────────────────────────────────────────

class TestTrackPromptShare:
    def test_basic_tracking(self):
        """기본 브랜드 추적이 정확히 동작한다"""
        prompts = [
            'ChatGPT is amazing',
            'I use ChatGPT daily',
            'Gemini is also good',
            'Claude is my favorite',
            'ChatGPT vs Claude',
        ]
        report = track_prompt_share(prompts, 'ChatGPT', ['Claude', 'Gemini'])

        assert isinstance(report, ShareReport)
        assert report.brand == 'ChatGPT'
        assert report.total_prompts == 5
        assert report.brand_mentions == 3
        assert report.share_percent == 60.0
        assert report.competitor_shares['Claude'] == 40.0
        assert report.competitor_shares['Gemini'] == 20.0

    def test_no_competitors(self):
        """경쟁사 없이도 동작한다"""
        prompts = ['Brand X rocks', 'I love Brand X']
        report = track_prompt_share(prompts, 'Brand X')

        assert report.competitor_shares == {}
        assert report.brand_mentions == 2

    def test_no_mentions(self):
        """브랜드가 언급되지 않으면 0%"""
        prompts = ['nothing here', 'still nothing']
        report = track_prompt_share(prompts, 'UnknownBrand')

        assert report.brand_mentions == 0
        assert report.share_percent == 0.0
        assert report.trending_prompts == []

    def test_empty_prompts_list(self):
        """빈 프롬프트 리스트"""
        report = track_prompt_share([], 'Brand')

        assert report.total_prompts == 0
        assert report.brand_mentions == 0
        assert report.share_percent == 0.0

    def test_trending_prompts_collected(self):
        """브랜드가 언급된 프롬프트가 trending에 수집된다"""
        prompts = ['Tesla car', 'Toyota truck', 'Tesla roadster']
        report = track_prompt_share(prompts, 'Tesla')

        assert len(report.trending_prompts) == 2
        assert 'Tesla car' in report.trending_prompts
        assert 'Tesla roadster' in report.trending_prompts

    def test_none_prompts_raises(self):
        """prompts가 None이면 ValueError"""
        with pytest.raises(ValueError, match="prompts는 None"):
            track_prompt_share(None, 'Brand')

    def test_empty_brand_raises(self):
        """brand가 빈 문자열이면 ValueError"""
        with pytest.raises(ValueError, match="brand는 빈 문자열"):
            track_prompt_share(['test'], '')

    def test_whitespace_brand_raises(self):
        """brand가 공백만이면 ValueError"""
        with pytest.raises(ValueError, match="brand는 빈 문자열"):
            track_prompt_share(['test'], '   ')

    def test_empty_competitor_skipped(self):
        """빈 문자열 경쟁사는 건너뛴다"""
        prompts = ['Google search', 'Bing search']
        report = track_prompt_share(prompts, 'Google', ['', '  ', 'Bing'])

        assert len(report.competitor_shares) == 1
        assert 'Bing' in report.competitor_shares

    def test_korean_brand(self):
        """한국어 브랜드명도 정확히 추적한다"""
        prompts = [
            '네이버 검색이 편해요',
            '구글 검색도 좋아요',
            '네이버 블로그 작성',
        ]
        report = track_prompt_share(prompts, '네이버', ['구글'])

        assert report.brand_mentions == 2
        assert report.share_percent == 66.67
        assert report.competitor_shares['구글'] == 33.33

    def test_brand_stripped(self):
        """브랜드명 앞뒤 공백이 제거된다"""
        prompts = ['Use Google', 'Try Bing']
        report = track_prompt_share(prompts, '  Google  ')

        assert report.brand == 'Google'
        assert report.brand_mentions == 1


# ──────────────────────────────────────────────────
# compare_brands 테스트
# ──────────────────────────────────────────────────

class TestCompareBrands:
    def test_comparison_sorted(self):
        """브랜드 비교 결과가 점유율 내림차순으로 정렬된다"""
        prompts = [
            'ChatGPT is great',
            'ChatGPT is fast',
            'Claude is smart',
            'Gemini is new',
        ]
        result = compare_brands(prompts, ['ChatGPT', 'Claude', 'Gemini'])

        keys = list(result.keys())
        assert keys[0] == 'ChatGPT'
        assert result['ChatGPT'] == 50.0
        assert result['Claude'] == 25.0

    def test_empty_inputs(self):
        """빈 입력은 빈 딕셔너리 반환"""
        assert compare_brands([], ['A']) == {}
        assert compare_brands(['test'], []) == {}


# ──────────────────────────────────────────────────
# get_top_mentioned_terms 테스트
# ──────────────────────────────────────────────────

class TestGetTopMentionedTerms:
    def test_top_n(self):
        """상위 N개 용어를 올바르게 반환한다"""
        prompts = ['AI AI AI', 'ML ML', 'DL']
        # 각 프롬프트에서 한번씩만 카운트 (프롬프트 수 기준)
        result = get_top_mentioned_terms(prompts, ['AI', 'ML', 'DL'], top_n=2)

        assert len(result) == 2
        assert result[0][0] == 'AI'
        assert result[0][1] == 1  # 1개 프롬프트에서 언급

    def test_empty_inputs(self):
        """빈 입력은 빈 리스트 반환"""
        assert get_top_mentioned_terms([], ['A']) == []
        assert get_top_mentioned_terms(['test'], []) == []
