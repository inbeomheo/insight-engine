"""크리에이터 적합도 점수 서비스 테스트

score_creator_fit, rank_creators 및 내부 함수들의 동작을 검증한다.
"""
import pytest
from services.creator_fit_service import (
    FitScore,
    score_creator_fit,
    rank_creators,
    _normalize_topics,
    _compute_topic_overlap,
    _compute_tone_score,
    _compute_audience_score,
    _identify_strengths,
    _identify_risks,
    _generate_recommendation,
)


# ── 픽스처 ────────────────────────────────────────────────────

def _make_profile(name="테스터", topics=None, audience_size=10000, tone="casual"):
    """테스트용 프로필 생성 헬퍼."""
    return {
        "name": name,
        "topics": topics or ["tech", "ai"],
        "audience_size": audience_size,
        "tone": tone,
    }


# ── _normalize_topics ────────────────────────────────────────

class TestNormalizeTopics:
    def test_기본_정규화(self):
        result = _normalize_topics(["AI", " Tech ", "python"])
        assert result == {"ai", "tech", "python"}

    def test_빈_리스트(self):
        assert _normalize_topics([]) == set()

    def test_공백_문자열_무시(self):
        result = _normalize_topics(["", "  ", "valid"])
        assert result == {"valid"}

    def test_비문자열_무시(self):
        result = _normalize_topics([123, None, "ok"])
        assert result == {"ok"}

    def test_중복_제거(self):
        result = _normalize_topics(["AI", "ai", "Ai"])
        assert result == {"ai"}


# ── _compute_topic_overlap ───────────────────────────────────

class TestComputeTopicOverlap:
    def test_완전_일치(self):
        score, overlap = _compute_topic_overlap({"a", "b"}, {"a", "b"})
        assert score == 1.0
        assert overlap == ["a", "b"]

    def test_부분_일치(self):
        score, overlap = _compute_topic_overlap({"a", "b", "c"}, {"b", "c", "d"})
        # 교집합={b,c}, 합집합={a,b,c,d}, Jaccard=2/4=0.5
        assert score == 0.5
        assert overlap == ["b", "c"]

    def test_겹침_없음(self):
        score, overlap = _compute_topic_overlap({"a"}, {"b"})
        assert score == 0.0
        assert overlap == []

    def test_양쪽_빈_집합(self):
        score, overlap = _compute_topic_overlap(set(), set())
        assert score == 0.0
        assert overlap == []

    def test_한쪽만_빈_집합(self):
        score, overlap = _compute_topic_overlap({"a"}, set())
        # 교집합=0, 합집합={a}, Jaccard=0/1=0.0
        assert score == 0.0


# ── _compute_tone_score ──────────────────────────────────────

class TestComputeToneScore:
    def test_동일_톤(self):
        assert _compute_tone_score("casual", "casual") == 1.0

    def test_호환_높은_톤(self):
        score = _compute_tone_score("casual", "humorous")
        assert score == 0.9

    def test_호환_낮은_톤(self):
        score = _compute_tone_score("professional", "humorous")
        assert score == 0.3

    def test_빈_톤(self):
        assert _compute_tone_score("", "casual") == 0.5

    def test_양쪽_빈_톤(self):
        assert _compute_tone_score("", "") == 0.5

    def test_매트릭스_외_톤(self):
        assert _compute_tone_score("aggressive", "gentle") == 0.5

    def test_역방향_조회(self):
        # (casual, professional)은 매트릭스에 없지만 (professional, casual) 있음
        score = _compute_tone_score("casual", "professional")
        assert score == 0.4


# ── _compute_audience_score ──────────────────────────────────

class TestComputeAudienceScore:
    def test_동일_규모(self):
        assert _compute_audience_score(10000, 10000) == 1.0

    def test_소규모_차이(self):
        assert _compute_audience_score(10000, 12000) == 1.0  # 비율 1.2

    def test_중간_차이(self):
        score = _compute_audience_score(10000, 40000)  # 비율 4
        assert score == 0.6

    def test_큰_차이(self):
        score = _compute_audience_score(1000, 100000)  # 비율 100
        assert score == 0.1

    def test_영_이하(self):
        assert _compute_audience_score(0, 10000) == 0.3
        assert _compute_audience_score(-1, 10000) == 0.3


