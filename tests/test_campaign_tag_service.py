"""캠페인 태그 분석 서비스 테스트

analyze_campaign, compare_campaigns 및 내부 함수들의 동작을 검증한다.
"""
import pytest
from services.campaign_tag_service import (
    CampaignReport,
    analyze_campaign,
    compare_campaigns,
    _normalize_tag,
    _compute_engagement,
    _estimate_reach,
    _analyze_sentiment,
    _rank_top_posts,
    _generate_recommendations,
)


# ── 픽스처 ────────────────────────────────────────────────────

def _make_post(text="테스트 게시물", likes=10, shares=5, comments=3):
    """테스트용 게시물 생성 헬퍼."""
    return {"text": text, "likes": likes, "shares": shares, "comments": comments}


def _make_posts(n, base_likes=10):
    """n개의 게시물을 생성한다."""
    return [_make_post(f"게시물 {i}", likes=base_likes * (i + 1)) for i in range(n)]


# ── _normalize_tag ────────────────────────────────────────────

class TestNormalizeTag:
    def test_해시태그_제거(self):
        assert _normalize_tag("#마케팅") == "마케팅"

    def test_공백_제거_소문자(self):
        assert _normalize_tag("  AI Marketing  ") == "ai marketing"

    def test_해시태그_없는_경우(self):
        assert _normalize_tag("tech") == "tech"

    def test_이중_해시태그(self):
        # 첫 번째 '#'만 제거
        assert _normalize_tag("##tag") == "#tag"


# ── _compute_engagement ──────────────────────────────────────

class TestComputeEngagement:
    def test_빈_리스트(self):
        assert _compute_engagement([]) == 0.0

    def test_정상_계산(self):
        # 게시물 1개, 총 상호작용 = 100+50+50 = 200
        # 평균 = 200, rate = (200/1000)*100 = 20.0
        posts = [_make_post(likes=100, shares=50, comments=50)]
        assert _compute_engagement(posts) == 20.0

    def test_상한_100_클리핑(self):
        # 상호작용이 매우 큰 경우 100 초과 불가
        posts = [_make_post(likes=5000, shares=5000, comments=5000)]
        assert _compute_engagement(posts) == 100.0

    def test_음수_값_무시(self):
        # 음수 likes/shares/comments는 0으로 처리
        posts = [{"text": "test", "likes": -10, "shares": -5, "comments": 20}]
        rate = _compute_engagement(posts)
        # 0 + 0 + 20 = 20, avg = 20, rate = 2.0
        assert rate == 2.0

    def test_여러_게시물_평균(self):
        # 2개 게시물, 총 = (10+5+3) + (20+10+5) = 18 + 35 = 53
        # 평균 = 26.5, rate = (26.5/1000)*100 = 2.65
        posts = [
            _make_post(likes=10, shares=5, comments=3),
            _make_post(likes=20, shares=10, comments=5),
        ]
        assert _compute_engagement(posts) == 2.65


# ── _estimate_reach ──────────────────────────────────────────

class TestEstimateReach:
    def test_빈_리스트(self):
        assert _estimate_reach([]) == 0

    def test_정상_계산(self):
        # 총 상호작용 = 100+50+30 = 180, 도달 = 180*3 = 540
        posts = [_make_post(likes=100, shares=50, comments=30)]
        assert _estimate_reach(posts) == 540

    def test_음수_값_무시(self):
        posts = [{"text": "test", "likes": -100, "shares": 10, "comments": 5}]
        # 0 + 10 + 5 = 15, 15*3 = 45
        assert _estimate_reach(posts) == 45

    def test_여러_게시물_합산(self):
        posts = [
            _make_post(likes=100, shares=0, comments=0),
            _make_post(likes=200, shares=0, comments=0),
        ]
        # 총 300, 도달 = 900
        assert _estimate_reach(posts) == 900


# ── _analyze_sentiment ───────────────────────────────────────

class TestAnalyzeSentiment:
    def test_빈_리스트(self):
        assert _analyze_sentiment([]) == "neutral"

    def test_긍정적(self):
        posts = [_make_post(text="정말 좋아요 추천합니다 최고의 콘텐츠")]
        assert _analyze_sentiment(posts) == "positive"

    def test_부정적(self):
        posts = [_make_post(text="별로 실망 최악의 경험 문제가 많다")]
        assert _analyze_sentiment(posts) == "negative"

    def test_중립(self):
        posts = [_make_post(text="오늘 날씨가 맑습니다")]
        assert _analyze_sentiment(posts) == "neutral"

    def test_영어_긍정(self):
        posts = [_make_post(text="This is great and awesome content, love it")]
        assert _analyze_sentiment(posts) == "positive"

    def test_텍스트_없는_게시물(self):
        posts = [{"likes": 10, "shares": 5, "comments": 2}]
        assert _analyze_sentiment(posts) == "neutral"

    def test_균형_시_중립(self):
        # 긍정 1개, 부정 1개 → 동점 → neutral
        posts = [_make_post(text="좋아요 별로")]
        assert _analyze_sentiment(posts) == "neutral"


