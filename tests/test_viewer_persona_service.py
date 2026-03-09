"""시청 페르소나 추론 및 관심사 이동 감지 서비스 테스트"""
import pytest

from services.viewer_persona_service import (
    InterestShift,
    VideoMeta,
    ViewerPersona,
    _avg_watch_ratio,
    _classify_length,
    _compute_category_stats,
    _determine_preferred_length,
    _parse_video,
    detect_interest_shift,
    infer_persona,
    suggest_reframe,
)


# ============================================================
# 헬퍼: 테스트 데이터 팩토리
# ============================================================

def _video(
    video_id="v1",
    title="테스트",
    category="Tech",
    duration_seconds=900,
    watch_ratio=0.8,
) -> dict:
    """VideoMeta 호환 dict를 간편하게 생성"""
    return {
        "video_id": video_id,
        "title": title,
        "category": category,
        "duration_seconds": duration_seconds,
        "watch_ratio": watch_ratio,
    }


# ============================================================
# _parse_video 테스트
# ============================================================

class TestParseVideo:
    def test_정상_변환(self):
        raw = _video(video_id="abc", category="Music", duration_seconds=120, watch_ratio=0.5)
        v = _parse_video(raw)
        assert isinstance(v, VideoMeta)
        assert v.video_id == "abc"
        assert v.category == "Music"
        assert v.duration_seconds == 120
        assert v.watch_ratio == 0.5

    def test_누락_필드_기본값(self):
        v = _parse_video({})
        assert v.video_id == ""
        assert v.watch_ratio == 0.0
        assert v.duration_seconds == 0

    def test_watch_ratio_클램핑(self):
        v = _parse_video({"watch_ratio": 1.5})
        assert v.watch_ratio == 1.0
        v2 = _parse_video({"watch_ratio": -0.3})
        assert v2.watch_ratio == 0.0

    def test_음수_duration_클램핑(self):
        v = _parse_video({"duration_seconds": -100})
        assert v.duration_seconds == 0


# ============================================================
# _classify_length 테스트
# ============================================================

class TestClassifyLength:
    def test_short(self):
        assert _classify_length(300) == "short"
        assert _classify_length(600) == "short"  # 경계값

    def test_medium(self):
        assert _classify_length(601) == "medium"
        assert _classify_length(1799) == "medium"

    def test_long(self):
        assert _classify_length(1800) == "long"  # 경계값
        assert _classify_length(7200) == "long"


# ============================================================
# infer_persona 테스트 — 3유형 분류
# ============================================================

class TestInferPersona:
    def test_빈_히스토리_기본값(self):
        """시청 데이터 없으면 learner + confidence 0"""
        result = infer_persona([])
        assert result.persona_type == "learner"
        assert result.confidence == 0.0
        assert result.interests == []
        assert result.preferred_length == "medium"

    def test_deep_diver_판별(self):
        """동일 카테고리 집중(70%) + 높은 시청 비율(80%)"""
        history = (
            [_video(category="AI", watch_ratio=0.85, duration_seconds=2000)] * 7
            + [_video(category="Web", watch_ratio=0.5)] * 2
            + [_video(category="Design", watch_ratio=0.4)] * 1
        )
        result = infer_persona(history)
        assert result.persona_type == "deep_diver"
        assert result.confidence > 0.5
        assert "AI" in result.interests

    def test_explorer_판별(self):
        """카테고리 다양성이 높은 경우 (각각 다른 카테고리)"""
        categories = ["AI", "Music", "Cook", "Sports", "Art", "Travel", "Science"]
        history = [_video(category=c, watch_ratio=0.5) for c in categories]
        result = infer_persona(history)
        assert result.persona_type == "explorer"
        assert result.confidence > 0.5

    def test_learner_판별(self):
        """집중도와 다양성이 중간인 경우"""
        history = (
            [_video(category="AI", watch_ratio=0.6)] * 4
            + [_video(category="Web", watch_ratio=0.5)] * 3
            + [_video(category="Design", watch_ratio=0.4)] * 3
        )
        result = infer_persona(history)
        assert result.persona_type == "learner"
        assert 0.0 < result.confidence <= 1.0

    def test_confidence_범위(self):
        """confidence는 항상 0~1"""
        # 극단적으로 높은 값들
        history = [_video(category="AI", watch_ratio=1.0)] * 20
        result = infer_persona(history)
        assert 0.0 <= result.confidence <= 1.0

    def test_interests_최대_5개(self):
        """관심사는 최대 5개까지"""
        cats = [f"Cat{i}" for i in range(10)]
        history = [_video(category=c) for c in cats]
        result = infer_persona(history)
        assert len(result.interests) <= 5

    def test_preferred_length_short(self):
        """짧은 영상 선호"""
        history = [_video(duration_seconds=300, watch_ratio=0.9)] * 10
        result = infer_persona(history)
        assert result.preferred_length == "short"

    def test_preferred_length_long(self):
        """긴 영상 선호"""
        history = [_video(duration_seconds=3600, watch_ratio=0.9)] * 10
        result = infer_persona(history)
        assert result.preferred_length == "long"

    def test_engagement_pattern_비어있지_않음(self):
        """engagement_pattern 문자열이 항상 존재"""
        result = infer_persona([_video()])
        assert len(result.engagement_pattern) > 0

    def test_단일_영상(self):
        """영상 1개로도 정상 동작"""
        result = infer_persona([_video(category="AI", watch_ratio=0.9)])
        assert result.persona_type in ("learner", "deep_diver", "explorer")
        assert len(result.interests) == 1