# ── _identify_strengths ─────────────────────────────────────

class TestIdentifyStrengths:
    def test_높은_토픽_점수(self):
        strengths = _identify_strengths(0.6, 0.5, 0.5, ["ai", "tech"], _make_profile())
        assert any("공통 관심 토픽" in s for s in strengths)

    def test_높은_톤_호환(self):
        strengths = _identify_strengths(0.3, 0.9, 0.5, [], _make_profile())
        assert any("톤이 매우 잘 맞" in s for s in strengths)

    def test_큰_오디언스(self):
        profile = _make_profile(audience_size=150000)
        strengths = _identify_strengths(0.3, 0.5, 0.5, [], profile)
        assert any("영향력이 큽니다" in s for s in strengths)

    def test_모든_점수_낮으면_강점_없음(self):
        profile = _make_profile(audience_size=500)
        strengths = _identify_strengths(0.1, 0.3, 0.3, [], profile)
        assert len(strengths) == 0


# ── _identify_risks ──────────────────────────────────────────

class TestIdentifyRisks:
    def test_토픽_겹침_없음(self):
        risks = _identify_risks(0.05, 0.5, 0.5, _make_profile(), _make_profile())
        assert any("토픽 겹침이 거의 없" in r for r in risks)

    def test_톤_차이(self):
        creator = _make_profile(tone="humorous")
        our = _make_profile(tone="professional")
        risks = _identify_risks(0.5, 0.3, 0.5, creator, our)
        assert any("톤 차이" in r for r in risks)

    def test_소규모_크리에이터(self):
        profile = _make_profile(audience_size=500)
        risks = _identify_risks(0.5, 0.5, 0.5, profile, _make_profile())
        assert any("매우 적어" in r for r in risks)

    def test_압도적_규모_차이(self):
        creator = _make_profile(audience_size=1000000)
        our = _make_profile(audience_size=1000)
        risks = _identify_risks(0.5, 0.5, 0.1, creator, our)
        assert any("협상력" in r for r in risks)


# ── _generate_recommendation ─────────────────────────────────

class TestGenerateRecommendation:
    def test_매우_적합(self):
        rec = _generate_recommendation(85, ["강점1"], [])
        assert "적극적으로" in rec

    def test_적합(self):
        rec = _generate_recommendation(65, ["강점1"], [])
        assert "적합한 편" in rec

    def test_보통(self):
        rec = _generate_recommendation(45, [], ["리스크1"])
        assert "시범 협업" in rec

    def test_낮음(self):
        rec = _generate_recommendation(25, [], ["리스크1"])
        assert "적합도가 낮" in rec

    def test_부적합(self):
        rec = _generate_recommendation(10, [], ["리스크1", "리스크2"])
        assert "부적합" in rec


# ── score_creator_fit ────────────────────────────────────────