# ── _rank_top_posts ──────────────────────────────────────────

class TestRankTopPosts:
    def test_빈_리스트(self):
        assert _rank_top_posts([]) == []

    def test_정렬_순서(self):
        posts = [
            _make_post(likes=10, shares=0, comments=0),
            _make_post(likes=100, shares=50, comments=20),
            _make_post(likes=50, shares=10, comments=5),
        ]
        result = _rank_top_posts(posts, top_n=2)
        assert len(result) == 2
        # 1위: 100+50+20=170, 2위: 50+10+5=65
        assert result[0]["likes"] == 100
        assert result[1]["likes"] == 50

    def test_top_n_초과(self):
        posts = _make_posts(3)
        result = _rank_top_posts(posts, top_n=10)
        assert len(result) == 3  # 3개밖에 없으므로 3개 반환


# ── _generate_recommendations ────────────────────────────────

class TestGenerateRecommendations:
    def test_낮은_참여율(self):
        recs = _generate_recommendations(3.0, "neutral", _make_posts(3))
        assert any("참여율이 낮습니다" in r for r in recs)

    def test_높은_참여율(self):
        recs = _generate_recommendations(25.0, "positive", _make_posts(10))
        assert any("참여율이 높습니다" in r for r in recs)

    def test_부정_감성_경고(self):
        recs = _generate_recommendations(10.0, "negative", _make_posts(10))
        assert any("부정적 반응" in r for r in recs)

    def test_데이터_부족_경고(self):
        recs = _generate_recommendations(10.0, "neutral", _make_posts(2))
        assert any("데이터가 부족" in r for r in recs)

    def test_충분한_데이터(self):
        recs = _generate_recommendations(10.0, "neutral", _make_posts(50))
        assert any("충분한 데이터" in r for r in recs)


# ── analyze_campaign ─────────────────────────────────────────

class TestAnalyzeCampaign:
    def test_정상_동작(self):
        posts = [
            _make_post("좋아요 최고!", likes=500, shares=200, comments=100),
            _make_post("추천합니다", likes=300, shares=100, comments=50),
        ]
        report = analyze_campaign("#AI마케팅", posts)

        assert isinstance(report, CampaignReport)
        assert report.tag == "ai마케팅"
        assert report.total_posts == 2
        assert 0 <= report.engagement_rate <= 100
        assert report.reach_estimate > 0
        assert report.sentiment == "positive"
        assert len(report.top_posts) <= 5
        assert len(report.recommendations) > 0

    def test_빈_태그_에러(self):
        with pytest.raises(ValueError, match="빈 문자열"):
            analyze_campaign("", [])

    def test_공백_태그_에러(self):
        with pytest.raises(ValueError, match="빈 문자열"):
            analyze_campaign("   ", [])

    def test_None_posts_에러(self):
        with pytest.raises(ValueError, match="None"):
            analyze_campaign("tag", None)

    def test_빈_게시물_리스트(self):
        report = analyze_campaign("test", [])
        assert report.total_posts == 0
        assert report.engagement_rate == 0.0
        assert report.reach_estimate == 0

    def test_해시태그_정규화(self):
        report = analyze_campaign("#MyTag", [])
        assert report.tag == "mytag"

    def test_필드_누락_게시물(self):
        # likes/shares/comments 키가 없는 게시물도 처리
        posts = [{"text": "텍스트만 있는 게시물"}]
        report = analyze_campaign("test", posts)
        assert report.total_posts == 1
        assert report.engagement_rate == 0.0


# ── compare_campaigns ────────────────────────────────────────

class TestCompareCampaigns:
    def test_정상_비교(self):
        r1 = analyze_campaign("tag1", _make_posts(5, base_likes=100))
        r2 = analyze_campaign("tag2", _make_posts(3, base_likes=50))
        result = compare_campaigns([r1, r2])

        assert "best_engagement" in result
        assert "best_reach" in result
        assert result["total_posts"] == 8
        assert result["avg_engagement"] > 0

    def test_빈_리포트_에러(self):
        with pytest.raises(ValueError, match="비교할 리포트"):
            compare_campaigns([])

    def test_단일_리포트(self):
        r = analyze_campaign("solo", _make_posts(2))
        result = compare_campaigns([r])
        assert result["best_engagement"]["tag"] == "solo"
        assert result["total_posts"] == 2