# ============================================================
# detect_interest_shift 테스트
# ============================================================

class TestDetectInterestShift:
    def test_빈_데이터(self):
        """한쪽이 비어있으면 strength 0"""
        result = detect_interest_shift([], [_video()])
        assert result.shift_strength == 0.0
        result2 = detect_interest_shift([_video()], [])
        assert result2.shift_strength == 0.0

    def test_동일_관심사_이동_없음(self):
        """최근과 과거가 동일하면 이동 강도 0"""
        videos = [_video(category="AI")] * 5
        result = detect_interest_shift(videos, videos)
        assert result.shift_strength == 0.0

    def test_완전_이동(self):
        """과거 A → 최근 B로 완전 전환"""
        older = [_video(category="AI")] * 5
        recent = [_video(category="Music")] * 5
        result = detect_interest_shift(recent, older)
        assert result.shift_strength == 1.0
        assert "AI" in result.from_topics
        assert "Music" in result.to_topics

    def test_부분_이동(self):
        """관심사가 일부만 이동한 경우 0 < strength < 1"""
        older = [_video(category="AI")] * 4 + [_video(category="Web")] * 1
        recent = [_video(category="AI")] * 2 + [_video(category="Music")] * 3
        result = detect_interest_shift(recent, older)
        assert 0.0 < result.shift_strength < 1.0

    def test_from_to_topics_내용(self):
        """감소/증가 토픽이 올바르게 분류되는지"""
        older = [_video(category="AI")] * 5
        recent = [_video(category="AI")] * 1 + [_video(category="Music")] * 4
        result = detect_interest_shift(recent, older)
        assert "AI" in result.from_topics
        assert "Music" in result.to_topics

    def test_period_문자열_포함(self):
        """period에 영상 수 정보가 포함되는지"""
        older = [_video(category="AI")] * 3
        recent = [_video(category="Music")] * 4
        result = detect_interest_shift(recent, older)
        assert "3" in result.period
        assert "4" in result.period

    def test_recommendation_안정적(self):
        """이동 강도 낮을 때 '안정적' 추천"""
        videos = [_video(category="AI")] * 5
        result = detect_interest_shift(videos, videos)
        assert "안정적" in result.recommendation

    def test_recommendation_강한_변화(self):
        """이동 강도 높을 때 '전략을 재편' 추천"""
        older = [_video(category="AI")] * 5
        recent = [_video(category="Music")] * 5
        result = detect_interest_shift(recent, older)
        assert "재편" in result.recommendation or "변화" in result.recommendation

    def test_카테고리_없는_데이터(self):
        """카테고리가 빈 문자열인 경우"""
        older = [_video(category="")] * 3
        recent = [_video(category="")] * 3
        result = detect_interest_shift(recent, older)
        assert result.shift_strength == 0.0
        assert "부족" in result.period or "부족" in result.recommendation


# ============================================================
# suggest_reframe 테스트
# ============================================================

class TestSuggestReframe:
    def test_빈_video_id(self):
        shift = InterestShift(shift_strength=0.5, to_topics=["AI"])
        result = suggest_reframe("", shift)
        assert "ID가 필요" in result

    def test_이동_없음(self):
        """shift_strength < 0.1이면 기존 유지 제안"""
        shift = InterestShift(shift_strength=0.05, to_topics=[])
        result = suggest_reframe("v1", shift)
        assert "유지" in result

    def test_약한_이동(self):
        """shift_strength 0.1~0.4 → 보조적 추가"""
        shift = InterestShift(shift_strength=0.3, to_topics=["Music"])
        result = suggest_reframe("v1", shift)
        assert "보조" in result
        assert "Music" in result

    def test_강한_이동(self):
        """shift_strength >= 0.4 → 방향 전환 권장"""
        shift = InterestShift(shift_strength=0.7, to_topics=["AI", "Design"])
        result = suggest_reframe("v1", shift)
        assert "재구성" in result
        assert "70%" in result

    def test_to_topics_비어있을_때(self):
        """to_topics가 없으면 일반적 제안"""
        shift = InterestShift(shift_strength=0.5, to_topics=[])
        result = suggest_reframe("v1", shift)
        assert "트렌드" in result


# ============================================================
# 내부 헬퍼 함수 직접 테스트
# ============================================================

class TestHelperFunctions:
    def test_avg_watch_ratio_빈_리스트(self):
        assert _avg_watch_ratio([]) == 0.0

    def test_avg_watch_ratio_정상(self):
        videos = [_parse_video(_video(watch_ratio=0.6)), _parse_video(_video(watch_ratio=0.8))]
        assert _avg_watch_ratio(videos) == pytest.approx(0.7)

    def test_compute_category_stats_빈_리스트(self):
        counter, diversity, dominant = _compute_category_stats([])
        assert len(counter) == 0
        assert diversity == 0.0
        assert dominant == 0.0

    def test_determine_preferred_length_빈_리스트(self):
        assert _determine_preferred_length([]) == "medium"