class TestScoreCreatorFit:
    def test_정상_동작(self):
        creator = _make_profile(
            name="크리에이터A",
            topics=["ai", "python", "data"],
            audience_size=50000,
            tone="educational",
        )
        our = _make_profile(
            name="우리채널",
            topics=["ai", "python", "web"],
            audience_size=40000,
            tone="educational",
        )
        result = score_creator_fit(creator, our)

        assert isinstance(result, FitScore)
        assert result.creator_name == "크리에이터A"
        assert 0 <= result.score <= 100
        assert "ai" in result.overlap_topics
        assert "python" in result.overlap_topics
        assert len(result.strengths) > 0
        assert isinstance(result.recommendation, str)

    def test_완벽_일치(self):
        profile = _make_profile(
            name="완벽매치",
            topics=["ai", "tech"],
            audience_size=10000,
            tone="casual",
        )
        result = score_creator_fit(profile, profile.copy())
        # 토픽 100% + 톤 100% + 오디언스 100% = 100
        assert result.score == 100.0

    def test_완전_불일치(self):
        creator = _make_profile(
            name="불일치",
            topics=["cooking", "travel"],
            audience_size=500,
            tone="humorous",
        )
        our = _make_profile(
            name="우리",
            topics=["finance", "law"],
            audience_size=500000,
            tone="professional",
        )
        result = score_creator_fit(creator, our)
        # 토픽 0 + 톤 낮음 + 오디언스 낮음 → 점수 낮음
        assert result.score < 30

    def test_None_creator_에러(self):
        with pytest.raises(ValueError, match="creator_profile"):
            score_creator_fit(None, _make_profile())

    def test_None_our_에러(self):
        with pytest.raises(ValueError, match="our_profile"):
            score_creator_fit(_make_profile(), None)

    def test_이름_없는_크리에이터_에러(self):
        with pytest.raises(ValueError, match="name"):
            score_creator_fit({"name": "", "topics": []}, _make_profile())

    def test_토픽_없는_프로필(self):
        creator = _make_profile(name="노토픽", topics=[])
        our = _make_profile(topics=[])
        result = score_creator_fit(creator, our)
        assert result.score >= 0  # 에러 없이 처리

    def test_톤_없는_프로필(self):
        creator = {"name": "노톤", "topics": ["ai"], "audience_size": 10000}
        our = {"name": "우리", "topics": ["ai"], "audience_size": 10000}
        result = score_creator_fit(creator, our)
        assert 0 <= result.score <= 100

    def test_점수_범위(self):
        """어떤 입력이든 점수는 0~100"""
        creator = _make_profile(name="범위테스트", audience_size=0)
        our = _make_profile(audience_size=0)
        result = score_creator_fit(creator, our)
        assert 0 <= result.score <= 100

    def test_토픽_대소문자_무시(self):
        creator = _make_profile(name="대소문자", topics=["AI", "Python"])
        our = _make_profile(topics=["ai", "python"])
        result = score_creator_fit(creator, our)
        assert "ai" in result.overlap_topics
        assert "python" in result.overlap_topics


# ── rank_creators ────────────────────────────────────────────

class TestRankCreators:
    def test_정상_랭킹(self):
        creators = [
            _make_profile(name="A", topics=["ai"], audience_size=10000),
            _make_profile(name="B", topics=["ai", "tech", "python"], audience_size=12000),
            _make_profile(name="C", topics=["cooking"], audience_size=500),
        ]
        our = _make_profile(topics=["ai", "tech", "python"], audience_size=10000)
        results = rank_creators(creators, our)

        assert len(results) == 3
        # B가 토픽 겹침 가장 많으므로 1위
        assert results[0].creator_name == "B"
        # C가 최하위
        assert results[-1].creator_name == "C"
        # 내림차순 정렬 확인
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_top_n_제한(self):
        creators = [_make_profile(name=f"크리에이터{i}") for i in range(20)]
        our = _make_profile()
        results = rank_creators(creators, our, top_n=5)
        assert len(results) == 5

    def test_유효하지_않은_프로필_건너뜀(self):
        creators = [
            _make_profile(name="유효"),
            {"name": "", "topics": []},  # name 없음 → 건너뜀
            {"topics": ["ai"]},  # name 키 없음 → 건너뜀
        ]
        our = _make_profile()
        results = rank_creators(creators, our)
        assert len(results) == 1
        assert results[0].creator_name == "유효"

    def test_None_creators_에러(self):
        with pytest.raises(ValueError, match="creators"):
            rank_creators(None, _make_profile())

    def test_None_our_profile_에러(self):
        with pytest.raises(ValueError, match="our_profile"):
            rank_creators([], None)

    def test_빈_크리에이터_리스트(self):
        results = rank_creators([], _make_profile())
        assert results == []
